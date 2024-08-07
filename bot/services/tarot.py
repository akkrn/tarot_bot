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

logger = logging.getLogger(__name__)

SHORT_SLEEP = 3
MIDDLE_SLEEP = 5
LONG_SLEEP = 12
RETRY_ATTEMPTS = 3

cards_list = {
    "01_The_Fool": "Шут",
    "02_The_Magician": "Маг",
    "03_The_High_Priestess": "Верховная Жрица",
    "04_The_Empress": "Императрица",
    "05_The_Emperor": "Император",
    "06_The_Hierophant": "Верховный Жрец",
    "07_The_Lovers": "Влюбленные",
    "08_The_Chariot": "Колесница",
    "09_Strength": "Сила",
    "10_The_Hermit": "Отшельник",
    "11_Wheel_of_Fortune": "Колесо Фортуны",
    "12_Justice": "Справедливость",
    "13_The_Hanged_Man": "Повешенный",
    "14_Death": "Смерть",
    "15_Temperance": "Умеренность",
    "16_The_Devil": "Дьявол",
    "17_The_Tower": "Башня",
    "18_The_Star": "Звезда",
    "19_The_Moon": "Луна",
    "20_The_Sun": "Солнце",
    "21_Judgement": "Суд",
    "22_The_World": "Мир",
    "23_Ace_of_Wands": "Туз Жезлов",
    "24_Two_of_Wands": "Двойка Жезлов",
    "25_Three_of_Wands": "Тройка Жезлов",
    "26_Four_of_Wands": "Четверка Жезлов",
    "27_Five_of_Wands": "Пятерка Жезлов",
    "28_Six_of_Wands": "Шестерка Жезлов",
    "29_Seven_of_Wands": "Семерка Жезлов",
    "30_Eight_of_Wands": "Восьмерка Жезлов",
    "31_Nine_of_Wands": "Девятка Жезлов",
    "32_Ten_of_Wands": "Десятка Жезлов",
    "33_Page_of_Wands": "Паж Жезлов",
    "34_Knight_of_Wands": "Рыцарь Жезлов",
    "35_Queen_of_Wands": "Королева Жезлов",
    "36_King_of_Wands": "Король Жезлов",
    "37_Ace_of_Cups": "Туз Кубков",
    "38_Two_of_Cups": "Двойка Кубков",
    "39_Three_of_Cups": "Тройка Кубков",
    "40_Four_of_Cups": "Четверка Кубков",
    "41_Five_of_Cups": "Пятерка Кубков",
    "42_Six_of_Cups": "Шестерка Кубков",
    "43_Seven_of_Cups": "Семерка Кубков",
    "44_Eight_of_Cups": "Восьмерка Кубков",
    "45_Nine_of_Cups": "Девятка Кубков",
    "46_Ten_of_Cups": "Десятка Кубков",
    "47_Page_of_Cups": "Паж Кубков",
    "48_Knight_of_Cups": "Рыцарь Кубков",
    "49_Queen_of_Cups": "Королева Кубков",
    "50_King_of_Cups": "Король Кубков",
    "51_Ace_of_Swords": "Туз Мечей",
    "52_Two_of_Swords": "Двойка Мечей",
    "53_Three_of_Swords": "Тройка Мечей",
    "54_Four_of_Swords": "Четверка Мечей",
    "55_Five_of_Swords": "Пятерка Мечей",
    "56_Six_of_Swords": "Шестерка Мечей",
    "57_Seven_of_Swords": "Семерка Мечей",
    "58_Eight_of_Swords": "Восьмерка Мечей",
    "59_Nine_of_Swords": "Девятка Мечей",
    "60_Ten_of_Swords": "Десятка Мечей",
    "61_Page_of_Swords": "Паж Мечей",
    "62_Knight_of_Swords": "Рыцарь Мечей",
    "63_Queen_of_Swords": "Королева Мечей",
    "64_King_of_Swords": "Король Мечей",
    "65_Ace_of_Pentacles": "Туз Пентаклей",
    "66_Two_of_Pentacles": "Двойка Пентаклей",
    "67_Three_of_Pentacles": "Тройка Пентаклей",
    "68_Four_of_Pentacles": "Четверка Пентаклей",
    "69_Five_of_Pentacles": "Пятерка Пентаклей",
    "70_Six_of_Pentacles": "Шестерка Пентаклей",
    "71_Seven_of_Pentacles": "Семерка Пентаклей",
    "72_Eight_of_Pentacles": "Восьмерка Пентаклей",
    "73_Nine_of_Pentacles": "Девятка Пентаклей",
    "74_Ten_of_Pentacles": "Десятка Пентаклей",
    "75_Page_of_Pentacles": "Паж Пентаклей",
    "76_Knight_of_Pentacles": "Рыцарь Пентаклей",
    "77_Queen_of_Pentacles": "Королева Пентаклей",
    "78_King_of_Pentacles": "Король Пентаклей",
}

gifs_dict = {
    "gif_magic_cards": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExaWRiYTRudm42NTkzMXZjdmtzMWZvZzNwY2NkOXd5cGxtM2M2bXdqciZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/jprXz2xFUB8yP9tdCr/giphy.gif",
    "gif_black_swing": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExOGgxNmNwajlnMWNpZng2cHRwNGFhdmFjZm5raDh2N2ducnVkaW54cyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/SrWh9peE9r1MTVr8aQ/giphy.gif",
    "gif_moon_card": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExMDJrNXB5YjcxOGw4eWg2Z3p1cjRta3lyamZqdTExdGxlaWZocXh0YSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/3o6Zt85lYEswGtG2YM/giphy.gif",
    "gif_belly_fun": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExZ28zNG5keXBoNDQ4dWR6cGNyM2gyeGtuamJzejlnNWw5YXVqaXpiNyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/6zTaXrUs1rmCY/giphy.gif",
    "gif_two_cards_loading": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExdzk2aGZ3ZmYyajNkMnJ4MHFoa244eGZ6cDN3dW4xd2gxNGJkNHhibCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/z5cfdNGd140jVRvejU/giphy.gif",
    "gif_hands_moon": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExN3FzeGhnNnNqd2dxbW9zd3c5bWcwazk1ODd6amxnNTJ5ZnpwZnZpNyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/Ej9oJbyNCpXb43EIQo/giphy.gif",
    "gif_girl_crystal": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExOXZmb3Fkbm9saWVyNGp5Z2NjM2QxZ2ZtMnVsZ3dwYmhpbHRjcW5seiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/auA7QtdqknAHjSVoFG/giphy.gif",
    "gif_swing_crystal": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExZzRvem1nbWpvMTFpMjZuejR2cDNsZHc4b2VjcHdjMDh4bnN2cGM0MSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/TgukSxJbi5gpBcveG9/giphy.gif",
    "gif_moon_sand_watch": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExOGF1bWRscTQ0bDY1M3J2ZG40dmw1YW1sMTVxaTl5d241Y2x4MHg2ciZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/7CV8LZHr09ZKcV2LeQ/giphy.gif",
    "gif_4_cards_black": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3U5cXljNzN2YmJtNjJjeTZocmY5aWg5eGJ5YTg3c242dWlwbWl2dSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/Kc8I6ZIyaZAmhn3qZv/giphy.gif",
    "gif_scary_claws": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExdW9xbnB4cWdldWF1cnYwdG0zZDl3ZDl6ZXI5NGpxMTE0aHo2MXF6OCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/l44QE4JgwyYayc4CY/giphy.gif",
    "gif_shiny_moon_hands": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExY2dkdGpoN3A2a2tsZmkydjY1dWUyOG5tMHJpYXRjZm91cmV3eGZwYyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/wY55zd2BiuQ8CaePWY/giphy.gif",
    "gif_transform_witch_thing": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExNnU5aGZ1Y2Uxdnd6aG42bzJia3ZoN3Nsc3VneWRqOTZxb2VoaWFvbiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/2uBT7xAkEHN7Li92Hx/giphy.gif",
    "gif_tarot_card": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExdWZmMXRxYnp1a3J2MG5kMGI4ZnB3dDRqeDA2dzRsbTJ3NzhkcmFieCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/kPMo4aQUTLK5q/giphy.gif",
    "gif_white_card": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExbWQwYTI4YnpvOHluajZ1NDU5OWUwcTZoeHd3d3dzaDh4cDQ2d3duZCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/RZpPMhj1i59kLAg5Eo/giphy.gif",
}


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
        gif_message: Message
) -> Tuple[str, List[str], str, str]:
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

    try:
        parsed = parse_response(response, len(readable_names))
        card_descriptions = parsed[:-2]
        interpretation, advice = parsed[-2:]
    except FailedParseResponseException:
        cleaned_text = re.sub(r"<[^>]*>", "", response)
        card_descriptions = [""] * len(readable_names)
        interpretation, advice = find_or_insert_newline(cleaned_text)

    return response, card_descriptions, interpretation, advice


async def send_cards_and_descriptions(
        bot: Bot,
        user_tg_id: int,
        img_names: List[str],
        readable_names: List[str],
        card_descriptions: List[str],
        gif_message: Message
):
    for index, (name, caption, card_desc) in enumerate(zip(img_names, readable_names, card_descriptions)):
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


async def send_interpretation_and_advice(bot: Bot, user_tg_id: int, interpretation: str, advice: str):
    await bot.send_message(user_tg_id, interpretation)
    await calculate_reading_time(interpretation)
    await bot.send_message(user_tg_id, advice)
    await calculate_reading_time(advice)


async def start_tarot(
        bot: Bot,
        session: AsyncSession,
        question: str,
        user: User,
        num_cards: int
):
    gif_message = await send_gif_with_retry(bot, user.user_tg_id)

    async with ChatActionSender(bot=bot, action="typing", chat_id=user.user_tg_id):
        keys = random.sample(list(cards_list.keys()), num_cards)
        selected_cards = {key: cards_list[key] for key in keys}
        img_names = list(selected_cards.keys())
        readable_names = list(selected_cards.values())

        _, card_descriptions, interpretation, advice = await generate_and_save_reading(
            session, user, question, readable_names, img_names, bot, gif_message
        )
        await asyncio.sleep(LONG_SLEEP)

    await send_cards_and_descriptions(
        bot, user.user_tg_id, img_names, readable_names, card_descriptions, gif_message
    )
    await send_interpretation_and_advice(bot, user.user_tg_id, interpretation, advice)


async def start_1_tarot(bot: Bot, session: AsyncSession, question: str, user: User):
    await start_tarot(bot, session, question, user, 1)


async def start_3_tarot(bot: Bot, session: AsyncSession, question: str, user: User):
    await start_tarot(bot, session, question, user, 3)
