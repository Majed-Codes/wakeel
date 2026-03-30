"""
Transaction Model — every financial movement recorded.

Bachmann: "Floats for money? In production, use Decimal.
For MVP, Float is acceptable. We'll refactor."
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from app.database import Base


class TransactionSource(str, enum.Enum):
    """مصدر المعاملة"""
    VOICE = "voice"
    MANUAL = "manual"
    WHATSAPP = "whatsapp"
    CSV = "csv"
    RECEIPT = "receipt"


class TransactionCategory(str, enum.Enum):
    """تصنيف المعاملة"""
    OPEX = "OpEx"        # مصاريف تشغيلية
    CAPEX = "CapEx"      # مصاريف رأسمالية
    REVENUE = "Revenue"  # إيرادات


class TransactionType(str, enum.Enum):
    """نوع المعاملة: إيراد أو مصروف"""
    REVENUE = "revenue"
    EXPENSE = "expense"


class Transaction(Base):
    """نموذج المعاملة المالية"""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False, comment="المبلغ بالريال")
    category = Column(String(50), nullable=True, comment="تصنيف المعاملة")
    description = Column(String(500), nullable=True, comment="وصف المعاملة")
    vendor = Column(String(255), nullable=True, comment="اسم المورد")
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc), comment="تاريخ المعاملة")
    source = Column(
        SQLEnum(TransactionSource),
        default=TransactionSource.MANUAL,
        comment="مصدر المعاملة: صوتي، يدوي، واتساب",
    )
    transaction_type = Column(
        SQLEnum(TransactionType),
        default=TransactionType.EXPENSE,
        nullable=True,
        comment="نوع المعاملة: إيراد أو مصروف",
    )
    confidence = Column(Float, nullable=True, comment="مستوى الثقة في الاستخراج")
    raw_transcription = Column(String(2000), nullable=True, comment="النص المُستخرج من الصوت")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    business = relationship("Business", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, amount={self.amount}, category='{self.category}')>"
