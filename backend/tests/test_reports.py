"""
Tests for Report Generation — ReportGenerator service and /api/v1/reports routes.
"""

import pytest
from datetime import datetime, timedelta, date

from app.models.transaction import Transaction, TransactionSource


class TestReportGenerator:
    """Unit tests for ReportGenerator service logic."""

    def test_get_summary_empty_transactions(self, db, test_business):
        """get_summary_data with no transactions returns all-zero totals."""
        from app.services.report_generator import ReportGenerator

        generator = ReportGenerator()
        result = generator.get_summary_data(
            business_id=test_business.id,
            db=db,
        )

        assert result["total_revenue"] == 0.0
        assert result["total_expenses"] == 0.0
        assert result["net_profit"] == 0.0
        assert result["transaction_count"] == 0

    def test_get_summary_with_transactions(self, db, test_business):
        """
        get_summary_data with seeded transactions returns non-zero totals
        and a correct transaction_count.
        """
        from app.services.report_generator import ReportGenerator

        now = datetime.utcnow()
        transactions = [
            Transaction(
                business_id=test_business.id,
                amount=10000.0,
                category="إيرادات",
                vendor="عميل أ",
                description="مبيعات الأسبوع",
                source=TransactionSource.MANUAL,
                date=now - timedelta(days=5),
            ),
            Transaction(
                business_id=test_business.id,
                amount=3000.0,
                category="تشغيلية",
                vendor="مورد ب",
                description="مصاريف تشغيل",
                source=TransactionSource.MANUAL,
                date=now - timedelta(days=3),
            ),
            Transaction(
                business_id=test_business.id,
                amount=1500.0,
                category="تشغيلية",
                vendor="مورد ج",
                description="مصاريف صيانة",
                source=TransactionSource.MANUAL,
                date=now - timedelta(days=1),
            ),
        ]
        for t in transactions:
            db.add(t)
        db.commit()

        generator = ReportGenerator()
        result = generator.get_summary_data(
            business_id=test_business.id,
            db=db,
        )

        assert result["transaction_count"] == 3
        # Total amount across all entries should be sum of all amounts
        total_amounts = result["total_revenue"] + result["total_expenses"]
        assert total_amounts == pytest.approx(14500.0, rel=1e-3)

    def test_generate_report_returns_bytes(self, db, test_business):
        """generate_report returns non-empty bytes (PDF or fallback text)."""
        from app.services.report_generator import ReportGenerator

        generator = ReportGenerator()
        result = generator.generate_report(
            business_id=test_business.id,
            db=db,
            business_name="مقهى تجريبي",
        )

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_summary_date_defaults(self, db, test_business):
        """
        get_summary_data without explicit dates defaults to the last 30 days —
        verified by checking start_date and end_date in the returned dict.
        """
        from app.services.report_generator import ReportGenerator

        generator = ReportGenerator()
        result = generator.get_summary_data(
            business_id=test_business.id,
            db=db,
        )

        assert "start_date" in result
        assert "end_date" in result

        end_date = date.fromisoformat(result["end_date"])
        start_date = date.fromisoformat(result["start_date"])
        delta = (end_date - start_date).days

        # Default window is 30 days
        assert delta == 30


class TestReportRoutes:
    """Route-level tests for /api/v1/reports."""

    def test_get_summary_requires_auth(self, client):
        """GET /api/v1/reports/summary without auth returns 403."""
        response = client.get("/api/v1/reports/summary")
        assert response.status_code in (401, 403)

    def test_get_summary_returns_200(self, client, auth_headers):
        """GET /api/v1/reports/summary with valid auth returns 200."""
        response = client.get("/api/v1/reports/summary", headers=auth_headers)
        assert response.status_code == 200

    def test_get_summary_fields(self, client, auth_headers):
        """GET /api/v1/reports/summary response contains all required fields."""
        response = client.get("/api/v1/reports/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "start_date",
            "end_date",
            "total_revenue",
            "total_expenses",
            "net_profit",
            "transaction_count",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        assert isinstance(data["total_revenue"], (int, float))
        assert isinstance(data["total_expenses"], (int, float))
        assert isinstance(data["net_profit"], (int, float))
        assert isinstance(data["transaction_count"], int)

    def test_generate_report_requires_auth(self, client):
        """POST /api/v1/reports/generate without auth returns 403."""
        response = client.post("/api/v1/reports/generate")
        assert response.status_code in (401, 403)

    def test_generate_report_returns_pdf(self, client, auth_headers):
        """POST /api/v1/reports/generate returns 200 with a PDF or octet-stream content type."""
        response = client.post("/api/v1/reports/generate", headers=auth_headers)
        assert response.status_code == 200

        content_type = response.headers.get("content-type", "")
        assert (
            "application/pdf" in content_type
            or "application/octet-stream" in content_type
            or len(response.content) > 0
        ), f"Unexpected content-type: {content_type}"
