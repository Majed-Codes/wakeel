"""VAT Filing Report — ZATCA Form 1 calculation for Saudi businesses."""
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone, date

VAT_RATE = 0.15  # 15% standard rate in Saudi Arabia

QUARTER_MONTHS = {
    1: (1, 2, 3),
    2: (4, 5, 6),
    3: (7, 8, 9),
    4: (10, 11, 12),
}

FILING_DEADLINES = {
    1: "30 أبريل",
    2: "31 يوليو",
    3: "31 أكتوبر",
    4: "31 يناير (العام التالي)",
}

class VATCalculator:
    def calculate(self, business_id: int, db: Session, quarter: int, year: int) -> dict:
        from app.models.transaction import Transaction

        months = QUARTER_MONTHS[quarter]
        start = datetime(year, months[0], 1)
        end_month = months[-1]
        end_day = 31 if end_month in (1, 3, 5, 7, 8, 10, 12) else 30 if end_month in (4, 6, 9, 11) else 28
        end = datetime(year, end_month, end_day, 23, 59, 59)

        standard_rated_sales = db.query(func.sum(Transaction.amount)).filter(
            Transaction.business_id == business_id,
            Transaction.transaction_type == "REVENUE",
            Transaction.date >= start,
            Transaction.date <= end,
        ).scalar() or 0.0

        standard_rated_purchases = db.query(func.sum(Transaction.amount)).filter(
            Transaction.business_id == business_id,
            Transaction.transaction_type == "EXPENSE",
            Transaction.date >= start,
            Transaction.date <= end,
        ).scalar() or 0.0

        output_vat = round(standard_rated_sales * VAT_RATE, 2)
        input_vat = round(standard_rated_purchases * VAT_RATE, 2)
        net_vat_due = round(output_vat - input_vat, 2)

        return {
            "quarter": quarter,
            "year": year,
            "period_start": start.date().isoformat(),
            "period_end": end.date().isoformat(),
            "standard_rated_sales": round(standard_rated_sales, 2),
            "output_vat": output_vat,
            "standard_rated_purchases": round(standard_rated_purchases, 2),
            "input_vat": input_vat,
            "net_vat_due": net_vat_due,
            "filing_deadline": FILING_DEADLINES[quarter],
        }

vat_calculator = VATCalculator()
