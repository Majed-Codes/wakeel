"""
Tests for Smart Alerts — AlertEngine service and /api/v1/alerts routes.
"""

import pytest
from datetime import datetime, timezone

from app.models.alert import Alert, AlertType, AlertSeverity


class TestAlertEngine:
    """Unit tests for AlertEngine service logic."""

    def test_get_alerts_empty(self, db, test_business):
        """get_alerts returns an empty list when no alerts exist."""
        from app.services.alert_engine import AlertEngine
        engine = AlertEngine()
        result = engine.get_alerts(business_id=test_business.id, db=db)
        assert result == []

    def test_mark_read(self, db, test_business):
        """mark_read sets is_read=True on the target alert."""
        from app.services.alert_engine import AlertEngine

        alert = Alert(
            business_id=test_business.id,
            type=AlertType.UNUSUAL_SPENDING,
            title="إنفاق غير اعتيادي",
            message="تم رصد إنفاق مرتفع هذا الشهر",
            severity=AlertSeverity.HIGH,
            is_read=False,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        engine = AlertEngine()
        updated = engine.mark_read(
            alert_id=alert.id,
            business_id=test_business.id,
            db=db,
        )

        assert updated is not None
        assert updated["is_read"] is True
        assert updated["id"] == alert.id

    def test_mark_all_read(self, db, test_business):
        """mark_all_read marks every unread alert and returns the count updated."""
        from app.services.alert_engine import AlertEngine

        for i in range(3):
            alert = Alert(
                business_id=test_business.id,
                type=AlertType.COMPLIANCE_DUE,
                title=f"تنبيه الامتثال {i + 1}",
                message="موعد التسجيل في ضريبة القيمة المضافة اقترب",
                severity=AlertSeverity.MEDIUM,
                is_read=False,
            )
            db.add(alert)
        db.commit()

        engine = AlertEngine()
        count = engine.mark_all_read(business_id=test_business.id, db=db)

        assert count == 3

        # Verify all are actually marked read in the DB
        remaining_unread = engine.get_unread_count(business_id=test_business.id, db=db)
        assert remaining_unread == 0

    def test_unread_count(self, db, test_business):
        """get_unread_count returns the correct number of unread alerts."""
        from app.services.alert_engine import AlertEngine

        # Add 2 unread and 1 read alert
        for i in range(2):
            alert = Alert(
                business_id=test_business.id,
                type=AlertType.BUDGET_EXCEEDED,
                title=f"تجاوز الميزانية {i + 1}",
                message="تجاوزت الميزانية الشهرية",
                severity=AlertSeverity.HIGH,
                is_read=False,
            )
            db.add(alert)

        read_alert = Alert(
            business_id=test_business.id,
            type=AlertType.FORECAST_WARNING,
            title="تحذير التوقعات",
            message="التدفق النقدي المتوقع سلبي",
            severity=AlertSeverity.LOW,
            is_read=True,
        )
        db.add(read_alert)
        db.commit()

        engine = AlertEngine()
        count = engine.get_unread_count(business_id=test_business.id, db=db)

        assert count == 2


class TestAlertRoutes:
    """Route-level tests for /api/v1/alerts."""

    def test_get_alerts_returns_200(self, client, auth_headers):
        """GET /api/v1/alerts/ returns 200 and a list."""
        response = client.get("/api/v1/alerts/", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_alerts_requires_auth(self, client):
        """GET /api/v1/alerts/ without auth returns 403."""
        response = client.get("/api/v1/alerts/")
        assert response.status_code in (401, 403)

    def test_get_count_requires_auth(self, client):
        """GET /api/v1/alerts/count without auth returns 403."""
        response = client.get("/api/v1/alerts/count")
        assert response.status_code in (401, 403)

    def test_get_count_returns_unread(self, client, auth_headers):
        """GET /api/v1/alerts/count returns a JSON object with an 'unread' integer field."""
        response = client.get("/api/v1/alerts/count", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "unread" in data
        assert isinstance(data["unread"], int)
        assert data["unread"] >= 0

    def test_mark_all_read(self, client, auth_headers, db, test_business):
        """PATCH /api/v1/alerts/read-all returns {updated: int}."""
        # Seed an unread alert so the endpoint has something to update
        alert = Alert(
            business_id=test_business.id,
            type=AlertType.REVENUE_DROP,
            title="انخفاض الإيرادات",
            message="الإيرادات انخفضت هذا الشهر",
            severity=AlertSeverity.MEDIUM,
            is_read=False,
        )
        db.add(alert)
        db.commit()

        response = client.patch("/api/v1/alerts/read-all", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "updated" in data
        assert isinstance(data["updated"], int)
        assert data["updated"] >= 1

    def test_mark_single_read_not_found(self, client, auth_headers):
        """PATCH /api/v1/alerts/999/read returns 404 for a non-existent alert."""
        response = client.patch("/api/v1/alerts/999/read", headers=auth_headers)
        assert response.status_code == 404
