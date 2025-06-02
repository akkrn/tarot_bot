import os
from datetime import datetime

from aiogram.types import Message
from services.openai import transcribe_voice_message
from loader import images_path


async def prepare_voice_message(message: Message) -> str | None:
    """Process a voice message, transcribe it to text, and return the transcribed text."""
    bot = message.bot
    unix_time = int(datetime.now().timestamp())
    file_name = f"{message.from_user.id}_{unix_time}.ogg"
    file_ogg_path = images_path + file_name
    file_info = await bot.get_file(message.voice.file_id)
    await bot.download_file(file_info.file_path, file_ogg_path)
    try:
        if os.path.exists(file_ogg_path):
            question = await transcribe_voice_message(file_ogg_path)
        else:
            question = None
    finally:
        if os.path.exists(file_ogg_path):
            os.remove(file_ogg_path)

    return question


# async def convert_ogg_to_mp3(input_file: str) -> str:
#     """Convert files ogg -> mp3"""
#     mp3_file_path = input_file.replace(".ogg", ".mp3")
#     loop = asyncio.get_event_loop()
#     await loop.run_in_executor(None, lambda: AudioSegment.from_ogg(input_file).export(mp3_file_path, format="mp3"))
#     return mp3_file_path
