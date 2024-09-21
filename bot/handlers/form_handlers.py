import asyncio
import logging

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from filters.filters import IsValidDateFilter
from fsm_settings import StartForm, AskState
from lexicon.lexicon import LEXICON_RU
from loader import async_session
from models import User
from services.utils import delete_warning, parse_birth_date

router = Router()
logger = logging.getLogger(__name__)


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
