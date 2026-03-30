"""Budget management routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import get_db
from app.models.user import Business
from app.models.budget import Budget
from app.auth.dependencies import get_current_user
from app.services.budget_service import budget_service

router = APIRouter(prefix="/api/v1/budget", tags=["Budget"])

@router.get("/")
async def list_budgets(
    month: int = None,
    year: int = None,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    m = month or now.month
    y = year or now.year
    return budget_service.get_status(current_user.id, m, y, db)

@router.post("/", status_code=201)
async def create_budget(
    data: dict,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    budget = Budget(
        business_id=current_user.id,
        category=data["category"],
        amount=float(data["amount"]),
        month=int(data.get("month", datetime.now().month)),
        year=int(data.get("year", datetime.now().year)),
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return {"id": budget.id, "category": budget.category, "amount": budget.amount,
            "month": budget.month, "year": budget.year, "spent": 0.0, "remaining": budget.amount, "pct_used": 0.0}

@router.put("/{budget_id}")
async def update_budget(
    budget_id: int,
    data: dict,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    budget = db.query(Budget).filter(Budget.id == budget_id, Budget.business_id == current_user.id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    if "amount" in data:
        budget.amount = float(data["amount"])
    db.commit()
    return {"id": budget.id, "category": budget.category, "amount": budget.amount,
            "month": budget.month, "year": budget.year}

@router.delete("/{budget_id}", status_code=204)
async def delete_budget(
    budget_id: int,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    budget = db.query(Budget).filter(Budget.id == budget_id, Budget.business_id == current_user.id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    db.delete(budget)
    db.commit()
