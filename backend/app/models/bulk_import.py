"""
BulkImport Model — tracks CSV/Excel file imports.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from app.database import Base


class ImportStatus(str, enum.Enum):
    """حالة الاستيراد"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BulkImport(Base):
    """نموذج استيراد البيانات الجماعي"""

    __tablename__ = "bulk_imports"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False, comment="اسم الملف")
    row_count = Column(Integer, default=0, comment="عدد الصفوف")
    success_count = Column(Integer, default=0, comment="عدد الناجحة")
    error_count = Column(Integer, default=0, comment="عدد الأخطاء")
    status = Column(String(20), default="pending", comment="حالة الاستيراد")
    errors = Column(Text, nullable=True, comment="تفاصيل الأخطاء JSON")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    business = relationship("Business", back_populates="bulk_imports")

    def __repr__(self) -> str:
        return f"<BulkImport(id={self.id}, file='{self.filename}', status='{self.status}')>"
