import io
import os

import aiofiles
import logging

import httpx
from openai import AsyncOpenAI

from loader import (
    openai_api_key,
    user_1_card_promt,
    user_3_card_promt,
    max_tokens,
    proxy_path
)

logger = logging.getLogger(__name__)


async def ask_openai(question: str, card_name: str | list) -> str:
    """Generate text by ChatGPT request"""
    http_client = httpx.AsyncClient(proxies=proxy_path, transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0"))
    client = AsyncOpenAI(
        api_key=openai_api_key,
        http_client=http_client,

    )

    if len(card_name) == 1:
        SYSTEM_PROMPT = user_1_card_promt
        prompt = f"Вопрос пользователя: {question}\nКарта: {card_name}"
    elif len(card_name) == 3:
        SYSTEM_PROMPT = user_3_card_promt
        prompt = f"Вопрос пользователя: {question}\nКарта: {card_name[0]}\n"
    else:
        raise ValueError("card_name must be str or list")
    try:
        chat_completion = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            model="gpt-4o-mini",
            max_tokens=max_tokens,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        logger.error(
            f"Ошибка при запросе к GPT: {e}"
        )
    finally:
        await http_client.aclose()


async def transcribe_voice_message(file_path):
    """OpenAI Speech To Text request"""
    http_client = httpx.AsyncClient(proxies=proxy_path, transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0"))

    client = AsyncOpenAI(api_key=openai_api_key, http_client=http_client)
    try:
        async with aiofiles.open(file_path, "rb") as f:
            file_content = await f.read()
            buffer = io.BytesIO(file_content)
            buffer.name = os.path.basename(file_path)

            transcription = await client.audio.transcriptions.create(
                model="whisper-1", file=buffer
            )
            return transcription.text
    except Exception as e:
        logger.error(
            f"При обработке голосового сообщения возникла ошибка: {e}"
        )
    finally:
        await http_client.aclose()
