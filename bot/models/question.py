import datetime
from typing import TYPE_CHECKING
from sqlalchemy import TIMESTAMP, TEXT, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User


class Question(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    question: Mapped[str | None] = mapped_column(TEXT)
    answer: Mapped[str | None] = mapped_column(TEXT)
    cards: Mapped[list | None] = mapped_column(ARRAY(String))
    added_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP)

    user: Mapped["User"] = relationship(back_populates="questions")
