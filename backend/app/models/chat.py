"""ChatSession model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.poi import Base

if TYPE_CHECKING:
    from app.models.user import User


class ChatSession(Base):
    """AI chat session with agent state."""

    __tablename__ = "chat_sessions"
    __table_args__ = (
        UniqueConstraint("user_id", "thread_id", name="uq_chat_sessions_user_thread"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    thread_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=True)
    messages_json: Mapped[dict | list] = mapped_column(JSONB, nullable=True)
    agent_state_json: Mapped[dict] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="chat_sessions")

    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, user_id={self.user_id}, title={self.title})>"
