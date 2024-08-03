from datetime import datetime

from aiogram.filters import BaseFilter
from aiogram.types import Message

from loader import admins_ids, owner_id


class IsValidDateFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        if not message or not message.text:
            return False
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
                date = datetime.strptime(message.text, date_format)
                return True if date else False
            except ValueError:
                continue


class AdminFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in admins_ids


class OwnerFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id == owner_id
