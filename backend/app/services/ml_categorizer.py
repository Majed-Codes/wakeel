"""
ML Transaction Categorizer — TF-IDF + Random Forest for transaction categorization.

Fallback chain:
  1. ML model (trained on user's own transaction history — fast, free)
  2. Claude API (if API key configured)
  3. Rule-based defaults

Training:
  - Requires >= 50 labeled transactions per business
  - Auto-retrains when 20+ new transactions since last train
  - Model persisted in memory (per-business dict, reloaded on startup from DB)
"""

import logging
import pickle
import re
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.transaction import Transaction

logger = logging.getLogger(__name__)

# Try to import scikit-learn
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import cross_val_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available — ML categorizer disabled")


# Arabic category labels
CATEGORIES = ["تشغيلية", "رأسمالية", "إيرادات", "رواتب", "مرافق", "أخرى"]

# Minimum transactions to train
MIN_TRAIN_SAMPLES = 15  # lowered from 50 for practical use
# Retrain threshold
RETRAIN_THRESHOLD = 20


class MLCategorizer:
    """TF-IDF + RandomForest transaction categorizer per business."""

    def __init__(self):
        # Dict: business_id → {pipeline, trained_at, transaction_count}
        self._models: dict[int, dict] = {}

    def predict(self, text: str, business_id: int, db: Optional[Session] = None) -> dict:
        """
        Predict category for transaction text.

        Returns:
            dict: {category: str, confidence: float, source: str}
        """
        # Attempt ML prediction if model is trained
        if business_id in self._models and SKLEARN_AVAILABLE:
            model_info = self._models[business_id]
            pipeline = model_info["pipeline"]
            try:
                clean_text = self._preprocess(text)
                proba = pipeline.predict_proba([clean_text])[0]
                max_prob = float(max(proba))
                pred_class = pipeline.classes_[proba.argmax()]

                if max_prob >= 0.5:  # Minimum confidence threshold
                    return {
                        "category": pred_class,
                        "confidence": round(max_prob, 3),
                        "source": "ml",
                    }
            except Exception as e:
                logger.warning(f"ML prediction failed: {e}")

        # Fall back to rule-based
        return self._rule_based_predict(text)

    def train(self, business_id: int, db: Session) -> dict:
        """
        Train or retrain the ML model for a business using its transaction history.

        Returns:
            dict: {success, samples, accuracy, message}
        """
        if not SKLEARN_AVAILABLE:
            return {"success": False, "message": "scikit-learn not available", "samples": 0, "accuracy": 0}

        # Fetch labeled transactions (with category)
        transactions = (
            db.query(Transaction)
            .filter(
                Transaction.business_id == business_id,
                Transaction.category.isnot(None),
                Transaction.category != "",
            )
            .all()
        )

        if len(transactions) < MIN_TRAIN_SAMPLES:
            return {
                "success": False,
                "message": f"يحتاج التدريب إلى {MIN_TRAIN_SAMPLES} معاملة على الأقل، لديك {len(transactions)} فقط",
                "samples": len(transactions),
                "accuracy": 0,
            }

        # Prepare training data
        texts = []
        labels = []
        for t in transactions:
            combined = self._build_text(t.vendor, t.description, t.category)
            texts.append(self._preprocess(combined))
            labels.append(t.category)

        # Build pipeline: TF-IDF + RandomForest
        pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(
                analyzer="char_wb",  # Character n-grams (works well for Arabic)
                ngram_range=(2, 4),
                max_features=5000,
                sublinear_tf=True,
            )),
            ("clf", RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                class_weight="balanced",
                random_state=42,
            )),
        ])

        # Train
        pipeline.fit(texts, labels)

        # Estimate accuracy via cross-validation (if enough samples)
        accuracy = 0.0
        if len(transactions) >= 30:
            try:
                scores = cross_val_score(pipeline, texts, labels, cv=3, scoring="accuracy")
                accuracy = float(scores.mean())
            except Exception:
                accuracy = 0.0

        # Store model
        self._models[business_id] = {
            "pipeline": pipeline,
            "trained_at": datetime.utcnow(),
            "transaction_count": len(transactions),
            "accuracy": accuracy,
        }

        logger.info(
            f"ML model trained for business {business_id}: "
            f"{len(transactions)} samples, accuracy={accuracy:.2f}"
        )

        return {
            "success": True,
            "message": f"تم التدريب بنجاح على {len(transactions)} معاملة",
            "samples": len(transactions),
            "accuracy": round(accuracy, 3),
        }

    def should_retrain(self, business_id: int, db: Session) -> bool:
        """Check if model should be retrained."""
        if business_id not in self._models:
            return True

        model_info = self._models[business_id]
        last_count = model_info.get("transaction_count", 0)
        current_count = db.query(Transaction).filter(
            Transaction.business_id == business_id,
            Transaction.category.isnot(None),
        ).count()

        return (current_count - last_count) >= RETRAIN_THRESHOLD

    def get_model_info(self, business_id: int) -> dict:
        """Return model metadata if available."""
        if business_id not in self._models:
            return {"trained": False}
        info = self._models[business_id]
        return {
            "trained": True,
            "trained_at": info["trained_at"].isoformat(),
            "transaction_count": info["transaction_count"],
            "accuracy": info.get("accuracy", 0),
        }

    # ── Private methods ────────────────────────────────────────────────────────

    def _preprocess(self, text: str) -> str:
        """Normalize Arabic text for vectorization."""
        if not text:
            return ""
        # Remove diacritics (تشكيل)
        text = re.sub(r"[\u0610-\u061A\u064B-\u065F]", "", text)
        # Normalize alef variants
        text = re.sub(r"[أإآا]", "ا", text)
        # Normalize teh marbuta
        text = re.sub(r"ة", "ه", text)
        # Remove punctuation but keep spaces
        text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
        return text.lower().strip()

    def _build_text(self, vendor: Optional[str], description: Optional[str], category: Optional[str] = None) -> str:
        """Combine fields into training text."""
        parts = [vendor or "", description or ""]
        return " ".join(p for p in parts if p)

    def _rule_based_predict(self, text: str) -> dict:
        """
        Simple keyword-based category prediction.
        Returns default تشغيلية with low confidence if no match.
        """
        text_lower = (text or "").lower()

        rules = [
            (["راتب", "رواتب", "salari", "payroll", "أجور"], "رواتب", 0.85),
            (["كهرباء", "ماء", "غاز", "اتصال", "انترنت", "utility", "electric", "water", "internet"], "مرافق", 0.85),
            (["معدات", "أجهزة", "equipment", "asset", "computer", "laptop", "طابعة"], "رأسمالية", 0.80),
            (["مبيعات", "فاتورة", "revenue", "income", "إيراد", "مبيع"], "إيرادات", 0.80),
            (["غذاء", "مواد", "مطعم", "قهوة", "food", "coffee", "supply", "مستلزمات"], "تشغيلية", 0.70),
        ]

        for keywords, category, confidence in rules:
            if any(kw in text_lower for kw in keywords):
                return {"category": category, "confidence": confidence, "source": "rules"}

        return {"category": "تشغيلية", "confidence": 0.4, "source": "default"}


ml_categorizer = MLCategorizer()
