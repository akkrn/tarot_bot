from typing import Union

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import update

from fsm_settings import AskState, PaymentState
from handlers.tarot_handlers import process_ask_question
from lexicon.lexicon import LEXICON_RU
from loader import async_session
from models import Question
from services.utils import delete_warning

router = Router()


@router.callback_query(
    F.data.startswith("thumb_up") | F.data.startswith("thumb_down")
)
async def process_feedback(callback: CallbackQuery):
    rate, question_id = callback.data.split("_")[1:]
    async with async_session() as session:
        stmt = (
            update(Question)
            .where(Question.id == int(question_id))
            .values(rating=1 if rate == "up" else -1)
        )
        await session.execute(stmt)
        await session.commit()
        response_text = (
            LEXICON_RU["positive_feedback"]
            if rate == "up"
            else LEXICON_RU["negative_feedback"]
        )
        await callback.answer()
        await callback.message.edit_text(response_text)


@router.callback_query(F.data.in_(["back"]))
@router.callback_query(
    F.data.in_(["cancel_payment"]),
    StateFilter(PaymentState.payment, PaymentState.choosing_payment_method),
)
async def back_to_question(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AskState.question)
    user_data = await state.get_data()
    await callback.message.delete()
    fake_message = callback.message.model_copy(
        update={"text": user_data["question"]}
    )
    fake_message._bot = callback.bot
    await process_ask_question(fake_message, state)


@router.callback_query(StateFilter(AskState.proccess))
@router.message(StateFilter(AskState.proccess))
async def procces_tarot_message(event: Union[Message, CallbackQuery]):
    message_obj = event if isinstance(event, Message) else event.message
    await delete_warning(message_obj, LEXICON_RU["proccess_tarot_message"])


@router.message()
async def error_message(message: Message):
    await delete_warning(message, LEXICON_RU["not_handled_message"])
    await message.answer(text=LEXICON_RU["help_start_command"])
