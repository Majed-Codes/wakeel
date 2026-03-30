"""
Business (User) Model — the core entity.

Bachmann: "A business is not a user. A user belongs to a business.
But for MVP, they're the same. We'll split later."
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.database import Base


class Business(Base):
    """نموذج الشركة / المنشأة — الكيان الأساسي في وكيل"""

    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, comment="اسم المنشأة")
    phone = Column(String(20), unique=True, nullable=False, index=True, comment="رقم الجوال")
    email = Column(String(255), nullable=True, comment="البريد الإلكتروني")
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    transactions = relationship("Transaction", back_populates="business", lazy="selectin")
    invoices = relationship("Invoice", back_populates="business", lazy="selectin")
    chat_history = relationship("ChatHistory", back_populates="business", lazy="selectin")
    alerts = relationship("Alert", back_populates="business", lazy="selectin")
    forecasts = relationship("Forecast", back_populates="business", lazy="selectin")
    bulk_imports = relationship("BulkImport", back_populates="business", lazy="selectin")
    budgets = relationship("Budget", back_populates="business", lazy="selectin")
    vendors = relationship("Vendor", back_populates="business", lazy="selectin")
    employees = relationship("Employee", back_populates="business", lazy="selectin")
    payroll_runs = relationship("PayrollRun", back_populates="business", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Business(id={self.id}, name='{self.name}', phone='{self.phone}')>"
