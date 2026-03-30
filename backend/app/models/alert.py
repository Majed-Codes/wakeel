"""
Alert Model — smart notifications for business owners.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from app.database import Base


class AlertType(str, enum.Enum):
    """نوع التنبيه"""
    BUDGET_EXCEEDED = "budget_exceeded"
    UNUSUAL_SPENDING = "unusual_spending"
    REVENUE_DROP = "revenue_drop"
    ANOMALY_DETECTED = "anomaly_detected"
    COMPLIANCE_DUE = "compliance_due"
    FORECAST_WARNING = "forecast_warning"


class AlertSeverity(str, enum.Enum):
    """مستوى الخطورة"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Alert(Base):
    """نموذج التنبيهات الذكية"""

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False, comment="نوع التنبيه")
    title = Column(String(255), nullable=False, comment="عنوان التنبيه")
    message = Column(Text, nullable=False, comment="نص التنبيه")
    severity = Column(String(20), default="medium", comment="مستوى الخطورة")
    is_read = Column(Boolean, default=False, comment="هل تم القراءة")
    data = Column(Text, nullable=True, comment="بيانات إضافية JSON")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    business = relationship("Business", back_populates="alerts")

    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, type='{self.type}', severity='{self.severity}')>"
