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
from services.admin import send_to_admin
from lexicon.lexicon import LEXICON_RU

logger = logging.getLogger(__name__)

# AMOUNT = [50, 100]
AMOUNT = [1, 1]


async def build_payment_invoice(
    bot: Bot, callback: CallbackQuery, state: FSMContext
) -> None:
    """Generate a payment invoice for a selected tarot card reading
    and sends it to the user with an option to pay."""
    builder = InlineKeyboardBuilder()
    card_type = callback.data
    card_options = {
        "one_card": {
            "button_text": f"Расклад на 1 карту - {AMOUNT[0]} XTR",
            "prices": [LabeledPrice(label="XTR", amount=AMOUNT[0])],
            "title": "Расклад на 1 карту",
            "payload": "1_card",
            "description": LEXICON_RU["description_1_card"],
        },
        "three_card": {
            "button_text": f"Расклад на 3 карты - {AMOUNT[1]} XTR",
            "prices": [LabeledPrice(label="XTR", amount=AMOUNT[1])],
            "title": "Расклад на 3 карты",
            "payload": "3_card",
            "description": LEXICON_RU["description_3_card"],
        },
    }

    if card_type in card_options:
        options = card_options[card_type]
        builder.button(text=options["button_text"], pay=True)
        prices = options["prices"]
        title = options["title"]
        payload = options["payload"]
        description = options["description"]
    else:
        await send_to_admin(bot, callback.message.text, callback.from_user.id)
        logger.error("Unknown card type")
        return

    builder.button(text="Назад", callback_data="cancel_payment")
    builder.adjust(1)

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=title,
        description=description,
        prices=prices,
        provider_token="",
        payload=payload,
        currency="XTR",
        reply_markup=builder.as_markup(),
    )
    await state.update_data(invoice_timestamp=int(datetime.now().timestamp()))


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
