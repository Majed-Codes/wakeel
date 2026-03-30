"""
Dashboard Routes — summary statistics and recent activity.

Bachmann: "This endpoint is called every time the app loads.
It must be fast. Query once, aggregate in memory."
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import Business
from app.models.transaction import Transaction
from app.models.invoice import Invoice
from app.schemas import DashboardSummary, TransactionResponse
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get(
    "/",
    response_model=DashboardSummary,
    summary="الملخص المالي",
)
async def get_dashboard(
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get financial dashboard summary for the current business."""

    transactions = (
        db.query(Transaction)
        .filter(Transaction.business_id == current_user.id)
        .all()
    )

    # Support both Arabic and English category names
    income_categories = {"Revenue", "إيرادات"}
    expense_categories = {"OpEx", "CapEx", "تشغيلية", "رأسمالية"}

    total_income = sum(t.amount for t in transactions if t.category in income_categories)
    total_expenses = sum(t.amount for t in transactions if t.category in expense_categories)

    # Compliance score: average of all invoice compliance scores
    avg_compliance = (
        db.query(func.avg(Invoice.compliance_score))
        .filter(Invoice.business_id == current_user.id)
        .scalar()
    ) or 0.0

    # Recent transactions (last 10)
    recent = sorted(transactions, key=lambda t: t.created_at, reverse=True)[:10]

    return DashboardSummary(
        total_income=total_income,
        total_expenses=total_expenses,
        transaction_count=len(transactions),
        compliance_score=float(avg_compliance),
        recent_transactions=[TransactionResponse.model_validate(t) for t in recent],
    )
