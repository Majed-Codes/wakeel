from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base

class Vendor(Base):
    __tablename__ = "vendors"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    contact_email = Column(String(255), nullable=True)
    payment_terms_days = Column(Integer, default=30)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    business = relationship("Business", back_populates="vendors")
