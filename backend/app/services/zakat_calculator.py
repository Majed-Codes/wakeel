"""Zakat calculator for Saudi SMEs (Islamic finance compliance)."""
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone, timedelta
from app.models.transaction import Transaction

# Nisab threshold for 2025 (85g gold equivalent in SAR)
# Update annually based on gold price
NISAB_SAR_2025 = 21_500.0
ZAKAT_RATE = 0.025  # 2.5%

class ZakatCalculator:
    def calculate(self, business_id: int, db: Session) -> dict:
        # Use last 12 months of data
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=365)

        revenue = db.query(func.sum(Transaction.amount)).filter(
            Transaction.business_id == business_id,
            Transaction.transaction_type == "REVENUE",
            Transaction.date >= start,
            Transaction.date <= end,
        ).scalar() or 0.0

        expenses = db.query(func.sum(Transaction.amount)).filter(
            Transaction.business_id == business_id,
            Transaction.transaction_type == "EXPENSE",
            Transaction.date >= start,
            Transaction.date <= end,
        ).scalar() or 0.0

        net_assets = max(0.0, revenue - expenses)
        is_above_nisab = net_assets >= NISAB_SAR_2025
        zakat_due = round(net_assets * ZAKAT_RATE, 2) if is_above_nisab else 0.0

        return {
            "zakatable_assets": round(revenue, 2),
            "liabilities": round(expenses, 2),
            "net_assets": round(net_assets, 2),
            "nisab_threshold": NISAB_SAR_2025,
            "zakat_due": zakat_due,
            "is_above_nisab": is_above_nisab,
            "hawl_reminder": "يُشترط اكتمال الحول (سنة هجرية كاملة) لوجوب الزكاة. تأكد من احتساب الزكاة بعد مرور سنة على امتلاك النصاب.",
            "calculation_date": end.date().isoformat(),
        }

zakat_calculator = ZakatCalculator()
