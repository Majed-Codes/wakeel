"""Zakat calculation route."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import Business
from app.auth.dependencies import get_current_user
from app.services.zakat_calculator import zakat_calculator

router = APIRouter(prefix="/api/v1/zakat", tags=["Zakat"])

@router.get("/")
async def calculate_zakat(
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return zakat_calculator.calculate(current_user.id, db)
