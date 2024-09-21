from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from lexicon.lexicon import LEXICON_RU
from services.utils import delete_warning

from loader import async_session
from models import Question
from sqlalchemy import update

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


@router.message()
async def error_message(message: Message):
    await delete_warning(message, LEXICON_RU["not_handled_message"])
    await message.answer(text=LEXICON_RU["help_start_command"])
