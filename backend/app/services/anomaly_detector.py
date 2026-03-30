"""
Anomaly Detection Service — Statistical anomaly detection for financial transactions.

Detects:
- Amount outliers (Z-score per category)
- Duplicate payments (same vendor + amount within 24h)
- Unusual timing (outside normal business hours pattern)
- Category spending drift (ratio changed significantly vs 3-month average)
"""

import logging
import statistics
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.transaction import Transaction, TransactionType

logger = logging.getLogger(__name__)


class Anomaly:
    """Represents a detected anomaly."""
    def __init__(
        self,
        transaction_id: int,
        anomaly_type: str,
        severity: str,
        title: str,
        description: str,
        amount: float,
        vendor: str,
        date: str,
        score: float = 0.0,
    ):
        self.transaction_id = transaction_id
        self.anomaly_type = anomaly_type
        self.severity = severity
        self.title = title
        self.description = description
        self.amount = amount
        self.vendor = vendor
        self.date = date
        self.score = score

    def to_dict(self) -> dict:
        return {
            "transaction_id": self.transaction_id,
            "anomaly_type": self.anomaly_type,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "amount": self.amount,
            "vendor": self.vendor,
            "date": self.date,
            "score": round(self.score, 3),
        }


class AnomalyDetector:
    """Statistical anomaly detection for financial transactions."""

    # Z-score threshold (|z| > threshold = anomaly)
    ZSCORE_THRESHOLD = 2.5
    # Minimum transactions needed per category for Z-score detection
    MIN_CATEGORY_SAMPLES = 5
    # Duplicate detection window in hours
    DUPLICATE_WINDOW_HOURS = 24
    # Category drift threshold (30% change)
    DRIFT_THRESHOLD = 0.30

    def detect_anomalies(self, business_id: int, db: Session) -> list[dict]:
        """
        Run all anomaly checks and return detected anomalies sorted by severity.
        """
        # Fetch all transactions for this business (last 90 days for analysis)
        cutoff = datetime.utcnow() - timedelta(days=90)
        transactions = (
            db.query(Transaction)
            .filter(
                Transaction.business_id == business_id,
                Transaction.date >= cutoff,
            )
            .order_by(Transaction.date.desc())
            .all()
        )

        if not transactions:
            return []

        anomalies: list[Anomaly] = []

        # Run detection methods
        anomalies.extend(self._check_amount_outliers(transactions))
        anomalies.extend(self._check_duplicate_payments(transactions))
        anomalies.extend(self._check_category_drift(transactions))

        # Sort by severity (critical > high > medium > low)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        anomalies.sort(key=lambda a: severity_order.get(a.severity, 4))

        return [a.to_dict() for a in anomalies]

    def get_summary(self, business_id: int, db: Session) -> dict:
        """Return a summary of detected anomalies."""
        anomalies = self.detect_anomalies(business_id, db)

        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        type_counts: dict[str, int] = {}

        for a in anomalies:
            sev = a.get("severity", "low")
            if sev in severity_counts:
                severity_counts[sev] += 1
            atype = a.get("anomaly_type", "unknown")
            type_counts[atype] = type_counts.get(atype, 0) + 1

        return {
            "total_anomalies": len(anomalies),
            "severity_breakdown": severity_counts,
            "type_breakdown": type_counts,
            "anomalies": anomalies[:10],  # Top 10 in summary
            "risk_level": self._overall_risk(severity_counts),
        }

    # ── Private detection methods ──────────────────────────────────────────────

    def _check_amount_outliers(self, transactions: list) -> list[Anomaly]:
        """Detect transactions with unusually high/low amounts per category."""
        anomalies = []

        # Group by category
        by_category: dict[str, list] = {}
        for t in transactions:
            cat = t.category or "غير محدد"
            by_category.setdefault(cat, []).append(t)

        for category, txns in by_category.items():
            if len(txns) < self.MIN_CATEGORY_SAMPLES:
                continue

            amounts = [float(t.amount) for t in txns]
            mean = statistics.mean(amounts)
            stdev = statistics.stdev(amounts)

            if stdev == 0:
                continue

            for t in txns:
                amount = float(t.amount)
                z_score = abs((amount - mean) / stdev)

                if z_score > self.ZSCORE_THRESHOLD:
                    severity = "high" if z_score > 3.5 else "medium"
                    direction = "مرتفع جداً" if amount > mean else "منخفض جداً"
                    anomalies.append(Anomaly(
                        transaction_id=t.id,
                        anomaly_type="amount_outlier",
                        severity=severity,
                        title=f"مبلغ شاذ — {category}",
                        description=(
                            f"المبلغ {amount:,.0f} ر.س {direction} "
                            f"مقارنةً بمتوسط الفئة {mean:,.0f} ر.س "
                            f"(درجة Z: {z_score:.1f})"
                        ),
                        amount=amount,
                        vendor=t.vendor or "",
                        date=t.date.strftime("%Y-%m-%d") if t.date else "",
                        score=z_score,
                    ))

        return anomalies

    def _check_duplicate_payments(self, transactions: list) -> list[Anomaly]:
        """Detect duplicate payments: same vendor + same amount within 24h."""
        anomalies = []
        seen: dict[str, list] = {}  # key → list of transactions

        for t in transactions:
            vendor = (t.vendor or "").strip().lower()
            amount = round(float(t.amount), 2)
            key = f"{vendor}:{amount}"
            seen.setdefault(key, []).append(t)

        for key, txns in seen.items():
            if len(txns) < 2:
                continue

            # Sort by date and find close pairs
            txns_sorted = sorted(txns, key=lambda x: x.date or datetime.min)
            for i in range(len(txns_sorted) - 1):
                t1 = txns_sorted[i]
                t2 = txns_sorted[i + 1]
                if t1.date and t2.date:
                    delta = abs((t2.date - t1.date).total_seconds()) / 3600
                    if delta <= self.DUPLICATE_WINDOW_HOURS:
                        anomalies.append(Anomaly(
                            transaction_id=t2.id,
                            anomaly_type="duplicate_payment",
                            severity="high",
                            title="دفعة مكررة محتملة",
                            description=(
                                f"دفعة {float(t2.amount):,.0f} ر.س للجهة "
                                f"'{t2.vendor}' تكررت خلال {delta:.0f} ساعة"
                            ),
                            amount=float(t2.amount),
                            vendor=t2.vendor or "",
                            date=t2.date.strftime("%Y-%m-%d") if t2.date else "",
                            score=1.0 - (delta / self.DUPLICATE_WINDOW_HOURS),
                        ))

        return anomalies

    def _check_category_drift(self, transactions: list) -> list[Anomaly]:
        """
        Detect if spending ratios by category changed significantly
        comparing the most recent 30 days vs the prior 60 days.
        """
        anomalies = []
        now = datetime.utcnow()
        recent_cutoff = now - timedelta(days=30)
        prior_cutoff = now - timedelta(days=90)

        # Only look at expenses
        expense_txns = [
            t for t in transactions
            if t.transaction_type == TransactionType.EXPENSE
        ]

        if not expense_txns:
            return []

        recent = [t for t in expense_txns if t.date and t.date >= recent_cutoff]
        prior = [t for t in expense_txns if t.date and prior_cutoff <= t.date < recent_cutoff]

        if not recent or not prior:
            return []

        # Compute category ratios
        def _ratios(txns: list) -> dict[str, float]:
            total = sum(float(t.amount) for t in txns) or 1
            cats: dict[str, float] = {}
            for t in txns:
                cat = t.category or "غير محدد"
                cats[cat] = cats.get(cat, 0) + float(t.amount)
            return {cat: amt / total for cat, amt in cats.items()}

        recent_ratios = _ratios(recent)
        prior_ratios = _ratios(prior)

        all_categories = set(recent_ratios) | set(prior_ratios)
        for cat in all_categories:
            r_ratio = recent_ratios.get(cat, 0.0)
            p_ratio = prior_ratios.get(cat, 0.0)
            if p_ratio == 0:
                continue
            drift = abs(r_ratio - p_ratio) / p_ratio
            if drift > self.DRIFT_THRESHOLD:
                direction = "زاد" if r_ratio > p_ratio else "انخفض"
                severity = "medium" if drift > 0.5 else "low"
                anomalies.append(Anomaly(
                    transaction_id=-1,  # No specific transaction
                    anomaly_type="category_drift",
                    severity=severity,
                    title=f"تغيّر في إنفاق — {cat}",
                    description=(
                        f"إنفاق فئة '{cat}' {direction} بنسبة "
                        f"{drift * 100:.0f}% مقارنةً بالشهرين الماضيين "
                        f"({p_ratio * 100:.0f}% → {r_ratio * 100:.0f}%)"
                    ),
                    amount=0.0,
                    vendor="",
                    date=now.strftime("%Y-%m-%d"),
                    score=drift,
                ))

        return anomalies

    def _overall_risk(self, severity_counts: dict) -> str:
        if severity_counts.get("critical", 0) > 0:
            return "critical"
        if severity_counts.get("high", 0) > 0:
            return "high"
        if severity_counts.get("medium", 0) > 0:
            return "medium"
        return "low"


anomaly_detector = AnomalyDetector()
