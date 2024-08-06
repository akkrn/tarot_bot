from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import FSInputFile, Message
import logging

from services.redis import get_file_id, save_file_id, delete_file_id

from exceptions import GifSendException

logger = logging.getLogger(__name__)


async def send_file(
    bot: Bot,
    file_path: str,
    redis_key: str,
    user_tg_id: int,
    caption: str,
    above: bool = False,
) -> Message: # TODO retry func to send file if ClientOSError
    """Send files to Telegam servers and collect file_id in Redis cache"""
    file_id = await get_file_id(redis_key)
    if file_id:
        try:
            result = await bot.send_photo(
                user_tg_id,
                photo=file_id,
                caption=caption,
                show_caption_above_media=above,
            )
            return result
        except TelegramAPIError:
            await delete_file_id(redis_key)
    try:
        image_from_pc = FSInputFile(file_path)
        result = await bot.send_photo(
            user_tg_id,
            photo=image_from_pc,
            caption=caption,
            show_caption_above_media=above,
        )
        file_id = result.photo[-1].file_id
        await save_file_id(redis_key, file_id)
        return result
    except Exception as e:
        logger.error(f"При отправке карты произошла ошибка: {e}")


async def send_gif(
    bot: Bot, gif_path: str, redis_key: str, user_tg_id: int
) -> Message:
    """Send gifs to Telegam servers and collect file_id in Redis cache"""
    file_id = await get_file_id(redis_key)
    if file_id:
        try:
            result = await bot.send_animation(user_tg_id, animation=file_id)
            return result
        except TelegramAPIError:
            await delete_file_id(redis_key)
    try:
        result = await bot.send_animation(user_tg_id, animation=gif_path)
        file_id = result.animation.file_id
        await save_file_id(redis_key, file_id)
        return result
    except Exception as e:
        logger.error(f"При отправке карты произошла ошибка: {e}")
        raise GifSendException

