"""
Pydantic Schemas — API contracts.

Bachmann: "API schemas are PUBLIC. Database models are PRIVATE.
Never expose your database structure through your API."
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


# ── Auth Schemas ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="اسم المنشأة")
    phone: str = Field(..., min_length=10, max_length=20, description="رقم الجوال")
    email: Optional[str] = Field(None, description="البريد الإلكتروني")
    password: str = Field(..., min_length=6, description="كلمة المرور")


class LoginRequest(BaseModel):
    phone: str = Field(..., description="رقم الجوال")
    password: str = Field(..., description="كلمة المرور")


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class BusinessResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Transaction Schemas ───────────────────────────────────────

class TransactionCreate(BaseModel):
    amount: float = Field(..., gt=0, description="المبلغ بالريال")
    category: Optional[str] = Field(None, description="تصنيف: OpEx, CapEx, Revenue")
    description: Optional[str] = Field(None, max_length=500, description="الوصف")
    vendor: Optional[str] = Field(None, max_length=255, description="اسم المورد")
    date: Optional[datetime] = None


class TransactionResponse(BaseModel):
    id: int
    business_id: int
    amount: float
    category: Optional[str] = None
    description: Optional[str] = None
    vendor: Optional[str] = None
    date: Optional[datetime] = None
    source: str
    confidence: Optional[float] = None
    raw_transcription: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class VoiceTransactionResponse(BaseModel):
    status: str  # "success" | "needs_confirmation" | "error"
    message: str
    transaction: Optional[TransactionResponse] = None
    extracted_data: Optional[dict] = None


# ── Chat Schemas ──────────────────────────────────────────────

class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="رسالة المستخدم")


class ChatMessageResponse(BaseModel):
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Invoice / Compliance Schemas ──────────────────────────────

class InvoiceValidationRequest(BaseModel):
    seller_name: Optional[str] = None
    seller_vat: Optional[str] = None
    buyer_name: Optional[str] = None
    date: Optional[str] = None
    total: Optional[float] = None
    vat_amount: Optional[float] = None
    qr_code: Optional[str] = None


class ComplianceResult(BaseModel):
    valid: bool
    errors: List[str]
    warnings: List[str]
    compliance_score: float


# ── Dashboard Schemas ─────────────────────────────────────────

class DashboardSummary(BaseModel):
    total_income: float
    total_expenses: float
    transaction_count: int
    compliance_score: float
    recent_transactions: List[TransactionResponse]


# ── Forecast Schemas ─────────────────────────────────────────

class ForecastPoint(BaseModel):
    date: str
    value: float
    lower: float
    upper: float


class ForecastSummary(BaseModel):
    avg_daily_revenue: float
    avg_daily_expense: float
    predicted_net_30d: float
    trend: str  # "growing" | "stable" | "declining"
    risk_level: str  # "low" | "medium" | "high"


class ForecastResponse(BaseModel):
    period_days: int
    revenue_forecast: List[ForecastPoint]
    expense_forecast: List[ForecastPoint]
    net_forecast: List[ForecastPoint]
    summary: ForecastSummary


class ForecastInsights(BaseModel):
    trend: str
    seasonal_patterns: List[str]
    risk_factors: List[str]
    recommendations: List[str]


# ── Upload / CSV Schemas ─────────────────────────────────────

class UploadPreview(BaseModel):
    filename: str
    total_rows: int
    columns: List[str]
    column_mapping: dict
    sample_rows: List[dict]


class UploadConfirm(BaseModel):
    rows: List[dict]
    column_mapping: dict


class UploadResult(BaseModel):
    imported: int
    errors: List[dict]
    filename: str


# ── Receipt OCR Schemas ──────────────────────────────────────

class ReceiptExtractionResponse(BaseModel):
    status: str  # "success" | "needs_confirmation" | "error"
    message: str
    transaction: Optional[TransactionResponse] = None
    extracted_data: Optional[dict] = None


# ── Alert Schemas ────────────────────────────────────────────

class AlertResponse(BaseModel):
    id: int
    type: str
    title: str
    message: str
    severity: str
    is_read: bool
    data: Optional[Any] = None  # JSON dict stored in DB
    created_at: Optional[str] = None  # ISO string from service layer

    model_config = {"from_attributes": True}


class AlertCountResponse(BaseModel):
    unread: int


# ── Report Schemas ───────────────────────────────────────────

class ReportRequest(BaseModel):
    start_date: str = Field(..., description="YYYY-MM-DD")
    end_date: str = Field(..., description="YYYY-MM-DD")
    language: str = Field(default="ar", description="ar or en")


class ReportSummary(BaseModel):
    start_date: str
    end_date: str
    total_revenue: float
    total_expenses: float
    net_profit: float
    transaction_count: int
    by_category: dict
    top_vendors: dict
    monthly_trend: dict


# ── Anomaly Schemas ──────────────────────────────────────────

class AnomalyResponse(BaseModel):
    transaction_id: int
    anomaly_type: str  # "amount_outlier" | "duplicate_payment" | "category_drift"
    severity: str      # "low" | "medium" | "high" | "critical"
    title: str
    description: str
    amount: float
    vendor: str
    date: str
    score: float


class AnomalySummary(BaseModel):
    total_anomalies: int
    severity_breakdown: dict
    type_breakdown: dict
    anomalies: List[AnomalyResponse]
    risk_level: str
