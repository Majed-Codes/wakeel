"""
Anomaly Detection Routes.

GET /api/v1/anomalies         → List[AnomalyResponse]
GET /api/v1/anomalies/summary → AnomalySummary
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import Business
from app.schemas import AnomalyResponse, AnomalySummary
from app.auth.dependencies import get_current_user
from app.services.anomaly_detector import anomaly_detector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/anomalies", tags=["Anomalies"])


@router.get(
    "/",
    response_model=list[AnomalyResponse],
    summary="اكتشاف الشذوذات",
    description="يكشف عن التحويلات غير الاعتيادية في البيانات المالية.",
)
async def get_anomalies(
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Detect and return financial anomalies for the current business."""
    anomalies = anomaly_detector.detect_anomalies(
        business_id=current_user.id, db=db
    )
    return [AnomalyResponse(**a) for a in anomalies]


@router.get(
    "/summary",
    response_model=AnomalySummary,
    summary="ملخص الشذوذات",
    description="يُعيد ملخصاً شاملاً لجميع الشذوذات المكتشفة.",
)
async def get_anomaly_summary(
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return an anomaly summary with counts by severity and type."""
    summary = anomaly_detector.get_summary(
        business_id=current_user.id, db=db
    )
    return AnomalySummary(**summary)
