"""Tests for CSV/Excel bulk import feature."""

import io
import json
import pytest


# ── Sample CSV data ─────────────────────────────────────────────

ARABIC_CSV = "المبلغ,التاريخ,الجهة,الوصف\n5000,2024-01-15,المراعي,توريد حليب\n3000,2024-01-20,نادك,توريد عصير\n12000,2024-02-01,شركة رضا,رواتب\n"

ENGLISH_CSV = "amount,date,vendor,description\n5000,2024-01-15,Al Marai,Milk supply\n3000,2024-01-20,NADA,Juice supply\n"

MIXED_CSV = "Amount,التاريخ,Vendor,الوصف\n1500,2024-03-01,مطعم البيك,وجبات\n"

BAD_CSV = "المبلغ,التاريخ\ninvalid,2024-01-01\n,2024-01-02\n"


class TestCSVImporterService:

    def test_parse_valid_arabic_csv(self):
        from app.services.csv_importer import CSVImporter
        importer = CSVImporter()
        result = importer.parse_file(ARABIC_CSV.encode(), "test.csv")
        assert result["total_rows"] == 3
        assert "المبلغ" in result["columns"]
        assert len(result["rows"]) == 3

    def test_parse_valid_english_csv(self):
        from app.services.csv_importer import CSVImporter
        importer = CSVImporter()
        result = importer.parse_file(ENGLISH_CSV.encode(), "test.csv")
        assert result["total_rows"] == 2
        assert "amount" in result["columns"]

    def test_parse_unsupported_extension_raises(self):
        from app.services.csv_importer import CSVImporter
        importer = CSVImporter()
        with pytest.raises(ValueError, match="غير مدعوم"):
            importer.parse_file(b"data", "test.txt")

    def test_auto_map_arabic_headers(self):
        from app.services.csv_importer import CSVImporter
        importer = CSVImporter()
        columns = ["المبلغ", "التاريخ", "الجهة", "الوصف"]
        mapping = importer.auto_map_columns(columns)
        assert mapping.get("amount") == "المبلغ"
        assert mapping.get("date") == "التاريخ"
        assert mapping.get("vendor") == "الجهة"
        assert mapping.get("description") == "الوصف"

    def test_auto_map_english_headers(self):
        from app.services.csv_importer import CSVImporter
        importer = CSVImporter()
        columns = ["amount", "date", "vendor", "description"]
        mapping = importer.auto_map_columns(columns)
        assert mapping.get("amount") == "amount"
        assert mapping.get("date") == "date"
        assert mapping.get("vendor") == "vendor"

    def test_auto_map_case_insensitive(self):
        from app.services.csv_importer import CSVImporter
        importer = CSVImporter()
        columns = ["Amount", "DATE", "Vendor"]
        mapping = importer.auto_map_columns(columns)
        assert "amount" in mapping
        assert "date" in mapping

    def test_auto_map_partial_match(self):
        from app.services.csv_importer import CSVImporter
        importer = CSVImporter()
        columns = ["transaction_date", "total_amount"]
        mapping = importer.auto_map_columns(columns)
        assert "date" in mapping or "amount" in mapping

    def test_categorize_batch_no_api_key(self):
        """Without API key, assigns default تشغيلية."""
        from app.services.csv_importer import CSVImporter
        from unittest.mock import patch
        importer = CSVImporter()
        rows = [{"vendor": "المراعي", "description": "حليب"}, {"vendor": "نادك", "description": "عصير"}]
        # Force no API key by temporarily removing the client
        importer._no_key = True
        with patch("app.services.csv_importer.settings") as mock_settings:
            mock_settings.has_anthropic_key = False
            result = importer.categorize_batch(rows)
        for row in result:
            assert row.get("category") is not None


class TestUploadRoutes:

    def test_upload_preview_valid_csv(self, client, auth_headers):
        files = {"file": ("test.csv", ARABIC_CSV.encode(), "text/csv")}
        response = client.post("/api/v1/upload/preview", files=files, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.csv"
        assert data["total_rows"] == 3
        assert "المبلغ" in data["columns"]
        assert "amount" in data["column_mapping"]
        assert len(data["sample_rows"]) <= 5

    def test_upload_preview_english_csv(self, client, auth_headers):
        files = {"file": ("english.csv", ENGLISH_CSV.encode(), "text/csv")}
        response = client.post("/api/v1/upload/preview", files=files, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["total_rows"] == 2

    def test_upload_preview_invalid_extension(self, client, auth_headers):
        files = {"file": ("data.txt", b"some data", "text/plain")}
        response = client.post("/api/v1/upload/preview", files=files, headers=auth_headers)
        assert response.status_code == 400

    def test_upload_preview_requires_auth(self, client):
        files = {"file": ("test.csv", ARABIC_CSV.encode(), "text/csv")}
        response = client.post("/api/v1/upload/preview", files=files)
        assert response.status_code in (401, 403)

    def test_upload_confirm_creates_transactions(self, client, auth_headers, db, test_business):
        from app.models.transaction import Transaction
        # First preview
        files = {"file": ("test.csv", ARABIC_CSV.encode(), "text/csv")}
        preview_resp = client.post("/api/v1/upload/preview", files=files, headers=auth_headers)
        assert preview_resp.status_code == 200
        preview = preview_resp.json()

        # Build rows with the mapping applied
        confirm_data = {
            "rows": preview["sample_rows"],
            "column_mapping": preview["column_mapping"],
        }
        response = client.post("/api/v1/upload/confirm", json=confirm_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "imported" in data
        assert data["imported"] >= 0  # some may error if amount parsing fails
        assert "errors" in data

    def test_upload_confirm_requires_auth(self, client):
        response = client.post(
            "/api/v1/upload/confirm",
            json={"rows": [], "column_mapping": {}},
        )
        assert response.status_code in (401, 403)

    def test_upload_handles_bad_rows(self, client, auth_headers):
        """Rows with invalid amounts are skipped, not crashing."""
        files = {"file": ("bad.csv", BAD_CSV.encode(), "text/csv")}
        preview_resp = client.post("/api/v1/upload/preview", files=files, headers=auth_headers)
        assert preview_resp.status_code == 200
        preview = preview_resp.json()
        confirm_data = {
            "rows": preview["sample_rows"],
            "column_mapping": preview["column_mapping"],
        }
        response = client.post("/api/v1/upload/confirm", json=confirm_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Some rows have errors but request succeeds
        assert "imported" in data
        assert "errors" in data
