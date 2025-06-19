from datetime import datetime

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
)
import logging

from aiogram.utils.keyboard import InlineKeyboardBuilder
from constants import PRICE_1_CARD_RUB, PRICE_3_CARD_RUB
from services.admin import send_to_admin
from lexicon.lexicon import LEXICON_RU
from loader import payments_provider_token

logger = logging.getLogger(__name__)


async def build_payment_invoice(
    bot: Bot, callback: CallbackQuery, state: FSMContext, currency: str = "XTR", manual_amount: int | None = None,
) -> None:
    """Generate a payment invoice for a selected tarot card reading
    and sends it to the user with an option to pay."""

    card_type = callback.data
    now = int(datetime.now().timestamp())

    card_options = {
        "one_card": {
            "title": "Расклад на 1 карту",
            "description": LEXICON_RU["description_1_card"],
            "amount_xtr": 50,
            "payload": "1_card",
        },
        "three_card": {
            "title": "Расклад на 3 карты",
            "description": LEXICON_RU["description_3_card"],
            "amount_xtr": 75,
            "payload": "3_card",
        },
    }

    option = card_options.get(card_type, None)
    builder = InlineKeyboardBuilder()
    if currency == "XTR" and option:
        price = option["amount_xtr"]
        currency_code = "XTR"
        provider_token = ""
        payload = option["payload"]
        title = option["title"]
        description = option["description"]
        button_text = f"{title} - {price} {currency_code}"

    elif currency == "RUB":
        price = manual_amount * 100
        title = "Пополнение баланса"
        description = f"Стоимость расклада на 1 карту - {PRICE_1_CARD_RUB}руб\nНа три - {PRICE_3_CARD_RUB}руб"
        currency_code = "RUB"
        provider_token = payments_provider_token
        payload = "balance_topup"
        button_text = f"{title} на {price/100} {currency_code}"
    else:
        await send_to_admin(bot, currency, callback.from_user.id)
        logger.error("Неизвестная валюта.")
        return
    
    builder.button(
        text=button_text,
        pay=True
    )
    builder.button(text="Назад", callback_data="cancel_payment")
    builder.adjust(1)


    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=title,
        description=description,
        prices=[LabeledPrice(label=currency_code, amount=price)],
        provider_token=provider_token,
        payload= payload,
        currency=currency_code,
        reply_markup=builder.as_markup(),
    )

    await state.update_data(invoice_timestamp=now)


async def refund(bot: Bot, user_id: int, payment_id: str):
    if payment_id is None:
        await bot.send_message(user_id, LEXICON_RU["no_payment_id"])
        return
    try:
        await bot.refund_star_payment(
            user_id=user_id, telegram_payment_charge_id=payment_id
        )
        await bot.send_message(user_id, LEXICON_RU["refund"])
    except TelegramBadRequest as error:
        if "CHARGE_NOT_FOUND" in error.message:
            text = LEXICON_RU["refund_not_found"]
        elif "CHARGE_ALREADY_REFUNDED" in error.message:
            text = LEXICON_RU["refund_already_done"]
        else:
            text = LEXICON_RU["no_payment_id"]
        await bot.send_message(user_id, text)
