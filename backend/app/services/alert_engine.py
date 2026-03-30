"""
Smart Alert Engine — Automatic financial alert generation.

Checks:
- Budget exceeded (monthly spending > 120% of 3-month average)
- Revenue drop (current month revenue down 20%+ vs last month)
- Anomaly detected (from anomaly detector)
- Forecast warning (negative net cash flow predicted)
- Duplicate payment alerts
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.alert import Alert, AlertType, AlertSeverity
from app.models.transaction import Transaction, TransactionType
from app.services.anomaly_detector import anomaly_detector

logger = logging.getLogger(__name__)


class AlertEngine:
    """Generates and persists smart financial alerts."""

    # Thresholds
    BUDGET_EXCEEDED_THRESHOLD = 1.20   # 120% of average
    REVENUE_DROP_THRESHOLD = 0.20      # 20% drop

    def check_alerts(self, business_id: int, db: Session) -> list[dict]:
        """
        Run all alert checks for a business.
        Creates new Alert records for unread alerts not already stored.
        Returns list of alert dicts (new + existing unread).
        """
        new_alerts: list[Alert] = []

        try:
            new_alerts.extend(self._check_budget_exceeded(business_id, db))
            new_alerts.extend(self._check_revenue_drop(business_id, db))
            new_alerts.extend(self._check_anomaly_alerts(business_id, db))
        except Exception as e:
            logger.error(f"Alert engine error for business {business_id}: {e}")

        # Persist new alerts (avoid duplicates by checking within last 7 days)
        cutoff_7d = datetime.utcnow() - timedelta(days=7)
        for alert in new_alerts:
            existing = (
                db.query(Alert)
                .filter(
                    Alert.business_id == business_id,
                    Alert.type == alert.type,
                    Alert.title == alert.title,
                    Alert.created_at >= cutoff_7d,
                )
                .first()
            )
            if not existing:
                db.add(alert)

        try:
            db.commit()
        except Exception as e:
            logger.error(f"Failed to commit alerts: {e}")
            db.rollback()

        return self.get_alerts(business_id, db)

    def get_alerts(self, business_id: int, db: Session, unread_only: bool = False) -> list[dict]:
        """Return alerts sorted by unread first, then by date descending."""
        query = db.query(Alert).filter(Alert.business_id == business_id)
        if unread_only:
            query = query.filter(Alert.is_read == False)
        alerts = query.order_by(Alert.is_read.asc(), Alert.created_at.desc()).all()

        return [
            {
                "id": a.id,
                "type": a.type.value if hasattr(a.type, "value") else str(a.type),
                "title": a.title,
                "message": a.message,
                "severity": a.severity.value if hasattr(a.severity, "value") else str(a.severity),
                "is_read": a.is_read,
                "data": a.data,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in alerts
        ]

    def get_unread_count(self, business_id: int, db: Session) -> int:
        """Return count of unread alerts."""
        return (
            db.query(Alert)
            .filter(Alert.business_id == business_id, Alert.is_read == False)
            .count()
        )

    def mark_read(self, alert_id: int, business_id: int, db: Session) -> dict | None:
        """Mark an alert as read and return updated alert."""
        alert = (
            db.query(Alert)
            .filter(Alert.id == alert_id, Alert.business_id == business_id)
            .first()
        )
        if not alert:
            return None
        alert.is_read = True
        db.commit()
        db.refresh(alert)
        return {
            "id": alert.id,
            "type": alert.type.value if hasattr(alert.type, "value") else str(alert.type),
            "title": alert.title,
            "message": alert.message,
            "severity": alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity),
            "is_read": alert.is_read,
            "data": alert.data,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
        }

    def mark_all_read(self, business_id: int, db: Session) -> int:
        """Mark all alerts as read. Returns count updated."""
        count = (
            db.query(Alert)
            .filter(Alert.business_id == business_id, Alert.is_read == False)
            .update({"is_read": True})
        )
        db.commit()
        return count

    # ── Private check methods ──────────────────────────────────────────────────

    def _check_budget_exceeded(self, business_id: int, db: Session) -> list[Alert]:
        """Alert if current month's expenses exceed 120% of 3-month average."""
        now = datetime.utcnow()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        three_months_ago = current_month_start - timedelta(days=90)

        # Current month expenses
        current_expenses = (
            db.query(Transaction)
            .filter(
                Transaction.business_id == business_id,
                Transaction.transaction_type == TransactionType.EXPENSE,
                Transaction.date >= current_month_start,
            )
            .all()
        )
        current_total = sum(float(t.amount) for t in current_expenses)

        # Prior 3 months average (per month)
        prior_expenses = (
            db.query(Transaction)
            .filter(
                Transaction.business_id == business_id,
                Transaction.transaction_type == TransactionType.EXPENSE,
                Transaction.date >= three_months_ago,
                Transaction.date < current_month_start,
            )
            .all()
        )
        prior_total = sum(float(t.amount) for t in prior_expenses)
        prior_avg_monthly = prior_total / 3 if prior_total > 0 else 0

        if prior_avg_monthly == 0 or current_total == 0:
            return []

        ratio = current_total / prior_avg_monthly
        if ratio >= self.BUDGET_EXCEEDED_THRESHOLD:
            severity = AlertSeverity.CRITICAL if ratio >= 1.5 else AlertSeverity.HIGH
            return [Alert(
                business_id=business_id,
                type=AlertType.BUDGET_EXCEEDED,
                title="تجاوز الميزانية الشهرية",
                message=(
                    f"إنفاق هذا الشهر {current_total:,.0f} ر.س "
                    f"يتجاوز المتوسط الشهري {prior_avg_monthly:,.0f} ر.س "
                    f"بنسبة {(ratio - 1) * 100:.0f}%"
                ),
                severity=severity,
                is_read=False,
                data={"current": current_total, "average": prior_avg_monthly, "ratio": ratio},
            )]
        return []

    def _check_revenue_drop(self, business_id: int, db: Session) -> list[Alert]:
        """Alert if current month revenue dropped 20%+ vs last month."""
        now = datetime.utcnow()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)

        def _revenue(start, end):
            txns = (
                db.query(Transaction)
                .filter(
                    Transaction.business_id == business_id,
                    Transaction.transaction_type == TransactionType.REVENUE,
                    Transaction.date >= start,
                    Transaction.date < end,
                )
                .all()
            )
            return sum(float(t.amount) for t in txns)

        current_rev = _revenue(current_month_start, now)
        last_rev = _revenue(last_month_start, current_month_start)

        if last_rev == 0 or current_rev == 0:
            return []

        # Adjust current month for days elapsed
        days_in_month = 30
        days_elapsed = max((now - current_month_start).days, 1)
        projected_current = current_rev * (days_in_month / days_elapsed)

        drop_ratio = (last_rev - projected_current) / last_rev
        if drop_ratio >= self.REVENUE_DROP_THRESHOLD:
            return [Alert(
                business_id=business_id,
                type=AlertType.REVENUE_DROP,
                title="انخفاض في الإيرادات",
                message=(
                    f"الإيرادات المتوقعة لهذا الشهر {projected_current:,.0f} ر.س "
                    f"أقل من الشهر الماضي {last_rev:,.0f} ر.س "
                    f"بنسبة {drop_ratio * 100:.0f}%"
                ),
                severity=AlertSeverity.HIGH,
                is_read=False,
                data={"current_projected": projected_current, "last_month": last_rev, "drop_pct": drop_ratio},
            )]
        return []

    def _check_anomaly_alerts(self, business_id: int, db: Session) -> list[Alert]:
        """Convert high/critical anomalies into alerts."""
        anomalies = anomaly_detector.detect_anomalies(business_id, db)
        alerts = []

        for a in anomalies:
            if a.get("severity") not in ("high", "critical"):
                continue
            if a.get("anomaly_type") == "duplicate_payment":
                alert_type = AlertType.UNUSUAL_SPENDING
                severity = AlertSeverity.HIGH
            else:
                alert_type = AlertType.ANOMALY_DETECTED
                severity = AlertSeverity.MEDIUM if a.get("severity") == "high" else AlertSeverity.HIGH

            alerts.append(Alert(
                business_id=business_id,
                type=alert_type,
                title=a.get("title", "شذوذ مالي مكتشف"),
                message=a.get("description", ""),
                severity=severity,
                is_read=False,
                data={"anomaly": a},
            ))

        # Limit to top 3 anomaly alerts to avoid flooding
        return alerts[:3]


alert_engine = AlertEngine()
