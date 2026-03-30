"""
Smart Alerts Routes.

GET   /api/v1/alerts              → List[AlertResponse] (triggers check + returns all)
GET   /api/v1/alerts/unread       → List[AlertResponse] (unread only)
GET   /api/v1/alerts/count        → AlertCountResponse
PATCH /api/v1/alerts/{id}/read    → AlertResponse
PATCH /api/v1/alerts/read-all     → {updated: int}
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import Business
from app.schemas import AlertResponse, AlertCountResponse
from app.auth.dependencies import get_current_user
from app.services.alert_engine import alert_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])


@router.get(
    "/",
    response_model=list[AlertResponse],
    summary="جميع التنبيهات",
    description="يُشغّل فحوصات التنبيهات ويُعيد جميع التنبيهات (غير المقروءة أولاً).",
)
async def get_alerts(
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger alert checks and return all alerts (unread first)."""
    alerts = alert_engine.check_alerts(business_id=current_user.id, db=db)
    return [AlertResponse(**a) for a in alerts]


@router.get(
    "/unread",
    response_model=list[AlertResponse],
    summary="التنبيهات غير المقروءة",
)
async def get_unread_alerts(
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return only unread alerts."""
    alerts = alert_engine.get_alerts(
        business_id=current_user.id, db=db, unread_only=True
    )
    return [AlertResponse(**a) for a in alerts]


@router.get(
    "/count",
    response_model=AlertCountResponse,
    summary="عدد التنبيهات غير المقروءة",
)
async def get_alert_count(
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return count of unread alerts (for badge display)."""
    count = alert_engine.get_unread_count(business_id=current_user.id, db=db)
    return AlertCountResponse(unread=count)


@router.patch(
    "/read-all",
    summary="تحديد الكل كمقروء",
)
async def mark_all_read(
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all alerts as read."""
    count = alert_engine.mark_all_read(business_id=current_user.id, db=db)
    return {"updated": count}


@router.patch(
    "/{alert_id}/read",
    response_model=AlertResponse,
    summary="تحديد تنبيه كمقروء",
)
async def mark_alert_read(
    alert_id: int,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a specific alert as read."""
    alert = alert_engine.mark_read(
        alert_id=alert_id, business_id=current_user.id, db=db
    )
    if not alert:
        raise HTTPException(status_code=404, detail="التنبيه غير موجود")
    return AlertResponse(**alert)
