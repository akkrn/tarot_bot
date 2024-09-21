import asyncio
import datetime
import random
import logging
import re
from typing import List, Tuple, Optional

from aiogram import Bot
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender
from sqlalchemy.ext.asyncio import AsyncSession

from models import Question, User
from services.openai import ask_openai
from services.utils import parse_response, find_or_insert_newline

from services.send_mediafiles import send_file, send_gif
from exceptions import FailedParseResponseException, GifSendException
from loader import images_path

from exceptions import FailedOpenAIGenerateError
from lexicon.lexicon import LEXICON_RU
from services.utils import calculate_reading_time
from constants import RETRY_ATTEMPTS, MIDDLE_SLEEP, LONG_SLEEP
from media_data import gifs_dict, cards_list

logger = logging.getLogger(__name__)


async def send_gif_with_retry(bot: Bot, user_tg_id: int) -> Optional[Message]:
    for _ in range(RETRY_ATTEMPTS):
        random_key = random.choice(list(gifs_dict.keys()))
        random_value = gifs_dict[random_key]
        try:
            return await send_gif(bot, random_value, random_key, user_tg_id)
        except GifSendException:
            continue
    return await bot.send_message(user_tg_id, LEXICON_RU["no_gif"])


async def generate_and_save_reading(
    session: AsyncSession,
    user: User,
    question: str,
    readable_names: List[str],
    img_names: List[str],
    bot: Bot,
    gif_message: Message,
) -> Tuple[Question, List[str], str, str]:
    try:
        response = await ask_openai(question, readable_names)
    except Exception:
        await bot.delete_message(user.user_tg_id, gif_message.message_id),
        raise FailedOpenAIGenerateError

    new_reading = Question(
        user_id=user.id,
        question=question,
        answer=response,
        cards=img_names,
        added_at=datetime.datetime.now(),
    )
    session.add(new_reading)
    await session.flush()

    try:
        parsed = parse_response(response, len(readable_names))
        card_descriptions = parsed[:-2]
        interpretation, advice = parsed[-2:]
    except FailedParseResponseException:
        cleaned_text = re.sub(r"<[^>]*>", "", response)
        card_descriptions = [""] * len(readable_names)
        interpretation, advice = find_or_insert_newline(cleaned_text)

    return new_reading, card_descriptions, interpretation, advice


async def send_cards_and_descriptions(
    bot: Bot,
    user_tg_id: int,
    img_names: List[str],
    readable_names: List[str],
    card_descriptions: List[str],
    gif_message: Message,
):
    for index, (name, caption, card_desc) in enumerate(
        zip(img_names, readable_names, card_descriptions)
    ):
        file_path = f"{images_path}{name}.jpg"
        if index == 0:
            await asyncio.gather(
                bot.delete_message(user_tg_id, gif_message.message_id),
                send_file(bot, file_path, name, user_tg_id, caption, True),
            )
        else:
            await send_file(bot, file_path, name, user_tg_id, caption, True)
        await asyncio.sleep(MIDDLE_SLEEP)
        if card_desc:
            await bot.send_message(user_tg_id, card_desc)
            await calculate_reading_time(card_desc)


async def send_interpretation_and_advice(
    bot: Bot, user_tg_id: int, interpretation: str, advice: str
):
    main_message = await bot.send_message(user_tg_id, interpretation)
    await calculate_reading_time(interpretation)
    await bot.send_message(user_tg_id, advice)
    await calculate_reading_time(advice)

    return main_message


async def start_tarot(
    bot: Bot, session: AsyncSession, question: str, user: User, num_cards: int
) -> int:
    gif_message = await send_gif_with_retry(bot, user.user_tg_id)

    async with ChatActionSender(
        bot=bot, action="typing", chat_id=user.user_tg_id
    ):
        keys = random.sample(list(cards_list.keys()), num_cards)
        selected_cards = {key: cards_list[key] for key in keys}
        img_names = list(selected_cards.keys())
        readable_names = list(selected_cards.values())

        new_reading, card_descriptions, interpretation, advice = (
            await generate_and_save_reading(
                session,
                user,
                question,
                readable_names,
                img_names,
                bot,
                gif_message,
            )
        )
        await asyncio.sleep(LONG_SLEEP)

    await send_cards_and_descriptions(
        bot,
        user.user_tg_id,
        img_names,
        readable_names,
        card_descriptions,
        gif_message,
    )
    main_message = await send_interpretation_and_advice(
        bot, user.user_tg_id, interpretation, advice
    )

    bot_username = main_message.from_user.username
    message_id = main_message.message_id
    link_to_answer = f"https://t.me/{bot_username}/{message_id}"
    new_reading.link = link_to_answer
    session.add(new_reading)
    return new_reading.id


async def start_1_tarot(
    bot: Bot, session: AsyncSession, question: str, user: User
) -> int:
    return await start_tarot(bot, session, question, user, 1)


async def start_3_tarot(
    bot: Bot, session: AsyncSession, question: str, user: User
) -> int:
    return await start_tarot(bot, session, question, user, 3)
