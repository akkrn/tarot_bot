from aiogram import Bot

from loader import owner_id
from models import User


async def send_to_admin(bot: Bot, message: str, user: User):
    await bot.send_message(
        chat_id=owner_id,
        text=f"Пользователь {user.user_tg_id} отправил сообщение: {message.text}",
    )
