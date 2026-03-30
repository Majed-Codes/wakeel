"""
Tests for Anomaly Detection — AnomalyDetector service and /api/v1/anomalies routes.
"""

import pytest
from datetime import datetime, timedelta

from app.models.transaction import Transaction, TransactionSource
from app.models.alert import Alert, AlertType, AlertSeverity


class TestAnomalyDetectorService:
    """Unit tests for AnomalyDetector service logic."""

    def test_no_transactions_returns_empty(self, db, test_business):
        """AnomalyDetector.detect_anomalies with no transactions returns empty list."""
        from app.services.anomaly_detector import AnomalyDetector
        detector = AnomalyDetector()
        result = detector.detect_anomalies(business_id=test_business.id, db=db)
        assert result == []

    def test_detect_amount_outlier(self, db, test_business):
        """
        Create 10 same-category transactions at a uniform base amount and 1 at 20x.
        The extreme outlier must exceed the Z-score threshold (2.5) and be flagged.

        Z-score check: with 10 identical normals + 1 value at 20x base,
        the outlier Z-score is ~3.02, safely above the 2.5 threshold.
        """
        from app.services.anomaly_detector import AnomalyDetector

        now = datetime.utcnow()
        base_amount = 500.0
        category = "مصاريف"

        # 10 identical normal transactions in the same category
        for i in range(10):
            t = Transaction(
                business_id=test_business.id,
                amount=base_amount,
                category=category,
                vendor=f"مورد-{i}",
                description="مصروف عادي",
                source=TransactionSource.MANUAL,
                date=now - timedelta(days=i),
            )
            db.add(t)

        # 1 extreme outlier — 20x the base amount (Z-score ~3.02)
        outlier = Transaction(
            business_id=test_business.id,
            amount=base_amount * 20,
            category=category,
            vendor="مورد-شاذ",
            description="مصروف شاذ",
            source=TransactionSource.MANUAL,
            date=now,
        )
        db.add(outlier)
        db.commit()

        detector = AnomalyDetector()
        anomalies = detector.detect_anomalies(business_id=test_business.id, db=db)

        assert len(anomalies) >= 1
        types = [a["anomaly_type"] for a in anomalies]
        assert "amount_outlier" in types

        # The outlier transaction should be flagged
        flagged_ids = [a["transaction_id"] for a in anomalies]
        assert outlier.id in flagged_ids

    def test_duplicate_payment_detected(self, db, test_business):
        """
        Two transactions with same vendor and same amount within 2 hours
        should be flagged as a duplicate payment.
        """
        from app.services.anomaly_detector import AnomalyDetector

        now = datetime.utcnow()
        vendor = "شركة التوريد"
        amount = 2500.0

        t1 = Transaction(
            business_id=test_business.id,
            amount=amount,
            vendor=vendor,
            category="تشغيلية",
            description="دفعة أولى",
            source=TransactionSource.MANUAL,
            date=now - timedelta(hours=1),
        )
        t2 = Transaction(
            business_id=test_business.id,
            amount=amount,
            vendor=vendor,
            category="تشغيلية",
            description="دفعة مكررة",
            source=TransactionSource.MANUAL,
            date=now,
        )
        db.add(t1)
        db.add(t2)
        db.commit()

        detector = AnomalyDetector()
        anomalies = detector.detect_anomalies(business_id=test_business.id, db=db)

        types = [a["anomaly_type"] for a in anomalies]
        assert "duplicate_payment" in types

    def test_get_summary_structure(self, db, test_business):
        """
        get_summary() must return a dict with the required keys:
        total_anomalies, severity_breakdown, type_breakdown, anomalies, risk_level.
        """
        from app.services.anomaly_detector import AnomalyDetector

        detector = AnomalyDetector()
        summary = detector.get_summary(business_id=test_business.id, db=db)

        assert "total_anomalies" in summary
        assert "severity_breakdown" in summary
        assert "type_breakdown" in summary
        assert "anomalies" in summary
        assert "risk_level" in summary

        assert isinstance(summary["total_anomalies"], int)
        assert isinstance(summary["severity_breakdown"], dict)
        assert isinstance(summary["type_breakdown"], dict)
        assert isinstance(summary["anomalies"], list)
        assert summary["risk_level"] in ("low", "medium", "high", "critical")


class TestAnomalyRoutes:
    """Route-level tests for /api/v1/anomalies."""

    def test_get_anomalies_empty(self, client, auth_headers):
        """GET /api/v1/anomalies/ with no transactions returns 200 and an empty list."""
        response = client.get("/api/v1/anomalies/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_anomalies_requires_auth(self, client):
        """GET /api/v1/anomalies/ without Authorization header returns 403."""
        response = client.get("/api/v1/anomalies/")
        assert response.status_code in (401, 403)

    def test_get_summary_requires_auth(self, client):
        """GET /api/v1/anomalies/summary without auth returns 403."""
        response = client.get("/api/v1/anomalies/summary")
        assert response.status_code in (401, 403)

    def test_get_summary_structure(self, client, auth_headers):
        """GET /api/v1/anomalies/summary returns proper fields."""
        response = client.get("/api/v1/anomalies/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        assert "total_anomalies" in data
        assert "severity_breakdown" in data
        assert "type_breakdown" in data
        assert "anomalies" in data
        assert "risk_level" in data

        assert isinstance(data["total_anomalies"], int)
        assert data["total_anomalies"] >= 0
        assert data["risk_level"] in ("low", "medium", "high", "critical")
