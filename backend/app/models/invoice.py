"""
Invoice Model — ZATCA compliance tracking.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.database import Base


class Invoice(Base):
    """نموذج الفاتورة — لتتبع الامتثال لهيئة الزكاة والضريبة"""

    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    seller_name = Column(String(255), nullable=False, comment="اسم البائع")
    seller_vat = Column(String(15), nullable=True, comment="الرقم الضريبي للبائع")
    buyer_name = Column(String(255), nullable=True, comment="اسم المشتري")
    date = Column(DateTime, nullable=False, comment="تاريخ الفاتورة")
    total = Column(Float, nullable=False, comment="المبلغ الإجمالي")
    vat_amount = Column(Float, nullable=True, comment="مبلغ الضريبة")
    qr_code = Column(Text, nullable=True, comment="رمز QR")
    is_compliant = Column(Boolean, default=False, comment="هل الفاتورة متوافقة")
    compliance_score = Column(Float, default=0.0, comment="نسبة الامتثال")
    validation_errors = Column(Text, nullable=True, comment="أخطاء التحقق")
    # E-invoice generation fields
    invoice_number = Column(String(50), nullable=True, comment="رقم الفاتورة الإلكترونية")
    xml_content = Column(Text, nullable=True, comment="محتوى XML للفاتورة")
    pdf_path = Column(String(500), nullable=True, comment="مسار ملف PDF")
    qr_data = Column(Text, nullable=True, comment="بيانات QR المشفرة")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    business = relationship("Business", back_populates="invoices")

    def __repr__(self) -> str:
        return f"<Invoice(id={self.id}, total={self.total}, compliant={self.is_compliant})>"
