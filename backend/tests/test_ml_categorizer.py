"""Tests for ML Transaction Categorizer."""

import pytest
from datetime import datetime


class TestMLCategorizerService:

    def test_rule_based_predict_returns_dict(self):
        from app.services.ml_categorizer import MLCategorizer
        cat = MLCategorizer()
        result = cat._rule_based_predict("راتب الموظفين")
        assert "category" in result
        assert "confidence" in result
        assert "source" in result

    def test_rule_based_salary_detection(self):
        from app.services.ml_categorizer import MLCategorizer
        cat = MLCategorizer()
        result = cat._rule_based_predict("رواتب شهر يناير")
        assert result["category"] == "رواتب"
        assert result["confidence"] >= 0.5

    def test_rule_based_utility_detection(self):
        from app.services.ml_categorizer import MLCategorizer
        cat = MLCategorizer()
        result = cat._rule_based_predict("فاتورة كهرباء الشهر")
        assert result["category"] == "مرافق"

    def test_default_category_for_unknown(self):
        from app.services.ml_categorizer import MLCategorizer
        cat = MLCategorizer()
        result = cat._rule_based_predict("xyz 123 unknown text")
        assert result["category"] == "تشغيلية"
        assert result["source"] == "default"

    def test_predict_falls_back_to_rules_when_no_model(self, db, test_business):
        from app.services.ml_categorizer import MLCategorizer
        cat = MLCategorizer()
        # No model trained, should fall back to rules
        result = cat.predict(text="مواد غذائية", business_id=test_business.id, db=db)
        assert "category" in result
        assert "confidence" in result

    def test_train_requires_minimum_samples(self, db, test_business):
        from app.services.ml_categorizer import MLCategorizer
        cat = MLCategorizer()
        result = cat.train(business_id=test_business.id, db=db)
        # test_business has no transactions, should fail with message
        assert result["success"] is False
        assert result["samples"] < 15

    def test_train_with_enough_samples(self, db, test_business):
        from app.services.ml_categorizer import MLCategorizer
        from app.models.transaction import Transaction, TransactionType, TransactionSource
        cat = MLCategorizer()

        # Create 20 labeled transactions
        categories = ["تشغيلية", "رواتب", "مرافق", "رأسمالية", "إيرادات"]
        vendors = ["مطعم", "موظفين", "كهرباء", "معدات", "عميل"]
        for i in range(20):
            cat_idx = i % len(categories)
            t = Transaction(
                business_id=test_business.id,
                amount=1000.0 + i * 100,
                vendor=vendors[cat_idx],
                description=f"معاملة {i}",
                category=categories[cat_idx],
                transaction_type=TransactionType.EXPENSE,
                source=TransactionSource.MANUAL,
                date=datetime.utcnow(),
            )
            db.add(t)
        db.commit()

        result = cat.train(business_id=test_business.id, db=db)
        assert result["success"] is True
        assert result["samples"] >= 15

    def test_get_model_info_untrained(self, db, test_business):
        from app.services.ml_categorizer import MLCategorizer
        cat = MLCategorizer()
        info = cat.get_model_info(business_id=test_business.id)
        assert info["trained"] is False

    def test_preprocess_arabic_text(self):
        from app.services.ml_categorizer import MLCategorizer
        cat = MLCategorizer()
        text = "فَاتُورَة الكَهربَاء"
        result = cat._preprocess(text)
        assert result  # not empty
        assert "فاتوره" in result or "فاتورة" in result or len(result) > 0

    def test_should_retrain_when_no_model(self, db, test_business):
        from app.services.ml_categorizer import MLCategorizer
        cat = MLCategorizer()
        # No model trained → should retrain
        assert cat.should_retrain(business_id=test_business.id, db=db) is True


class TestMLRoutes:

    def test_train_requires_auth(self, client):
        response = client.post("/api/v1/transactions/ml/train")
        assert response.status_code in (401, 403)

    def test_predict_requires_auth(self, client):
        response = client.post("/api/v1/transactions/ml/predict", params={"text": "test"})
        assert response.status_code in (401, 403)

    def test_info_requires_auth(self, client):
        response = client.get("/api/v1/transactions/ml/info")
        assert response.status_code in (401, 403)

    def test_train_with_auth_returns_result(self, client, auth_headers):
        response = client.post("/api/v1/transactions/ml/train", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "samples" in data

    def test_info_with_auth(self, client, auth_headers):
        response = client.get("/api/v1/transactions/ml/info", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "trained" in data

    def test_predict_with_auth(self, client, auth_headers):
        response = client.post(
            "/api/v1/transactions/ml/predict",
            params={"text": "مواد غذائية"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "category" in data
        assert "confidence" in data
