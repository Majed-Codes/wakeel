"""
CSV/Excel Bulk Importer — parse, map, categorize, and import transactions.

Supports CSV (.csv) and Excel (.xlsx, .xls) files with Arabic and English headers.
Uses Claude for AI-powered batch categorization when available.
"""

import io
import logging
from typing import List, Optional
from datetime import datetime

import pandas as pd

from app.config import settings
from app.models.transaction import Transaction, TransactionSource
from app.services.rag import financial_rag

logger = logging.getLogger(__name__)

# ── Column Mapping Dictionaries ─────────────────────────────────

ARABIC_COLUMN_MAP = {
    "المبلغ": "amount",
    "القيمة": "amount",
    "السعر": "amount",
    "التاريخ": "date",
    "تاريخ": "date",
    "تاريخ المعاملة": "date",
    "الجهة": "vendor",
    "المورد": "vendor",
    "اسم المورد": "vendor",
    "الشركة": "vendor",
    "الوصف": "description",
    "البيان": "description",
    "ملاحظات": "description",
    "التفاصيل": "description",
    "التصنيف": "category",
    "الفئة": "category",
    "النوع": "category",
}

ENGLISH_COLUMN_MAP = {
    "amount": "amount",
    "value": "amount",
    "price": "amount",
    "total": "amount",
    "date": "date",
    "transaction_date": "date",
    "transaction date": "date",
    "vendor": "vendor",
    "supplier": "vendor",
    "company": "vendor",
    "merchant": "vendor",
    "description": "description",
    "desc": "description",
    "details": "description",
    "note": "description",
    "notes": "description",
    "memo": "description",
    "category": "category",
    "type": "category",
    "class": "category",
}


class CSVImporter:
    """Handles parsing, mapping, categorization, and importing of CSV/Excel files."""

    # ── File Parsing ────────────────────────────────────────────

    def parse_file(self, file_bytes: bytes, filename: str) -> dict:
        """
        Parse a CSV or Excel file into rows and columns.

        Args:
            file_bytes: Raw file content
            filename: Original filename (used to detect format)

        Returns:
            {"columns": List[str], "rows": List[dict], "total_rows": int}

        Raises:
            ValueError: If file format is unsupported or file is malformed
        """
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        try:
            if ext == "csv":
                df = pd.read_csv(io.BytesIO(file_bytes))
            elif ext in ("xlsx", "xls"):
                df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
            else:
                raise ValueError(f"نوع ملف غير مدعوم: .{ext}")
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to parse file {filename}: {e}")
            raise ValueError(f"خطأ في قراءة الملف: {str(e)}")

        # Clean up: strip whitespace from column names
        df.columns = [str(col).strip() for col in df.columns]

        # Drop completely empty rows
        df = df.dropna(how="all")

        # Convert NaN to None for JSON serialization
        df = df.where(pd.notna(df), None)

        columns = list(df.columns)
        rows = df.to_dict(orient="records")

        return {
            "columns": columns,
            "rows": rows,
            "total_rows": len(rows),
        }

    # ── Column Auto-Mapping ─────────────────────────────────────

    def auto_map_columns(self, columns: List[str]) -> dict:
        """
        Automatically map file column headers to transaction fields.

        Supports Arabic and English headers with case-insensitive fuzzy matching.

        Args:
            columns: List of column header strings from the file

        Returns:
            Mapping dict, e.g. {"amount": "المبلغ", "date": "التاريخ", ...}
        """
        mapping = {}

        for col in columns:
            col_clean = col.strip()
            col_lower = col_clean.lower()

            # Check Arabic mappings (exact match, Arabic is case-insensitive by nature)
            if col_clean in ARABIC_COLUMN_MAP:
                field = ARABIC_COLUMN_MAP[col_clean]
                if field not in mapping:
                    mapping[field] = col_clean
                continue

            # Check English mappings (case-insensitive)
            if col_lower in ENGLISH_COLUMN_MAP:
                field = ENGLISH_COLUMN_MAP[col_lower]
                if field not in mapping:
                    mapping[field] = col_clean
                continue

            # Fuzzy: check if any known key is contained in the column name
            matched = False
            for key, field in ARABIC_COLUMN_MAP.items():
                if key in col_clean and field not in mapping:
                    mapping[field] = col_clean
                    matched = True
                    break
            if matched:
                continue

            for key, field in ENGLISH_COLUMN_MAP.items():
                if key in col_lower and field not in mapping:
                    mapping[field] = col_clean
                    matched = True
                    break

        return mapping

    # ── AI Batch Categorization ─────────────────────────────────

    def categorize_batch(self, rows: List[dict]) -> List[dict]:
        """
        Use Claude to categorize transactions in batches.

        Categories: تشغيلية (OpEx), رأسمالية (CapEx), إيرادات (Revenue)

        Args:
            rows: List of row dicts (each must have at least description/vendor)

        Returns:
            Same rows with "category" field added/updated
        """
        if not settings.has_anthropic_key:
            logger.info("No Anthropic API key — assigning default category 'تشغيلية'")
            for row in rows:
                if not row.get("category"):
                    row["category"] = "تشغيلية"
            return rows

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
            for row in rows:
                if not row.get("category"):
                    row["category"] = "تشغيلية"
            return rows

        # Process in batches of 20
        batch_size = 20
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]

            # Build batch description for Claude
            items = []
            for idx, row in enumerate(batch):
                desc = row.get("description", "") or ""
                vendor = row.get("vendor", "") or ""
                amount = row.get("amount", "") or ""
                items.append(f"{idx + 1}. المبلغ: {amount}, الجهة: {vendor}, الوصف: {desc}")

            prompt = (
                "صنّف كل معاملة من المعاملات التالية إلى واحدة من هذه الفئات:\n"
                "- تشغيلية (مصاريف تشغيل يومية)\n"
                "- رأسمالية (أصول ومعدات)\n"
                "- إيرادات (دخل ومبيعات)\n\n"
                "المعاملات:\n" + "\n".join(items) + "\n\n"
                "أجب بأرقام المعاملات وتصنيفها فقط، كل معاملة في سطر:\n"
                "1. تشغيلية\n2. إيرادات\n..."
            )

            try:
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                result_text = response.content[0].text

                # Parse response lines
                for line in result_text.strip().split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    # Extract number and category
                    parts = line.split(".", 1)
                    if len(parts) == 2:
                        try:
                            num = int(parts[0].strip()) - 1
                            cat = parts[1].strip()
                            if 0 <= num < len(batch):
                                if cat in ("تشغيلية", "رأسمالية", "إيرادات"):
                                    batch[num]["category"] = cat
                        except (ValueError, IndexError):
                            continue

            except Exception as e:
                logger.warning(f"Claude categorization failed for batch {i // batch_size}: {e}")

            # Fill any remaining uncategorized
            for row in batch:
                if not row.get("category"):
                    row["category"] = "تشغيلية"

        return rows

    # ── Transaction Import ──────────────────────────────────────

    def import_transactions(
        self,
        rows: List[dict],
        column_mapping: dict,
        business_id: int,
        db,
    ) -> dict:
        """
        Create Transaction objects from parsed rows.

        Args:
            rows: List of row dicts from the parsed file
            column_mapping: Field mapping, e.g. {"amount": "المبلغ", ...}
            business_id: ID of the business that owns these transactions
            db: SQLAlchemy session

        Returns:
            {"imported": int, "errors": List[dict]}
        """
        imported = 0
        errors = []

        # Reverse the mapping: file_column -> transaction_field
        reverse_map = {v: k for k, v in column_mapping.items()}

        for idx, row in enumerate(rows):
            try:
                # Map row values using column_mapping
                mapped = {}
                for file_col, value in row.items():
                    if file_col in reverse_map:
                        mapped[reverse_map[file_col]] = value

                # Amount is required
                amount_raw = mapped.get("amount")
                if amount_raw is None:
                    errors.append({
                        "row": idx + 1,
                        "error": "المبلغ مطلوب",
                        "data": row,
                    })
                    continue

                try:
                    amount = float(amount_raw)
                except (ValueError, TypeError):
                    errors.append({
                        "row": idx + 1,
                        "error": f"قيمة المبلغ غير صالحة: {amount_raw}",
                        "data": row,
                    })
                    continue

                # Parse date
                txn_date = None
                date_raw = mapped.get("date")
                if date_raw is not None:
                    try:
                        if isinstance(date_raw, datetime):
                            txn_date = date_raw
                        else:
                            txn_date = pd.to_datetime(str(date_raw)).to_pydatetime()
                    except Exception:
                        # If date parsing fails, use current time
                        txn_date = None

                transaction = Transaction(
                    business_id=business_id,
                    amount=amount,
                    category=mapped.get("category") or row.get("category", "تشغيلية"),
                    description=mapped.get("description"),
                    vendor=mapped.get("vendor"),
                    date=txn_date,
                    source=TransactionSource.CSV,
                    confidence=1.0,
                    raw_transcription=None,
                )

                db.add(transaction)
                db.flush()  # Get ID for RAG indexing

                # Index in RAG
                try:
                    financial_rag.index_single_transaction(transaction, business_id)
                except Exception as e:
                    logger.warning(f"RAG indexing failed for row {idx + 1}: {e}")

                imported += 1

            except Exception as e:
                logger.error(f"Failed to import row {idx + 1}: {e}")
                errors.append({
                    "row": idx + 1,
                    "error": str(e),
                    "data": row,
                })

        # Commit all successful transactions
        if imported > 0:
            db.commit()

        return {
            "imported": imported,
            "errors": errors,
        }


# Singleton instance
csv_importer = CSVImporter()
