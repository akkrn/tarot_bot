import whisper
import logging

import httpx
from openai import AsyncOpenAI

from loader import (
    openai_api_key,
    openai_engine,
    user_1_card_promt,
    user_3_card_promt,
    max_tokens,
    proxy_path,
)

logger = logging.getLogger(__name__)


async def ask_deepseek(question: str, card_name: list) -> str:
    """Generate text by Deepseek"""
    http_client = httpx.AsyncClient(
        transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0"),
    )
    client = AsyncOpenAI(
        api_key=openai_api_key,
        http_client=http_client,
        base_url="https://api.deepseek.com",
    )
    if len(card_name) == 1:
        SYSTEM_PROMPT = user_1_card_promt
        prompt = f"Вопрос пользователя: {question}\nКарта: {card_name}"
    elif len(card_name) == 3:
        SYSTEM_PROMPT = user_3_card_promt
        prompt = (
            f"Вопрос пользователя: {question}\nКарты: {', '.join(card_name)}\n"
        )
    else:
        raise ValueError("card_name must be str or list")
    try:
        chat_completion = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            model=openai_engine,
            max_tokens=max_tokens,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Ошибка при запросе к GPT: {e}")
        raise Exception
    finally:
        await http_client.aclose()


async def transcribe_voice_message(file_path):
    """OpenAI Speech To Text request"""
    try:
        model = whisper.load_model("small")

        audio = whisper.load_audio(file_path)
        audio = whisper.pad_or_trim(audio)
        mel = whisper.log_mel_spectrogram(audio).to(model.device)
        options = whisper.DecodingOptions(language='ru', without_timestamps = True, fp16 = False)
        result = whisper.decode(model, mel, options)

        #result = model.transcribe(file_path)
        return result.text
    except Exception as e:
        logger.error(
            f"При обработке голосового сообщения возникла ошибка: {e}"
        )

