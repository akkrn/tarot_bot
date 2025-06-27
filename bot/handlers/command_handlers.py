import asyncio
import base64
import datetime
import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from constants import (MIDDLE_SLEEP, PRICE_1_CARD_RUB, PRICE_1_CARD_XTR,
                       PRICE_3_CARD_RUB, PRICE_3_CARD_XTR, REFERRAL_BONUS,
                       SHORT_SLEEP)
from fsm_settings import AskState, PaymentState, StartForm
from lexicon.lexicon import LEXICON_RU
from loader import async_session
from models import User
from services.profile import get_profile_info
from services.utils import create_inline_kb, delete_warning

router = Router()
logger = logging.getLogger(__name__)


@router.message(
    CommandStart(), ~StateFilter(StartForm.name, StartForm.birth_date)
)
async def cmd_start(
    message: Message, state: FSMContext, command: CommandObject
):
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.user_tg_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        if (
            not user
        ):  # TODO если в бд статус BANNED, то добавлять префикс для id пользователя,
            # чтобы при повторном запуске анкета была пустая
            # но данные все равно сохранялись, либо сделать отдельную таблицу, где id пользователя не будет уникальным
            # и переносить данные при бане бота в отдельную таблицу
            link_args = command.args
            new_user = User(
                user_tg_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                added_at=datetime.datetime.now(),
            )
            if link_args:
                try:
                    referrer_id = int(
                        base64.urlsafe_b64decode(link_args).decode()
                    )
                    result = await session.execute(
                        select(User).where(User.user_tg_id == referrer_id)
                    )
                    referrer_user = result.scalar_one_or_none()
                    if referrer_user:
                        new_user.referrer_id = referrer_user.id
                        bot = message.bot
                        referrer_user.free_attempts += REFERRAL_BONUS
                        try:
                            await bot.send_message(
                                referrer_id, LEXICON_RU["enter_new_friend"]
                            )
                        except Exception as e:
                            logger.error(
                                f"Ошибка при отправлении сообщения рефералу, ошибка: {e}"
                            )
                except Exception as e:
                    logger.error(
                        f"Ошибка при добавлении реферала, ошибка: {e}"
                    )
            session.add(new_user)
            await session.commit()
            await message.answer(text=LEXICON_RU["/start"])
            await asyncio.sleep(MIDDLE_SLEEP)
            await message.answer(text=LEXICON_RU["help_start_command"])
            await asyncio.sleep(SHORT_SLEEP)
            await message.answer(text=LEXICON_RU["make_friend"])
            await state.set_state(StartForm.name)
            await asyncio.sleep(SHORT_SLEEP)
        else:
            await message.answer(text=LEXICON_RU["let_ask_question"])
            await state.set_state(AskState.question)


@router.message(
    CommandStart(), StateFilter(StartForm.name, StartForm.birth_date)
)
async def cmd_start_form(message: Message, state: FSMContext):
    await delete_warning(message, LEXICON_RU["let_finish_form"])


@router.message(Command("referral"))
async def cmd_referral(message: Message):
    encoded_id = base64.urlsafe_b64encode(
        str(message.from_user.id).encode()
    ).decode()
    bot_username = message.bot._me.username
    referral_link = (
        LEXICON_RU["referral_link"]
        + f"`https://t.me/{bot_username}?start={encoded_id}`"
    )
    await message.answer(referral_link)


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    async with async_session() as session:
        response_text = await get_profile_info(session, message.from_user.id)
        await message.answer(response_text, parse_mode="HTML")


@router.message(Command("paysupport"))
async def cmd_paysupport(
    message: Message,
):
    await message.answer(LEXICON_RU["paysupport"])


@router.message(Command("topup"))
async def command_topup(message: Message, state: FSMContext):
    keyboard = create_inline_kb(
        2,
        pay_100="100₽",
        pay_200="200₽",
        pay_500="500₽",
        pay_1000="1000₽",
        pay_custom="Другая сумма",
        back="Назад",
    )
    await state.set_state(PaymentState.choosing_amount)
    await message.answer("Выберите сумму пополнения:", reply_markup=keyboard)


@router.message(Command("price"))
async def command_price(message: Message, state: FSMContext):
    await message.answer(
        f"*Cтоимость раскладов:*\n\nНа 1 карту - {PRICE_1_CARD_RUB}₽ (или {PRICE_1_CARD_XTR} звёзд)\n"
        f"На 3 карты - {PRICE_3_CARD_RUB}₽ (или {PRICE_3_CARD_XTR} звёзд)\n"
    )
