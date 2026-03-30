"""Budget tracking service."""
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
from app.models.budget import Budget
from app.models.transaction import Transaction

class BudgetService:
    def get_status(self, business_id: int, month: int, year: int, db: Session) -> list:
        budgets = db.query(Budget).filter(
            Budget.business_id == business_id,
            Budget.month == month,
            Budget.year == year,
        ).all()

        result = []
        for b in budgets:
            # Sum expenses for this category in this month/year
            start = datetime(year, month, 1)
            if month == 12:
                end = datetime(year + 1, 1, 1)
            else:
                end = datetime(year, month + 1, 1)

            spent = db.query(func.sum(Transaction.amount)).filter(
                Transaction.business_id == business_id,
                Transaction.category == b.category,
                Transaction.transaction_type == "EXPENSE",
                Transaction.date >= start,
                Transaction.date < end,
            ).scalar() or 0.0

            remaining = max(0.0, b.amount - spent)
            pct = round((spent / b.amount * 100) if b.amount > 0 else 0.0, 1)

            result.append({
                "id": b.id,
                "category": b.category,
                "amount": b.amount,
                "month": b.month,
                "year": b.year,
                "spent": round(spent, 2),
                "remaining": round(remaining, 2),
                "pct_used": pct,
            })
        return result

budget_service = BudgetService()
