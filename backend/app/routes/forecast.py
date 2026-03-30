"""
Forecast Routes — cash flow prediction endpoints.

GET /api/v1/forecast/         → Generate forecast for 30/60/90 days
GET /api/v1/forecast/insights → Trend analysis + AI recommendations
"""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import Business
from app.schemas import ForecastResponse, ForecastInsights
from app.auth.dependencies import get_current_user
from app.services.forecasting import forecasting_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/forecast", tags=["Forecast"])


@router.get(
    "/",
    response_model=ForecastResponse,
    summary="التنبؤ بالتدفق النقدي",
    description="يولّد تنبؤات للإيرادات والمصاريف والصافي للفترة القادمة.",
)
async def get_forecast(
    period_days: int = Query(default=30, ge=7, le=365, description="عدد أيام التنبؤ (7-365)"),
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate cash flow forecast using historical transaction data.

    - Uses Facebook Prophet when >= 15 transactions exist
    - Falls back to moving average for sparse data
    - Returns mock realistic data when no transactions exist
    """
    result = forecasting_service.generate_forecast(
        business_id=current_user.id,
        db=db,
        period_days=period_days,
    )
    return ForecastResponse(**result)


@router.get(
    "/insights",
    response_model=ForecastInsights,
    summary="تحليل الاتجاهات والتوصيات",
    description="يحلّل الأنماط المالية ويقدّم توصيات مدعومة بالذكاء الاصطناعي.",
)
async def get_forecast_insights(
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Analyze financial trends and generate actionable Arabic recommendations.
    Uses Claude when API key is configured, falls back to rule-based insights.
    """
    result = forecasting_service.get_insights(
        business_id=current_user.id,
        db=db,
    )
    return ForecastInsights(**result)
