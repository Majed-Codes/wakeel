"""
Auth Dependencies — extracting and validating the current user from JWT.

Bachmann: "Every protected endpoint calls get_current_user.
If you forget it, the endpoint is public. Don't forget it."
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.utils import decode_access_token
from app.models.user import Business

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Business:
    """
    FastAPI dependency: extracts JWT from Authorization header,
    validates it, and returns the authenticated Business entity.
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="رمز التوثيق غير صالح أو منتهي الصلاحية",  # Invalid or expired token
            headers={"WWW-Authenticate": "Bearer"},
        )

    business_id: str = payload.get("sub")
    if business_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="رمز التوثيق لا يحتوي على معرف المستخدم",
        )

    business = db.query(Business).filter(Business.id == int(business_id)).first()
    if business is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المنشأة غير موجودة",  # Business not found
        )

    if not business.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="الحساب معطل",  # Account disabled
        )

    return business
