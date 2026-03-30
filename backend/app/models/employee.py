from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base

class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    name_ar = Column(String(255), nullable=False)
    name_en = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=False)
    national_id = Column(String(20), nullable=True)
    base_salary = Column(Float, nullable=False)
    is_saudi = Column(Boolean, default=True)
    gosi_enrolled = Column(Boolean, default=True)
    start_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    business = relationship("Business", back_populates="employees")

class PayrollRun(Base):
    __tablename__ = "payroll_runs"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    total_gross = Column(Float, default=0.0)
    total_gosi_employer = Column(Float, default=0.0)
    total_gosi_employee = Column(Float, default=0.0)
    total_net = Column(Float, default=0.0)
    headcount = Column(Integer, default=0)
    status = Column(String(20), default="draft")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    business = relationship("Business", back_populates="payroll_runs")
