"""
Forecast Model — cash flow prediction records.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.database import Base


class Forecast(Base):
    """نموذج التنبؤ المالي"""

    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    forecast_type = Column(String(20), nullable=False, comment="revenue/expenses/net")
    period_start = Column(DateTime, nullable=False, comment="بداية فترة التنبؤ")
    period_end = Column(DateTime, nullable=False, comment="نهاية فترة التنبؤ")
    predicted_value = Column(Float, nullable=False, comment="القيمة المتوقعة")
    lower_bound = Column(Float, nullable=True, comment="الحد الأدنى")
    upper_bound = Column(Float, nullable=True, comment="الحد الأعلى")
    confidence_level = Column(Float, default=0.8, comment="مستوى الثقة")
    model_used = Column(String(50), default="prophet", comment="النموذج المستخدم")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    business = relationship("Business", back_populates="forecasts")

    def __repr__(self) -> str:
        return f"<Forecast(id={self.id}, type='{self.forecast_type}', value={self.predicted_value})>"
