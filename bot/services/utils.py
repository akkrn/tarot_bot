import asyncio
import re
from datetime import datetime
import logging

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from lexicon.lexicon import LEXICON_RU
from exceptions import FailedParseResponseException

logger = logging.getLogger(__name__)


# Функция для формирования инлайн-клавиатуры на лету
def create_inline_kb(
    width: int, *args: str, **kwargs: str
) -> InlineKeyboardMarkup:
    kb_builder: InlineKeyboardBuilder = InlineKeyboardBuilder()
    buttons: list[InlineKeyboardButton] = []
    if args:
        for button in args:
            buttons.append(
                InlineKeyboardButton(
                    text=(
                        LEXICON_RU[button] if button in LEXICON_RU else button
                    ),
                    callback_data=button,
                )
            )
    if kwargs:
        for button, text in kwargs.items():
            buttons.append(
                InlineKeyboardButton(text=text, callback_data=button)
            )

    kb_builder.row(*buttons, width=width)
    return kb_builder.as_markup()


def convert_to_float(amount_str: str) -> float:
    clean_str = "".join(
        filter(lambda x: x.isdigit() or x in [",", "."], amount_str)
    )
    if "." in clean_str and "," in clean_str:
        if clean_str.find(".") < clean_str.find(","):
            clean_str = clean_str.replace(".", "").replace(",", ".")
        else:
            clean_str = clean_str.replace(",", "")
    else:
        clean_str = clean_str.replace(",", ".")

    return float(clean_str)


def parse_response(response, num_cards=1):
    try:
        card_descriptions = []
        interpretations = []
        advices = []

        if num_cards == 1:
            card_pattern = re.compile(
                r"<карта> (.*?)(?=<|$)", re.DOTALL | re.IGNORECASE
            )
            card_match = card_pattern.search(response)
            card_descriptions.append(card_match.group(1).strip())
        else:
            for i in range(1, num_cards + 1):
                card_pattern = re.compile(
                    rf"<карта {i}> (.*?)(?=<|$)", re.DOTALL | re.IGNORECASE
                )
                card_match = card_pattern.search(response)
                card_descriptions.append(card_match.group(1).strip())
        interpretation_pattern = re.compile(
            r"<интерпретация> (.*?)(?=<|$)", re.DOTALL | re.IGNORECASE
        )
        advice_pattern = re.compile(
            r"<совет> (.*?)(?=<|$)", re.DOTALL | re.IGNORECASE
        )

        interpretation_match = interpretation_pattern.search(response)
        advice_match = advice_pattern.search(response)

        if not card_match or not interpretation_match or not advice_match:
            logger.debug(f"Неверный формат ответа для карты: {response}")
            raise FailedParseResponseException

        interpretations.append(interpretation_match.group(1).strip())
        advices.append(advice_match.group(1).strip())

        return *card_descriptions, *interpretations, *advices

    except Exception:
        logger.debug(f"Ошибка при разборе карты: {response}")
        raise FailedParseResponseException


def parse_birth_date(date_str: str) -> datetime:
    date_formats = [
        "%d.%m.%Y",
        "%d,%m,%Y",
        "%d-%m-%Y",
        "%d  %m  %Y",
        "%d%m%Y",
        "%d/%m/%Y",
    ]
    for date_format in date_formats:
        try:
            return datetime.strptime(date_str, date_format)
        except ValueError:
            continue


def find_or_insert_newline(text: str) -> [str, str]:
    mid_index = len(text) // 2
    if "\n" in text:
        newline_indices = [i for i, char in enumerate(text) if char == "\n"]
        closest_newline = min(
            newline_indices, key=lambda x: abs(x - mid_index)
        )
        return text[: closest_newline + 1], text[closest_newline + 1 :]
    else:
        return text, "\n"


async def calculate_reading_time(message: str) -> None:
    """Calculate time for asyncio.sleep() based on length of text"""
    chars_per_second = 50  # Скорость чтения в символах в секунду
    reading_coefficient = (
        1.15  # Коэффициент для добавления дополнительного времени
    )
    num_chars = len(message)
    base_time = num_chars / chars_per_second
    adjusted_time = base_time * reading_coefficient
    await asyncio.sleep(adjusted_time)
