"""Vendor/Supplier management routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import Business
from app.models.vendor import Vendor
from app.models.transaction import Transaction
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/vendors", tags=["Vendors"])

def vendor_to_dict(v: Vendor, db: Session) -> dict:
    from sqlalchemy import func
    total_spent = db.query(func.sum(Transaction.amount)).filter(
        Transaction.business_id == v.business_id,
        Transaction.vendor == v.name,
    ).scalar() or 0.0
    tx_count = db.query(Transaction).filter(
        Transaction.business_id == v.business_id,
        Transaction.vendor == v.name,
    ).count()
    return {
        "id": v.id,
        "name": v.name,
        "category": v.category,
        "contact_phone": v.contact_phone,
        "contact_email": v.contact_email,
        "payment_terms_days": v.payment_terms_days,
        "notes": v.notes,
        "total_spent": round(total_spent, 2),
        "transaction_count": tx_count,
        "created_at": v.created_at.isoformat(),
    }

@router.get("/")
async def list_vendors(
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vendors = db.query(Vendor).filter(Vendor.business_id == current_user.id).all()
    return [vendor_to_dict(v, db) for v in vendors]

@router.post("/", status_code=201)
async def create_vendor(
    data: dict,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vendor = Vendor(
        business_id=current_user.id,
        name=data["name"],
        category=data.get("category"),
        contact_phone=data.get("contact_phone"),
        contact_email=data.get("contact_email"),
        payment_terms_days=int(data.get("payment_terms_days", 30)),
        notes=data.get("notes"),
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor_to_dict(vendor, db)

@router.put("/{vendor_id}")
async def update_vendor(
    vendor_id: int,
    data: dict,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id, Vendor.business_id == current_user.id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    for field in ["name", "category", "contact_phone", "contact_email", "payment_terms_days", "notes"]:
        if field in data:
            setattr(vendor, field, data[field])
    db.commit()
    return vendor_to_dict(vendor, db)

@router.delete("/{vendor_id}", status_code=204)
async def delete_vendor(
    vendor_id: int,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id, Vendor.business_id == current_user.id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    db.delete(vendor)
    db.commit()

@router.get("/{vendor_id}/transactions")
async def vendor_transactions(
    vendor_id: int,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id, Vendor.business_id == current_user.id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    txs = db.query(Transaction).filter(
        Transaction.business_id == current_user.id,
        Transaction.vendor == vendor.name,
    ).order_by(Transaction.date.desc()).limit(50).all()
    return [{"id": t.id, "amount": t.amount, "description": t.description,
             "date": t.date.isoformat() if t.date else None,
             "category": t.category, "transaction_type": t.transaction_type} for t in txs]
