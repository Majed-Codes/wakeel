"""AI Financial Advisor route."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import Business
from app.auth.dependencies import get_current_user
from app.services.financial_advisor import financial_advisor

router = APIRouter(prefix="/api/v1/advisor", tags=["Advisor"])

@router.get("/")
async def get_advice(
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return financial_advisor.generate(current_user.id, db)
