from aiogram import Bot

from loader import owner_id


async def send_to_admin(bot: Bot, message: str, user_id: int):
    await bot.send_message(
        chat_id=owner_id,
        text=f"Пользователь {user_id} отправил сообщение: {message}",
    )
