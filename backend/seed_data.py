"""
Seed Data Script — Populate Wakeel AI with realistic Saudi SME demo data.

Usage: cd wakeel-ai/backend && ./venv/bin/python seed_data.py

Creates:
- 1 demo business (مقهى الوكيل)
- 25+ transactions across 6 months
- 3 sample invoices for compliance testing
- Indexes all transactions into ChromaDB
"""

import sys
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure app is importable
sys.path.insert(0, str(Path(__file__).parent))

from app.database import engine, SessionLocal, Base
from app.models.user import Business
from app.models.transaction import Transaction, TransactionSource
from app.models.invoice import Invoice
from app.models.chat import ChatHistory
from app.auth.utils import hash_password
from app.services.rag import financial_rag


def seed():
    # Create tables
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if demo user already exists
        existing = db.query(Business).filter(Business.phone == "0501234567").first()
        if existing:
            print("⚠️  Demo business already exists. Cleaning up old data...")
            db.query(ChatHistory).filter(ChatHistory.business_id == existing.id).delete()
            db.query(Transaction).filter(Transaction.business_id == existing.id).delete()
            db.query(Invoice).filter(Invoice.business_id == existing.id).delete()
            db.delete(existing)
            db.commit()

        # === Create Demo Business ===
        business = Business(
            name="مقهى الوكيل",
            phone="0501234567",
            email="demo@wakeel.ai",
            hashed_password=hash_password("demo123"),
            is_active=True,
        )
        db.add(business)
        db.commit()
        db.refresh(business)
        print(f"✅ Created demo business: {business.name} (ID: {business.id})")

        # === Create Transactions ===
        now = datetime.now(timezone.utc)
        transactions_data = [
            # --- Month 1 (6 months ago) ---
            {"amount": 12000, "category": "تشغيلية", "description": "إيجار المحل الشهري", "vendor": "شركة العقارات المتحدة", "source": "manual", "days_ago": 180},
            {"amount": 3500, "category": "تشغيلية", "description": "توريد بن وقهوة", "vendor": "المراعي", "source": "voice", "days_ago": 178, "confidence": 0.95, "transcription": "حولت ثلاثة آلاف وخمسمية للمراعي حق القهوة"},
            {"amount": 45000, "category": "إيرادات", "description": "مبيعات الشهر", "vendor": "عملاء متنوعين", "source": "manual", "days_ago": 170},
            {"amount": 8000, "category": "تشغيلية", "description": "رواتب الموظفين", "vendor": "موظفين", "source": "manual", "days_ago": 165},
            {"amount": 1200, "category": "تشغيلية", "description": "فاتورة الكهرباء", "vendor": "شركة الكهرباء السعودية", "source": "voice", "days_ago": 160, "confidence": 0.88, "transcription": "دفعت ألف ومئتين حق الكهرباء"},

            # --- Month 2 (5 months ago) ---
            {"amount": 12000, "category": "تشغيلية", "description": "إيجار المحل الشهري", "vendor": "شركة العقارات المتحدة", "source": "manual", "days_ago": 150},
            {"amount": 4200, "category": "تشغيلية", "description": "توريد حليب ومنتجات ألبان", "vendor": "نادك", "source": "voice", "days_ago": 148, "confidence": 0.92, "transcription": "حولت أربعة آلاف ومئتين لنادك توريد حليب"},
            {"amount": 52000, "category": "إيرادات", "description": "مبيعات الشهر", "vendor": "عملاء متنوعين", "source": "manual", "days_ago": 140},
            {"amount": 8000, "category": "تشغيلية", "description": "رواتب الموظفين", "vendor": "موظفين", "source": "manual", "days_ago": 135},
            {"amount": 2500, "category": "تشغيلية", "description": "صيانة ماكينة القهوة", "vendor": "شركة الصيانة", "source": "manual", "days_ago": 130},

            # --- Month 3 (4 months ago) ---
            {"amount": 12000, "category": "تشغيلية", "description": "إيجار المحل الشهري", "vendor": "شركة العقارات المتحدة", "source": "manual", "days_ago": 120},
            {"amount": 15000, "category": "رأسمالية", "description": "شراء ماكينة إسبريسو جديدة", "vendor": "معدات المقاهي", "source": "manual", "days_ago": 115},
            {"amount": 48000, "category": "إيرادات", "description": "مبيعات الشهر", "vendor": "عملاء متنوعين", "source": "manual", "days_ago": 110},
            {"amount": 8000, "category": "تشغيلية", "description": "رواتب الموظفين", "vendor": "موظفين", "source": "manual", "days_ago": 105},
            {"amount": 3800, "category": "تشغيلية", "description": "توريد بن وقهوة", "vendor": "المراعي", "source": "voice", "days_ago": 100, "confidence": 0.93, "transcription": "صرفت ثلاثة آلاف وثمانمية للمراعي"},

            # --- Month 4 (3 months ago) ---
            {"amount": 12000, "category": "تشغيلية", "description": "إيجار المحل الشهري", "vendor": "شركة العقارات المتحدة", "source": "manual", "days_ago": 90},
            {"amount": 61000, "category": "إيرادات", "description": "مبيعات الشهر — موسم رمضان", "vendor": "عملاء متنوعين", "source": "manual", "days_ago": 80},
            {"amount": 5000, "category": "تشغيلية", "description": "توريد تمور ومكسرات رمضان", "vendor": "مؤسسة التمور الفاخرة", "source": "voice", "days_ago": 85, "confidence": 0.91, "transcription": "حولت خمسة آلاف ريال لمؤسسة التمور الفاخرة حق تمور رمضان"},
            {"amount": 10000, "category": "تشغيلية", "description": "رواتب الموظفين + بونص رمضان", "vendor": "موظفين", "source": "manual", "days_ago": 75},

            # --- Month 5 (2 months ago) ---
            {"amount": 12000, "category": "تشغيلية", "description": "إيجار المحل الشهري", "vendor": "شركة العقارات المتحدة", "source": "manual", "days_ago": 60},
            {"amount": 55000, "category": "إيرادات", "description": "مبيعات الشهر", "vendor": "عملاء متنوعين", "source": "manual", "days_ago": 50},
            {"amount": 8000, "category": "تشغيلية", "description": "رواتب الموظفين", "vendor": "موظفين", "source": "manual", "days_ago": 45},
            {"amount": 900, "category": "تشغيلية", "description": "فاتورة الماء", "vendor": "شركة المياه الوطنية", "source": "voice", "days_ago": 55, "confidence": 0.87, "transcription": "دفعت تسعمية حق فاتورة الماء"},
            {"amount": 7500, "category": "رأسمالية", "description": "شراء طاولات وكراسي جديدة", "vendor": "ايكيا", "source": "manual", "days_ago": 48},

            # --- Month 6 (this month) ---
            {"amount": 12000, "category": "تشغيلية", "description": "إيجار المحل الشهري", "vendor": "شركة العقارات المتحدة", "source": "manual", "days_ago": 25},
            {"amount": 67000, "category": "إيرادات", "description": "مبيعات الشهر", "vendor": "عملاء متنوعين", "source": "manual", "days_ago": 5},
            {"amount": 8000, "category": "تشغيلية", "description": "رواتب الموظفين", "vendor": "موظفين", "source": "manual", "days_ago": 15},
            {"amount": 4000, "category": "تشغيلية", "description": "توريد بن وقهوة ومواد", "vendor": "المراعي", "source": "voice", "days_ago": 20, "confidence": 0.94, "transcription": "حولت أربعة آلاف للمراعي حق القهوة والمواد"},
            {"amount": 1500, "category": "تشغيلية", "description": "اشتراك إنترنت وهاتف", "vendor": "موبايلي", "source": "manual", "days_ago": 10},
        ]

        created_transactions = []
        for t in transactions_data:
            source = TransactionSource.VOICE if t["source"] == "voice" else TransactionSource.MANUAL
            txn = Transaction(
                business_id=business.id,
                amount=t["amount"],
                category=t["category"],
                description=t["description"],
                vendor=t["vendor"],
                date=now - timedelta(days=t["days_ago"]),
                source=source,
                confidence=t.get("confidence"),
                raw_transcription=t.get("transcription"),
            )
            db.add(txn)
            created_transactions.append(txn)

        db.commit()

        # Refresh all transactions to get IDs
        for txn in created_transactions:
            db.refresh(txn)

        print(f"✅ Created {len(created_transactions)} transactions")

        # === Create Sample Invoices ===
        invoices_data = [
            {
                "seller_name": "المراعي للتجارة",
                "seller_vat": "300000000000003",
                "buyer_name": "مقهى الوكيل",
                "date": now - timedelta(days=20),
                "total": 4600.0,
                "vat_amount": 600.0,
                "qr_code": "TVRJR05FUkFJLi4u",
                "is_compliant": True,
                "compliance_score": 100.0,
            },
            {
                "seller_name": "شركة الكهرباء",
                "seller_vat": "300000000000007",
                "buyer_name": "مقهى الوكيل",
                "date": now - timedelta(days=30),
                "total": 1380.0,
                "vat_amount": 180.0,
                "qr_code": "RUxFQ1RSSUMuLi4=",
                "is_compliant": True,
                "compliance_score": 100.0,
            },
            {
                "seller_name": "مؤسسة التمور",
                "seller_vat": "",  # Missing VAT — non-compliant
                "buyer_name": "مقهى الوكيل",
                "date": now - timedelta(days=85),
                "total": 5750.0,
                "vat_amount": 750.0,
                "qr_code": "",  # Missing QR — non-compliant
                "is_compliant": False,
                "compliance_score": 55.0,
                "validation_errors": "حقل مفقود: الرقم الضريبي للبائع, رمز QR مفقود",
            },
        ]

        for inv_data in invoices_data:
            invoice = Invoice(business_id=business.id, **inv_data)
            db.add(invoice)

        db.commit()
        print(f"✅ Created {len(invoices_data)} sample invoices")

        # === Index Transactions in ChromaDB ===
        print("📊 Indexing transactions in ChromaDB...")
        financial_rag.index_transactions(created_transactions, business.id)
        print("✅ Transactions indexed for RAG")

        # === Summary ===
        total_income = sum(t["amount"] for t in transactions_data if t["category"] == "إيرادات")
        total_expenses = sum(t["amount"] for t in transactions_data if t["category"] in ("تشغيلية", "رأسمالية"))
        print("\n" + "=" * 50)
        print("📋 SEED DATA SUMMARY")
        print("=" * 50)
        print(f"Business: {business.name}")
        print(f"Phone: 0501234567")
        print(f"Password: demo123")
        print(f"Transactions: {len(created_transactions)}")
        print(f"  - إيرادات (Revenue): {total_income:,.0f} SAR")
        print(f"  - مصاريف (Expenses): {total_expenses:,.0f} SAR")
        print(f"  - صافي (Net): {total_income - total_expenses:,.0f} SAR")
        print(f"Invoices: {len(invoices_data)}")
        print(f"  - Compliant: {sum(1 for i in invoices_data if i['is_compliant'])}")
        print(f"  - Non-compliant: {sum(1 for i in invoices_data if not i['is_compliant'])}")
        print("=" * 50)
        print("\n🚀 Login with: phone=0501234567, password=demo123")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
