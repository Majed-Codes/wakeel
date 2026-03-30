"""
Dashboard API Tests.
"""

import pytest


class TestDashboardEndpoints:
    """Test dashboard summary endpoint."""

    def test_dashboard_empty(self, client, auth_headers):
        response = client.get("/api/v1/dashboard/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_income"] == 0
        assert data["total_expenses"] == 0
        assert data["transaction_count"] == 0
        assert data["recent_transactions"] == []

    def test_dashboard_with_transactions(self, client, auth_headers, sample_transactions):
        response = client.get("/api/v1/dashboard/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["transaction_count"] == 3
        # Revenue: 45000
        assert data["total_income"] == 45000
        # OpEx: 5000 + 12000 = 17000
        assert data["total_expenses"] == 17000
        assert len(data["recent_transactions"]) == 3

    def test_dashboard_requires_auth(self, client):
        response = client.get("/api/v1/dashboard/")
        assert response.status_code in (401, 403)

    def test_dashboard_recent_transactions_limited(self, client, auth_headers, db, test_business):
        """Dashboard returns max 10 recent transactions."""
        from app.models.transaction import Transaction, TransactionSource
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        for i in range(15):
            db.add(Transaction(
                business_id=test_business.id,
                amount=1000 + i,
                category="تشغيلية",
                description=f"معاملة {i+1}",
                source=TransactionSource.MANUAL,
                date=now,
            ))
        db.commit()

        response = client.get("/api/v1/dashboard/", headers=auth_headers)
        data = response.json()
        assert data["transaction_count"] == 15
        assert len(data["recent_transactions"]) == 10

    def test_dashboard_compliance_score(self, client, auth_headers, db, test_business):
        """Dashboard returns average compliance score from invoices."""
        from app.models.invoice import Invoice
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        db.add(Invoice(
            business_id=test_business.id,
            seller_name="test",
            date=now,
            total=1000,
            compliance_score=100.0,
        ))
        db.add(Invoice(
            business_id=test_business.id,
            seller_name="test2",
            date=now,
            total=2000,
            compliance_score=60.0,
        ))
        db.commit()

        response = client.get("/api/v1/dashboard/", headers=auth_headers)
        data = response.json()
        assert data["compliance_score"] == 80.0  # Average of 100 and 60
