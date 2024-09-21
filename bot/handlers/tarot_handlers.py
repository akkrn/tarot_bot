import asyncio
import logging

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from constants import LONG_SLEEP, SHORT_SLEEP
from exceptions import FailedOpenAIGenerateError
from fsm_settings import AskState
from lexicon.lexicon import LEXICON_RU
from loader import async_session
from models import User
from services.audio_transcribe import prepare_voice_message
from services.payments import build_payment_invoice
from services.tarot import start_1_tarot, start_3_tarot
from services.utils import create_inline_kb, delete_warning


router = Router()
logger = logging.getLogger(__name__)


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
                    await callback.answer()
                    if callback.data == "one_card":
                        balance = user.balance - 1
                        await callback.message.delete()
                        try:
                            question_id = await start_1_tarot(
                                bot, session, question, user
                            )
                        except FailedOpenAIGenerateError:
                            await callback.message.answer(
                                text=LEXICON_RU["generate_error"]
                            )
                            await state.set_state(AskState.question)
                            await callback.message.answer(
                                text=LEXICON_RU["new_question_after_error"]
                            )
                            return
                    elif callback.data == "three_card":
                        balance = user.balance - 1
                        await callback.message.delete()
                        try:
                            question_id = await start_3_tarot(
                                bot, session, question, user
                            )
                        except FailedOpenAIGenerateError:
                            await callback.message.answer(
                                text=LEXICON_RU["generate_error"]
                            )
                            await state.set_state(AskState.question)
                            await callback.message.answer(
                                text=LEXICON_RU["new_question_after_error"]
                            )
                            return
                    user.balance = balance
                    await session.commit()
                    await asyncio.sleep(LONG_SLEEP)
                    await state.set_state(AskState.question)

                    keyboard = create_inline_kb(
                        2,
                        **{
                            f"thumb_up_{question_id}": "👍",
                            f"thumb_down_{question_id}": "👎",
                        },
                    )
                    await callback.message.answer(
                        text=LEXICON_RU["feedback_please"],
                        reply_markup=keyboard,
                    )
                    await asyncio.sleep(SHORT_SLEEP)
                    await callback.message.answer(
                        text=LEXICON_RU["ask_new_question"]
                    )
                else:
                    await callback.answer()
                    await state.set_state(AskState.payment)
                    await callback.message.delete()
                    await build_payment_invoice(bot, callback, state)
                    return
            except Exception as e:
                logger.error(e)
    elif callback.data == "new_question":
        await state.set_state(AskState.question)
        await callback.message.delete()
        await callback.message.answer(text=LEXICON_RU["let_ask_question"])
