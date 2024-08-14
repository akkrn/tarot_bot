import datetime

from aiogram import F, Router
from aiogram.filters.chat_member_updated import (
    ChatMemberUpdatedFilter,
    MEMBER,
    KICKED,
)
from aiogram.types import ChatMemberUpdated
from sqlalchemy import update

from loader import async_session
from models.user import UserStatus, User

router = Router()
router.my_chat_member.filter(F.chat.type == "private")
router.message.filter(F.chat.type == "private")


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED))
async def user_blocked_bot(event: ChatMemberUpdated):
    async with async_session() as session:
        stmt = (
            update(User)
            .where(User.user_tg_id == event.from_user.id)
            .values(status=UserStatus.BANNED, updated_at=datetime.datetime.now())
        )
        await session.execute(stmt)
        await session.commit()


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=MEMBER))
async def user_unblocked_bot(event: ChatMemberUpdated):
    async with async_session() as session:
        stmt = (
            update(User)
            .where(User.user_tg_id == event.from_user.id)
            .values(status=UserStatus.ACTIVE, updated_at=datetime.datetime.now())
        )
        await session.execute(stmt)
        await session.commit()
