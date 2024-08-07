import datetime
from typing import TYPE_CHECKING
from sqlalchemy import TIMESTAMP, INTEGER, TEXT, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User


class Payment(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    payment_id: Mapped[str] = mapped_column(TEXT, nullable=False)
    invoice_payload: Mapped[str] = mapped_column(TEXT, nullable=False)
    total_amount: Mapped[int] = mapped_column(INTEGER, nullable=False)
    is_refunded: Mapped[bool] = mapped_column(default=False)
    date: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP, default=datetime.datetime.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="payments")
