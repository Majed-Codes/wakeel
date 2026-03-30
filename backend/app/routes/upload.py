"""
Upload Routes — CSV/Excel bulk import for transactions.

Two-step flow:
  1. POST /preview — Upload file, get preview with auto-mapped columns
  2. POST /confirm — Confirm import with final column mapping
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import Business
from app.models.bulk_import import BulkImport
from app.schemas import UploadPreview, UploadConfirm, UploadResult
from app.auth.dependencies import get_current_user
from app.services.csv_importer import csv_importer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/upload", tags=["Upload"])

ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post(
    "/preview",
    response_model=UploadPreview,
    summary="معاينة ملف CSV/Excel",
    description="ارفع ملف CSV أو Excel لمعاينة البيانات قبل الاستيراد.",
)
async def upload_preview(
    file: UploadFile = File(...),
    current_user: Business = Depends(get_current_user),
):
    """
    Upload a CSV/Excel file and return a preview with auto-mapped columns.
    """
    # Validate extension
    filename = file.filename or "unknown"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"نوع ملف غير مدعوم. الأنواع المسموحة: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read and validate size
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="حجم الملف كبير جداً. الحد الأقصى: 10 ميجابايت",
        )

    # Parse file
    try:
        parsed = csv_importer.parse_file(file_bytes, filename)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Auto-map columns
    column_mapping = csv_importer.auto_map_columns(parsed["columns"])

    # Return preview with first 5 sample rows
    sample_rows = parsed["rows"][:5]

    return UploadPreview(
        filename=filename,
        total_rows=parsed["total_rows"],
        columns=parsed["columns"],
        column_mapping=column_mapping,
        sample_rows=sample_rows,
    )


@router.post(
    "/confirm",
    response_model=UploadResult,
    summary="تأكيد استيراد البيانات",
    description="أكّد استيراد المعاملات بعد مراجعة المعاينة.",
)
async def upload_confirm(
    data: UploadConfirm,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Confirm and import transactions after previewing the file.
    Optionally categorizes via Claude, then creates Transaction records.
    """
    # Categorize if no category mapping exists
    rows = data.rows
    if "category" not in data.column_mapping:
        rows = csv_importer.categorize_batch(rows)

    # Import transactions
    result = csv_importer.import_transactions(
        rows=rows,
        column_mapping=data.column_mapping,
        business_id=current_user.id,
        db=db,
    )

    # Create BulkImport record
    bulk_import = BulkImport(
        business_id=current_user.id,
        filename="bulk_upload",
        row_count=len(rows),
        success_count=result["imported"],
        error_count=len(result["errors"]),
        status="completed" if result["imported"] > 0 else "failed",
        errors=json.dumps(result["errors"], ensure_ascii=False) if result["errors"] else None,
    )
    db.add(bulk_import)
    db.commit()

    return UploadResult(
        imported=result["imported"],
        errors=result["errors"],
        filename="bulk_upload",
    )


@router.post("/bank-statement")
async def upload_bank_statement(
    file: UploadFile = File(...),
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Parse a Saudi bank statement (PDF or image) using Claude Vision."""
    from app.services.bank_statement_parser import bank_statement_parser
    content = await file.read()
    rows = bank_statement_parser.parse(content, file.content_type or "image/jpeg")
    return {
        "filename": file.filename,
        "total_rows": len(rows),
        "columns": ["date", "description", "amount", "transaction_type"],
        "column_mapping": {"date": "date", "description": "description", "amount": "amount"},
        "sample_rows": rows[:5],
        "all_rows": rows,
    }
