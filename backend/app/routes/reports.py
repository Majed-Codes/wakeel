"""
Report Generation Routes.

POST /api/v1/reports/generate  → StreamingResponse (PDF download)
GET  /api/v1/reports/summary   → ReportSummary (JSON data without PDF)
"""

import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.database import get_db
from app.models.user import Business
from app.schemas import ReportSummary
from app.auth.dependencies import get_current_user
from app.services.report_generator import report_generator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


@router.post(
    "/generate",
    summary="إنشاء تقرير PDF",
    description="يُنشئ تقريراً مالياً احترافياً بصيغة PDF للفترة المحددة.",
    response_class=StreamingResponse,
)
async def generate_report(
    start_date: Optional[date] = Query(None, description="تاريخ البداية (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="تاريخ النهاية (YYYY-MM-DD)"),
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate and download a PDF financial report."""
    # Default: last 30 days
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=30)

    pdf_bytes = report_generator.generate_report(
        business_id=current_user.id,
        db=db,
        business_name=current_user.name or "مقهى الوكيل",
        start_date=start_date,
        end_date=end_date,
    )

    filename = f"wakeel-report-{start_date}-to-{end_date}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/summary",
    response_model=ReportSummary,
    summary="ملخص التقرير",
    description="يُعيد بيانات ملخص التقرير المالي بدون إنشاء PDF.",
)
async def get_report_summary(
    start_date: Optional[date] = Query(None, description="تاريخ البداية (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="تاريخ النهاية (YYYY-MM-DD)"),
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return report summary data as JSON."""
    data = report_generator.get_summary_data(
        business_id=current_user.id,
        db=db,
        start_date=start_date,
        end_date=end_date,
    )
    return ReportSummary(**data)
