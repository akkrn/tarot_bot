import asyncio
import datetime
import logging

from aiogram import F, Router
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from filters.filters import IsValidDateFilter
from fsm_settings import StartForm, AskState
from loader import async_session
from models import User
from services.payments import build_payment_invoice
from services.tarot import start_1_tarot, start_3_tarot
from services.utils import create_inline_kb, parse_birth_date
from services.audio_transcribe import prepare_voice_message

from lexicon.lexicon import LEXICON_RU

router = Router()
logger = logging.getLogger(__name__)

SLEEP_TIME_ANSWER = 2
SLEEP_TIME_WARNING = 4


async def delete_warning(message: Message, text: str) -> None:
    """Delete useless messages from user with warnings"""
    bot_message = await message.answer(text=text)
    await asyncio.sleep(SLEEP_TIME_WARNING)
    await message.delete()
    await bot_message.delete()


@router.message(
    CommandStart(), ~StateFilter(StartForm.name, StartForm.birth_date)
)
async def process_start_command(message: Message, state: FSMContext):
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.user_tg_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        if not user:
            new_user = User(
                user_tg_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                added_at=datetime.datetime.now(),
            )
            session.add(new_user)
            await session.commit()
            await message.answer(text=LEXICON_RU["/start"])
            await asyncio.sleep(5)
            await message.answer(text=LEXICON_RU["help_start_command"])
            await asyncio.sleep(3)
            await message.answer(text=LEXICON_RU["make_friend"])
            await state.set_state(StartForm.name)
            await asyncio.sleep(3)
        else:
            await message.answer(text=LEXICON_RU["let_ask_question"])
            await state.set_state(AskState.question)


@router.message(
    CommandStart(), StateFilter(StartForm.name, StartForm.birth_date)
)
async def unprocess_start_command(message: Message, state: FSMContext):
    await delete_warning(message, LEXICON_RU["let_finish_form"])


@router.message(F.text.len() < 200, StateFilter(StartForm.name))
async def process_form_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(text=LEXICON_RU["ask_birth_date"])
    await state.set_state(StartForm.birth_date)


@router.message(StateFilter(StartForm.name))
async def error_form_name(message: Message):
    await delete_warning(message, LEXICON_RU["wrong_name_input"])


@router.message(IsValidDateFilter(), StateFilter(StartForm.birth_date))
async def process_form_birth_date(message: Message, state: FSMContext):
    user_data = await state.get_data()
    birth_date = parse_birth_date(message.text)
    async with async_session() as session:
        user = await session.execute(
            select(User).where(User.user_tg_id == message.from_user.id)
        )
        user = user.scalar_one()
        user.real_name = user_data["name"]
        user.birth_date = birth_date
        await session.commit()
    await message.answer(text=LEXICON_RU["finish_form"])
    await asyncio.sleep(1)
    await message.answer(text=LEXICON_RU["let_ask_question"])
    await state.set_state(AskState.question)


@router.message(StateFilter(StartForm.birth_date))
async def error_form_birth_date(message: Message):
    await delete_warning(message, LEXICON_RU["wrong_birth_date_input"])


@router.message(F.text, StateFilter(AskState.question))
async def process_ask_question(message: Message, state: FSMContext):
    await state.update_data(question=message.text)
    keyboard = create_inline_kb(
        2,
        "one_card",
        "three_card",
        "new_question",
    )
    await message.answer(text=LEXICON_RU["choose_type"], reply_markup=keyboard)
    await state.set_state(AskState.choose_type)


@router.message(F.voice, StateFilter(AskState.question))
async def process_voice_question(message: Message, state: FSMContext):
    question = await prepare_voice_message(message)
    if not question:
        await delete_warning(message, LEXICON_RU["error_voice_transcribe"])
        return
    await state.update_data(question=question)
    keyboard = create_inline_kb(
        2,
        "one_card",
        "three_card",
        "new_question",
    )
    await message.answer(text=LEXICON_RU["choose_type"], reply_markup=keyboard)
    await state.set_state(AskState.choose_type)


@router.callback_query(
    F.data.in_(["one_card", "three_card", "new_question"]),
    StateFilter(AskState.choose_type),
)
async def process_choose_type(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    question = user_data["question"]
    bot = callback.bot
    if callback.data == "one_card" or callback.data == "three_card":
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.user_tg_id == callback.from_user.id)
            )
            try:
                user = result.scalar_one()
                if user.balance:
                    if callback.data == "one_card":
                        balance = user.balance - 1
                        await callback.message.delete()
                        await start_1_tarot(bot, session, question, user)
                    elif callback.data == "three_card":
                        balance = user.balance - 1
                        await callback.message.delete()
                        await start_3_tarot(bot, session, question, user)
                    user.balance = balance
                    await session.commit()
                    await asyncio.sleep(15)
                else:
                    await state.set_state(AskState.payment)
                    await build_payment_invoice(callback, state)
                    return
                await state.set_state(AskState.question)
                await callback.message.answer(
                    text=LEXICON_RU["ask_new_question"]
                )
            except Exception as e:
                logger.error(e)
    elif callback.data == "new_question":
        await state.set_state(AskState.question)
        await callback.message.delete()
        await callback.message.answer(text=LEXICON_RU["let_ask_question"])


@router.callback_query(
    F.data.in_(["cancel_payment"]), StateFilter(AskState.payment)
)
async def cancel_payment(callback: CallbackQuery, state: FSMContext):
    keyboard = create_inline_kb(
        2,
        "one_card",
        "three_card",
        "new_question",
    )
    await callback.message.delete()
    await callback.message.answer(
        text=LEXICON_RU["choose_type"], reply_markup=keyboard
    )
    await state.set_state(AskState.choose_type)


@router.message()
async def error_message(message: Message):
    await delete_warning(message, LEXICON_RU["not_handled_message"])
    await message.answer(text=LEXICON_RU["help_start_command"])
