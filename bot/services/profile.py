import logging

from sqlalchemy import func, select, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from models import User, Question
from media_data import cards_list
from sqlalchemy.orm import aliased

logger = logging.getLogger(__name__)


async def get_user_info(session: AsyncSession, user_tg_id: int):
    ReferredUser = aliased(User)
    query = (
        select(
            User,
            func.count(distinct(ReferredUser.id)).label("friends_invited"),
            func.count(distinct(Question.id)).label("questions_asked"),
        )
        .outerjoin(ReferredUser, User.id == ReferredUser.referrer_id)
        .outerjoin(Question, User.id == Question.user_id)
        .filter(User.user_tg_id == user_tg_id)
        .group_by(User.id)
    )
    result = await session.execute(query)
    return result.first()


async def get_most_frequent_card(
    session: AsyncSession, user_id: int
) -> str | None:
    query = (
        select(Question.cards)
        .filter(Question.user_id == user_id)
        .filter(Question.cards.isnot(None))
    )
    result = await session.execute(query)
    all_cards = result.scalars().all()

    if not all_cards:
        return None

    flat_cards = [card for sublist in all_cards for card in sublist if card]
    if not flat_cards:
        return None

    return max(set(flat_cards), key=flat_cards.count).split(",")[0]


async def get_profile_info(session: AsyncSession, user_tg_id: int) -> str:
    user_info = await get_user_info(session, user_tg_id)

    if not user_info:
        return "Пользователь не найден"

    user, friends_invited, questions_asked = user_info

    name = user.real_name or user.first_name or "Имя не указано"
    birth_date = (
        user.birth_date.strftime("%d.%m.%Y")
        if user.birth_date
        else "Дата рождения не указана"
    )

    most_frequent_card = await get_most_frequent_card(session, user.id)
    most_frequent_card_name = (
        cards_list[most_frequent_card]
        if most_frequent_card
        else "Вам еще не выпадали карты"
    )

    referrer = (
        await session.get(User, user.referrer_id) if user.referrer_id else None
    )
    referrer_username = (
        f"@{referrer.username}" if referrer and referrer.username else None
    )

    response_text = f"Имя: {name}\n" f"Дата рождения: {birth_date}\n\n"
    if referrer_username:
        response_text += f"Вас пригласил: {referrer_username}\n"

    response_text += (
        f"Чаще всего выпадающая карта: {most_frequent_card_name}\n"
        f"Друзей приглашено: {friends_invited}\n"
        f"Вопросов задано: {questions_asked}\n"
        f"Бесплатных вопросов: {user.balance}\n"
    )
    return response_text
