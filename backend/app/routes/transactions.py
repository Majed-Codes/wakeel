"""
Transaction Routes — CRUD + voice-to-transaction pipeline.

Bachmann: "The voice endpoint is the crown jewel. Audio in, structured data out.
Every other fintech app requires typing. We require talking."
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import Business
from app.models.transaction import Transaction, TransactionSource
from app.schemas import TransactionCreate, TransactionResponse, VoiceTransactionResponse
from app.auth.dependencies import get_current_user
from app.services.transcription import transcription_service
from app.services.extraction import entity_extractor
from app.services.rag import financial_rag
from app.services.receipt_ocr import receipt_ocr_service
from app.services.ml_categorizer import ml_categorizer

router = APIRouter(prefix="/api/v1/transactions", tags=["Transactions"])


@router.get(
    "/",
    response_model=List[TransactionResponse],
    summary="جميع المعاملات",
)
async def list_transactions(
    skip: int = 0,
    limit: int = 50,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all transactions for the current business."""
    transactions = (
        db.query(Transaction)
        .filter(Transaction.business_id == current_user.id)
        .order_by(Transaction.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return transactions


@router.post(
    "/",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إضافة معاملة يدوية",
)
async def create_transaction(
    data: TransactionCreate,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a transaction manually."""
    transaction = Transaction(
        business_id=current_user.id,
        amount=data.amount,
        category=data.category,
        description=data.description,
        vendor=data.vendor,
        date=data.date,
        source=TransactionSource.MANUAL,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    # Auto-index into ChromaDB for RAG
    financial_rag.index_single_transaction(transaction, current_user.id)

    return transaction


@router.post(
    "/voice",
    response_model=VoiceTransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="تسجيل معاملة صوتية",
    description="ارفق رسالة صوتية وسيتم تحويلها لمعاملة مالية.",
)
async def create_voice_transaction(
    audio: UploadFile = File(...),
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Main voice pipeline: Audio → Whisper → GPT-4 → Transaction

    Supports .ogg, .mp3, .wav, .m4a (max 25MB).
    """
    # Validate file type
    allowed = ["audio/ogg", "audio/mpeg", "audio/wav", "audio/mp4", "audio/x-m4a"]
    if audio.content_type and audio.content_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"نوع ملف غير مدعوم: {audio.content_type}",
        )

    # Read audio
    audio_bytes = await audio.read()
    if len(audio_bytes) > 25 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="حجم الملف كبير جداً. الحد الأقصى: 25 ميجابايت",
        )

    # Step 1: Transcribe
    try:
        transcription = await transcription_service.transcribe_audio(
            audio_bytes, filename=audio.filename or "audio.ogg"
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="خدمة تحويل الصوت غير متاحة حالياً",
        )

    # Step 2: Extract entities
    extracted = await entity_extractor.extract_transaction(transcription)
    if not extracted:
        return VoiceTransactionResponse(
            status="error",
            message="لم نتمكن من استخراج بيانات المعاملة من الرسالة الصوتية",
        )

    confidence = extracted.get("confidence", 0)

    # Step 3: Create transaction
    transaction = Transaction(
        business_id=current_user.id,
        amount=extracted.get("amount", 0),
        category=extracted.get("category"),
        description=extracted.get("description"),
        vendor=extracted.get("vendor"),
        source=TransactionSource.VOICE,
        confidence=confidence,
        raw_transcription=transcription,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    # Auto-index into ChromaDB for RAG
    financial_rag.index_single_transaction(transaction, current_user.id)

    # Determine status based on confidence
    if confidence >= 0.8:
        return VoiceTransactionResponse(
            status="success",
            message="تم تسجيل المعاملة بنجاح",
            transaction=TransactionResponse.model_validate(transaction),
        )
    else:
        return VoiceTransactionResponse(
            status="needs_confirmation",
            message="يرجى مراجعة البيانات المستخرجة والتأكيد",
            transaction=TransactionResponse.model_validate(transaction),
            extracted_data=extracted,
        )


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="تفاصيل معاملة",
)
async def get_transaction(
    transaction_id: int,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single transaction by ID."""
    transaction = (
        db.query(Transaction)
        .filter(
            Transaction.id == transaction_id,
            Transaction.business_id == current_user.id,
        )
        .first()
    )
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المعاملة غير موجودة",
        )
    return transaction


@router.post(
    "/receipt",
    response_model=VoiceTransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="تسجيل معاملة من صورة إيصال",
)
async def create_receipt_transaction(
    file: UploadFile = File(...),
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Receipt OCR pipeline: Image → Claude Vision → Transaction"""
    from datetime import timezone, datetime as dt

    allowed_ext = {".jpg", ".jpeg", ".png", ".heic", ".webp"}
    ext = Path(file.filename or "").suffix.lower()
    if ext not in allowed_ext:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="نوع الملف غير مدعوم. الأنواع المدعومة: JPG, PNG, HEIC, WebP",
        )

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="حجم الملف كبير جداً. الحد الأقصى 10 ميجابايت",
        )

    extracted = await receipt_ocr_service.extract_from_image(
        contents, file.filename or "receipt.jpg"
    )
    if not extracted or not extracted.get("amount"):
        return VoiceTransactionResponse(
            status="error",
            message="فشل في استخراج البيانات من الإيصال. تأكد من وضوح الصورة.",
        )

    txn_date = None
    if extracted.get("date"):
        try:
            txn_date = dt.strptime(extracted["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            pass

    transaction = Transaction(
        business_id=current_user.id,
        amount=extracted.get("amount", 0),
        category=extracted.get("category", "تشغيلية"),
        description=extracted.get("description", ""),
        vendor=extracted.get("vendor", ""),
        date=txn_date,
        source=TransactionSource.RECEIPT,
        confidence=extracted.get("confidence", 0.85),
        raw_transcription=f"استخراج من إيصال: {file.filename}",
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    financial_rag.index_single_transaction(transaction, current_user.id)

    confidence = extracted.get("confidence", 0.85)
    status_str = "success" if confidence >= 0.7 else "needs_confirmation"
    msg = "تم استخراج المعاملة من الإيصال بنجاح" if status_str == "success" else "يرجى مراجعة البيانات المستخرجة"
    return VoiceTransactionResponse(
        status=status_str,
        message=msg,
        transaction=TransactionResponse.model_validate(transaction),
        extracted_data=extracted,
    )


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف معاملة",
)
async def delete_transaction(
    transaction_id: int,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a transaction."""
    transaction = (
        db.query(Transaction)
        .filter(
            Transaction.id == transaction_id,
            Transaction.business_id == current_user.id,
        )
        .first()
    )
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المعاملة غير موجودة",
        )
    db.delete(transaction)
    db.commit()


# ── ML Categorizer Endpoints ─────────────────────────────────────────────────

@router.post(
    "/ml/train",
    summary="تدريب نموذج التصنيف",
    description="يدرّب نموذج ML على سجل المعاملات الخاص بالمنشأة.",
)
async def train_ml_model(
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Train or retrain the ML categorizer for the current business."""
    result = ml_categorizer.train(business_id=current_user.id, db=db)
    return result


@router.post(
    "/ml/predict",
    summary="تنبؤ بالفئة",
    description="يتنبأ بفئة المعاملة بناءً على النص.",
)
async def predict_category(
    text: str,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Predict category for a transaction description."""
    # Auto-retrain if needed
    if ml_categorizer.should_retrain(business_id=current_user.id, db=db):
        ml_categorizer.train(business_id=current_user.id, db=db)

    result = ml_categorizer.predict(text=text, business_id=current_user.id, db=db)
    return result


@router.get(
    "/ml/info",
    summary="معلومات نموذج ML",
    description="يُعيد معلومات عن نموذج ML المدرَّب للمنشأة.",
)
async def get_ml_info(
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return ML model information for the current business."""
    return ml_categorizer.get_model_info(business_id=current_user.id)
