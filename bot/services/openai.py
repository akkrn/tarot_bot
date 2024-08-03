import io
import os

import aiofiles
import logging

from openai import AsyncOpenAI

from loader import (
    openai_api_key,
    user_1_card_promt,
    user_3_card_promt,
    max_tokens,
)

logger = logging.getLogger(__name__)


async def ask_openai(question: str, card_name: str | list) -> str:
    """Generate text by ChatGPT request"""
    if isinstance(card_name, str):
        SYSTEM_PROMPT = user_1_card_promt
        prompt = f"Вопрос пользователя: {question}\nКарта: {card_name}"
    elif isinstance(card_name, list):
        SYSTEM_PROMPT = user_3_card_promt
        prompt = f"Вопрос пользователя: {question}\nКарта: {card_name[0]}\n"
    else:
        raise ValueError("card_name must be str or list")

    client = AsyncOpenAI(api_key=openai_api_key)
    chat_completion = await client.chat.completions.create(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        model="gpt-4o-mini",
        max_tokens=max_tokens,
    )
    return chat_completion.choices[0].message.content


async def transcribe_voice_message(file_path):
    """OpenAI Speech To Text request"""
    client = AsyncOpenAI(api_key=openai_api_key)
    try:
        async with aiofiles.open(file_path, "rb") as f:
            file_content = await f.read()
            buffer = io.BytesIO(file_content)
            buffer.name = os.path.basename(file_path)

            transcription = await client.audio.transcriptions.create(
                model="whisper-1", file=buffer
            )
    except Exception as e:
        logger.error(
            f"При обработке голосового сообщения возникла ошибка: {e}"
        )
    return transcription.text
