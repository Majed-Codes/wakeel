"""
Chat History Model — stores conversation with the AI assistant.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from app.database import Base


class ChatRole(str, enum.Enum):
    """دور المتحدث في المحادثة"""
    USER = "user"
    ASSISTANT = "assistant"


class ChatHistory(Base):
    """نموذج سجل المحادثات"""

    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    role = Column(SQLEnum(ChatRole), nullable=False, comment="المتحدث: مستخدم أو مساعد")
    content = Column(Text, nullable=False, comment="محتوى الرسالة")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    business = relationship("Business", back_populates="chat_history")

    def __repr__(self) -> str:
        return f"<ChatHistory(id={self.id}, role='{self.role}', len={len(self.content)})>"
