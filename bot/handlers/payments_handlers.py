from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import PreCheckoutQuery, Message
from sqlalchemy import select
import logging

from lexicon.lexicon import LEXICON_RU
from loader import async_session
from models import User, Payment
from services.admin import send_to_admin
from services.tarot import start_1_tarot, start_3_tarot

from fsm_settings import AskState

from exceptions import FailedOpenAIGenerateError
from services.payments import refund

logger = logging.getLogger(__name__)

router = Router()

INVOICE_LIFETIME_SECONDS = 120


@router.pre_checkout_query()
async def on_pre_checkout_query(
    pre_checkout_query: PreCheckoutQuery, state: FSMContext
):
    current_time = int(datetime.now().timestamp())
    user_data = await state.get_data()
    invoice_timestamp = user_data.get("invoice_timestamp")
    question = user_data["question"]
    if not question:
        await pre_checkout_query.answer(
            ok=False, error_message=LEXICON_RU["payment_question_failure"]
        )
    if not invoice_timestamp or (
        current_time - invoice_timestamp > INVOICE_LIFETIME_SECONDS
    ):
        await pre_checkout_query.answer(
            ok=False, error_message=LEXICON_RU["payment_timestamp_failure"]
        )
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def on_successful_payment(
    message: Message,
    state: FSMContext,
):
    user_data = await state.get_data()
    question = user_data["question"]
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.user_tg_id == message.from_user.id)
        )
        user = result.scalar_one()
        payment_id = message.successful_payment.telegram_payment_charge_id
        new_payment = Payment(
            user_id=user.id,
            payment_id=payment_id,
            invoice_payload=message.successful_payment.invoice_payload,
            total_amount=message.successful_payment.total_amount,
        )
        session.add(new_payment)
        bot = message.bot
        if message.successful_payment.invoice_payload == "1_card":
            try:
                await start_1_tarot(bot, session, question, user)
            except FailedOpenAIGenerateError:
                await message.answer(text=LEXICON_RU["generate_error"])
                await refund(bot, user.user_tg_id, payment_id)
                new_payment.is_refunded = True
                await session.commit()
                await state.set_state(AskState.question)
                await message.answer(text=LEXICON_RU["new_question_after_error"])
                return
        elif message.successful_payment.invoice_payload == "3_card":
            try:
                await start_3_tarot(bot, session, question, user)
            except FailedOpenAIGenerateError:
                await message.answer(text=LEXICON_RU["generate_error"])
                await refund(bot, user.user_tg_id, payment_id)
                new_payment.is_refunded = True
                await session.commit()
                await state.set_state(AskState.question)
                await message.answer(text=LEXICON_RU["new_question_after_error"])
                return
        else:
            await send_to_admin(bot, message.text, user.user_tg_id)
        await session.commit()
        await state.set_state(AskState.question)
        await message.answer(text=LEXICON_RU["ask_new_question"])


@router.message(F.refunded_payment)
async def on_refunded_payment(
        message: Message,
):
    pass

@router.message(Command("paysupport"))
async def cmd_paysupport(
    message: Message,
):
    await message.answer(LEXICON_RU["paysupport"])
