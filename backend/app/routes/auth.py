"""
Authentication Routes — register, login, get profile.

Bachmann: "Auth is the first thing I build. Without it,
every other endpoint is a security hole."
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import Business
from app.schemas import RegisterRequest, LoginRequest, Token, BusinessResponse
from app.auth.utils import hash_password, verify_password, create_access_token
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="تسجيل منشأة جديدة",
)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new business (user). Returns a JWT token."""
    existing = db.query(Business).filter(Business.phone == request.phone).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="رقم الجوال مسجل مسبقاً",
        )

    business = Business(
        name=request.name,
        phone=request.phone,
        email=request.email,
        hashed_password=hash_password(request.password),
    )
    db.add(business)
    db.commit()
    db.refresh(business)

    token = create_access_token(data={"sub": str(business.id)})
    return Token(access_token=token)


@router.post(
    "/login",
    response_model=Token,
    summary="تسجيل الدخول",
)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login with phone and password. Returns a JWT token."""
    business = db.query(Business).filter(Business.phone == request.phone).first()
    if not business or not verify_password(request.password, business.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="رقم الجوال أو كلمة المرور غير صحيحة",
        )

    token = create_access_token(data={"sub": str(business.id)})
    return Token(access_token=token)


@router.get(
    "/me",
    response_model=BusinessResponse,
    summary="الملف الشخصي",
)
async def get_profile(current_user: Business = Depends(get_current_user)):
    """Get the current user's business profile."""
    return current_user
