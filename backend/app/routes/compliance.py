"""
Compliance Routes — ZATCA invoice validation and e-invoice generation.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional

from app.database import get_db
from app.models.user import Business
from app.models.invoice import Invoice
from app.models.transaction import Transaction
from app.schemas import InvoiceValidationRequest, ComplianceResult
from app.auth.dependencies import get_current_user
from app.services.zatca import zatca_validator
from app.services.einvoice_generator import einvoice_generator
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/compliance", tags=["Compliance"])


@router.post(
    "/validate",
    response_model=ComplianceResult,
    summary="التحقق من امتثال فاتورة",
)
async def validate_invoice(
    data: InvoiceValidationRequest,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Validate an invoice against ZATCA Phase 2 requirements."""
    result = zatca_validator.validate_invoice(data.model_dump())

    # Save invoice with compliance results
    invoice = Invoice(
        business_id=current_user.id,
        seller_name=data.seller_name or "",
        seller_vat=data.seller_vat,
        buyer_name=data.buyer_name,
        date=datetime.now(timezone.utc),
        total=data.total or 0,
        vat_amount=data.vat_amount,
        qr_code=data.qr_code,
        is_compliant=result["valid"],
        compliance_score=result["compliance_score"],
        validation_errors="; ".join(result["errors"]) if result["errors"] else None,
    )
    db.add(invoice)
    db.commit()

    return ComplianceResult(
        valid=result["valid"],
        errors=result["errors"],
        warnings=result["warnings"],
        compliance_score=result["compliance_score"],
    )


# ── Request schema ────────────────────────────────────────────────────────────

class GenerateInvoiceRequest(BaseModel):
    transaction_id: int
    vendor_name: Optional[str] = None


# ── E-Invoice generation ──────────────────────────────────────────────────────

@router.post(
    "/generate-invoice",
    summary="إنشاء فاتورة إلكترونية — ZATCA Phase 2",
)
async def generate_invoice(
    data: GenerateInvoiceRequest,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate a ZATCA Phase 2 e-invoice for a specific transaction.

    Retrieves the transaction from the database, generates an XML invoice
    with a TLV-encoded QR code, persists the result, and returns a preview.
    """
    # Fetch the transaction — must belong to the current business
    transaction = (
        db.query(Transaction)
        .filter(
            Transaction.id == data.transaction_id,
            Transaction.business_id == current_user.id,
        )
        .first()
    )

    if not transaction:
        raise HTTPException(
            status_code=404,
            detail=f"Transaction {data.transaction_id} not found for this business",
        )

    # Build transaction data dict for the generator
    transaction_data = {
        "amount": transaction.amount,
        "vendor": data.vendor_name or transaction.vendor or "غير محدد",
        "date": transaction.date,
        "description": transaction.description or "",
        "category": transaction.category or "",
    }

    vat_number = getattr(current_user, "vat_number", None) or "300000000000003"

    # Generate the e-invoice
    invoice_result = einvoice_generator.generate_invoice(
        transaction_id=transaction.id,
        business_name=current_user.name,
        vat_number=vat_number,
        transaction_data=transaction_data,
    )

    # Persist the generated invoice
    invoice = Invoice(
        business_id=current_user.id,
        seller_name=current_user.name,
        seller_vat=vat_number,
        buyer_name=transaction_data["vendor"],
        date=datetime.now(timezone.utc),
        total=invoice_result["total_amount"],
        vat_amount=invoice_result["vat_amount"],
        invoice_number=invoice_result["invoice_number"],
        xml_content=invoice_result["xml_content"],
        qr_data=invoice_result["qr_data"],
        qr_code=invoice_result["qr_data"],
        is_compliant=True,
        compliance_score=100.0,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    return {
        "invoice_number": invoice_result["invoice_number"],
        "qr_data": invoice_result["qr_data"],
        "xml_preview": invoice_result["xml_content"][:500],
        "message": f"تم إنشاء الفاتورة الإلكترونية {invoice_result['invoice_number']} بنجاح",
    }


# ── Invoice list ──────────────────────────────────────────────────────────────

@router.post("/vat-return")
async def generate_vat_return(
    data: dict,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.vat_calculator import vat_calculator
    from fastapi import HTTPException
    quarter = int(data.get("quarter", 1))
    year = int(data.get("year", 2025))
    if quarter not in (1, 2, 3, 4):
        raise HTTPException(status_code=400, detail="Quarter must be 1-4")
    return vat_calculator.calculate(current_user.id, db, quarter, year)


@router.get(
    "/invoices",
    summary="قائمة الفواتير الإلكترونية",
)
async def list_invoices(
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return all generated e-invoices for the authenticated business.
    """
    invoices = (
        db.query(Invoice)
        .filter(Invoice.business_id == current_user.id)
        .order_by(Invoice.created_at.desc())
        .all()
    )

    return [
        {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "total_amount": inv.total,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
            "compliance_status": "compliant" if inv.is_compliant else "non_compliant",
        }
        for inv in invoices
    ]
