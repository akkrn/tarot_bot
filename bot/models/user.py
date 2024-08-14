import datetime
from typing import TYPE_CHECKING
from sqlalchemy import BigInteger, TIMESTAMP, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from .base import Base

if TYPE_CHECKING:
    from .question import Question
    from .payment import Payment


class UserStatus(enum.Enum):
    ACTIVE = "active"
    BANNED = "banned"


class User(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    user_tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[str | None]
    first_name: Mapped[str | None]
    last_name: Mapped[str | None]
    real_name: Mapped[str | None]
    birth_date: Mapped[datetime.date | None]
    balance: Mapped[int] = mapped_column(BigInteger, default=3)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False
    )
    referrer_id: Mapped[int | None]
    added_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP)
    updated_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP)

    questions: Mapped[list["Question"]] = relationship(back_populates="user")
    payments: Mapped[list["Payment"]] = relationship(back_populates="user")
