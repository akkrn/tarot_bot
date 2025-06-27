import asyncio
import logging
from datetime import datetime
from typing import Optional

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery
from sqlalchemy import select

from constants import (INVOICE_LIFETIME_SECONDS, MINIMAL_TOPUP_VALUE,
                       SHORT_SLEEP)
from exceptions import FailedOpenAIGenerateError
from fsm_settings import AskState, PaymentState
from handlers.command_handlers import command_topup
from lexicon.lexicon import LEXICON_RU
from loader import async_session
from models import Payment, User
from services.admin import send_to_admin
from services.payments import build_payment_invoice, refund
from services.tarot import start_1_tarot, start_3_tarot
from services.utils import create_inline_kb, delete_warning

logger = logging.getLogger(__name__)
router = Router()


async def process_tarot_question(
    bot, session, user, question: str, invoice_payload: str
) -> Optional[int]:
    try:
        if invoice_payload == "1_card":
            return await start_1_tarot(bot, session, question, user)
        elif invoice_payload == "3_card":
            return await start_3_tarot(bot, session, question, user)
    except FailedOpenAIGenerateError:
        return None


async def handle_generation_failure(
    bot, message, state, payment_id=None, user=None
):
    await message.answer(text=LEXICON_RU["generate_error"])
    if payment_id and user:
        await refund(bot, user.user_tg_id, payment_id)
    await state.set_state(AskState.question)
    await message.answer(text=LEXICON_RU["new_question_after_error"])


@router.callback_query(
    F.data == "top_up_balance",
    StateFilter(PaymentState.choosing_payment_method),
)
async def topup_balance(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await command_topup(callback.message, state)


@router.callback_query(
    F.data == "pay_by_stars", StateFilter(PaymentState.choosing_payment_method)
)
async def pay_with_invoice(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    payload = user_data["payment_type"]
    await callback.message.delete()
    await build_payment_invoice(callback.bot, callback, state, payload=payload)


@router.callback_query(
    F.data.startswith("pay_"), StateFilter(PaymentState.choosing_amount)
)
async def pay_selected_amount(callback: CallbackQuery, state: FSMContext):
    data = callback.data
    if data == "pay_custom":
        await state.set_state(PaymentState.entering_custom_amount)
        await callback.message.edit_text(
            f"Введите сумму в рублях (минимум {MINIMAL_TOPUP_VALUE}):"
        )
    else:
        amount = int(data.split("_")[1])
        await callback.message.delete()
        await build_payment_invoice(
            callback.bot, callback, state, currency="RUB", manual_amount=amount
        )


@router.message(StateFilter(PaymentState.entering_custom_amount))
async def handle_custom_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
        if amount < MINIMAL_TOPUP_VALUE:
            raise ValueError

        class FakeCallback:
            def __init__(self, user_id):
                self.data = "balance_topup"
                self.from_user = type("User", (), {"id": user_id})()
                self.message = message

        fake_cb = FakeCallback(message.from_user.id)
        await build_payment_invoice(
            message.bot, fake_cb, state, currency="RUB", manual_amount=amount
        )
    except ValueError:
        await delete_warning(
            message,
            f"Введите корректное число от {MINIMAL_TOPUP_VALUE} и выше.",
        )


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
        return

    if not invoice_timestamp or (
        current_time - invoice_timestamp > INVOICE_LIFETIME_SECONDS
    ):
        await pre_checkout_query.answer(
            ok=False, error_message=LEXICON_RU["payment_timestamp_failure"]
        )
        return

    await pre_checkout_query.answer(ok=True)


@router.message(
    F.successful_payment
)  # TODO Сделать рефакторинг, чтобы не было двух одинаковых методов в двух разных местах
async def on_successful_payment(
    message: Message,
    state: FSMContext,
):
    await state.set_state(AskState.proccess)
    user_data = await state.get_data()
    question = user_data["question"]

    invoice_message_id = user_data.get("invoice_message_id")
    if invoice_message_id:
        try:
            await message.bot.delete_message(
                chat_id=message.chat.id, message_id=invoice_message_id
            )
        except Exception as e:
            logger.warning(f"Не удалось удалить инвойс: {e}")

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.user_tg_id == message.from_user.id)
        )
        user = result.scalar_one()
        payment_id = message.successful_payment.telegram_payment_charge_id
        currency_data = message.successful_payment.currency
        currency = (
            currency_data
            if isinstance(currency_data, str)
            else currency_data[0]
        )

        new_payment = Payment(
            user_id=user.id,
            payment_id=payment_id,
            currency=currency,
            invoice_payload=message.successful_payment.invoice_payload,
            total_amount=(
                message.successful_payment.total_amount / 100
                if currency != "XTR"
                else message.successful_payment.total_amount
            ),
        )
        session.add(new_payment)
        bot = message.bot
        if message.successful_payment.invoice_payload == "balance_topup":
            amount_rub = message.successful_payment.total_amount // 100
            user.balance_rub += amount_rub
            await message.answer(
                f"Баланс успешно пополнен на {amount_rub}₽.\n\nТекущий баланс: {user.balance_rub}₽"
            )
            await state.set_state(AskState.question)
            await session.commit()
            return

        elif message.successful_payment.invoice_payload == "1_card":
            try:
                question_id = await start_1_tarot(bot, session, question, user)
            except FailedOpenAIGenerateError:
                await message.answer(text=LEXICON_RU["generate_error"])
                await refund(bot, user.user_tg_id, payment_id)
                new_payment.is_refunded = True
                await session.commit()
                await state.set_state(AskState.question)
                await message.answer(
                    text=LEXICON_RU["new_question_after_error"]
                )
                return
        elif message.successful_payment.invoice_payload == "3_card":
            try:
                question_id = await start_3_tarot(bot, session, question, user)
            except FailedOpenAIGenerateError:
                await message.answer(text=LEXICON_RU["generate_error"])
                await refund(bot, user.user_tg_id, payment_id)
                new_payment.is_refunded = True
                await session.commit()
                await state.set_state(AskState.question)
                await message.answer(
                    text=LEXICON_RU["new_question_after_error"]
                )
                return
        else:
            await send_to_admin(bot, message.text, user.user_tg_id)
        await session.commit()
        await state.set_state(AskState.question)
        keyboard = create_inline_kb(
            2,
            **{
                f"thumb_up_{question_id}": "👍",
                f"thumb_down_{question_id}": "👎",
            },
        )
        await message.answer(
            text=LEXICON_RU["feedback_please"], reply_markup=keyboard
        )
        await asyncio.sleep(SHORT_SLEEP)
        await message.answer(text=LEXICON_RU["ask_new_question"])


@router.message(F.refunded_payment)
async def on_refunded_payment(
    message: Message,
):
    pass


@router.callback_query(
    F.data.in_(["cancel_payment"]),
    StateFilter(
        PaymentState.choosing_amount, PaymentState.entering_custom_amount
    ),
)
async def cancel_payment(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await command_topup(callback.message, state)
