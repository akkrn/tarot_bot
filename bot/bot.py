import asyncio
import logging
import sys
from logging.handlers import RotatingFileHandler

import sentry_sdk
from aiogram.utils.callback_answer import CallbackAnswerMiddleware

from handlers import (
    users_handlers,
    payments_handlers,
    admin_handlers,
    other_handlers,
    tarot_handlers,
    form_handlers,
    command_handlers,
)
from loader import bot, dp, sentry_url

logger = logging.getLogger(__name__)


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(filename)s:%(lineno)d %(levelname)-8s "
        "[%(asctime)s] - %(name)s - %(message)s",
        handlers=[
            RotatingFileHandler(
                "bot.log", maxBytes=50000000, backupCount=5, encoding="utf-8"
            )
        ],
    )

    logger.info("Starting bot")

    dp.include_router(command_handlers.router)
    dp.include_router(payments_handlers.router)
    dp.include_router(users_handlers.router)
    dp.include_router(form_handlers.router)
    dp.include_router(admin_handlers.router)
    dp.include_router(tarot_handlers.router)
    dp.include_router(other_handlers.router)

    # Автоматический ответ на необработанные колбеки, в данном случае нажатия не будут
    # крутиться песочные часы, что хорошо скажется на UI/UX
    dp.callback_query.middleware(CallbackAnswerMiddleware())

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    if "win32" in sys.platform:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    sentry_sdk.init(sentry_url)
    asyncio.run(main())
