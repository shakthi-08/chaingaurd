from __future__ import annotations

from sqlalchemy import Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Attribution(Base):
    __tablename__ = "attributions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    wallet_id: Mapped[int] = mapped_column(ForeignKey("wallets.id"), nullable=False)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reasons: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)

    wallet: Mapped["Wallet"] = relationship(back_populates="attributions")
    entity: Mapped["Entity"] = relationship(back_populates="attributions")
