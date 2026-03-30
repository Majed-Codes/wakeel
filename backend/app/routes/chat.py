"""
Chat Routes — AI financial assistant conversations.

Supports conversation history for context-aware responses.
Auto-indexes transactions on first chat interaction.
"""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import Business
from app.models.chat import ChatHistory, ChatRole
from app.models.transaction import Transaction
from app.schemas import ChatMessageRequest, ChatMessageResponse
from app.auth.dependencies import get_current_user
from app.services.rag import financial_rag

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])


def _ensure_transactions_indexed(db: Session, business_id: int):
    """Ensure the user's transactions are indexed in the vector DB."""
    transactions = (
        db.query(Transaction)
        .filter(Transaction.business_id == business_id)
        .all()
    )
    if transactions:
        financial_rag.index_transactions(transactions, business_id)


@router.post(
    "/",
    response_model=ChatMessageResponse,
    summary="إرسال رسالة للمساعد الذكي",
)
async def send_message(
    data: ChatMessageRequest,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a message to the AI assistant and get a response."""

    # Ensure transactions are indexed for RAG
    _ensure_transactions_indexed(db, current_user.id)

    # Get recent conversation history for context
    recent_messages = (
        db.query(ChatHistory)
        .filter(ChatHistory.business_id == current_user.id)
        .order_by(ChatHistory.created_at.desc())
        .limit(10)
        .all()
    )
    chat_history = [
        {"role": msg.role.value if hasattr(msg.role, 'value') else msg.role, "content": msg.content}
        for msg in reversed(recent_messages)
    ]

    # Save user message
    user_msg = ChatHistory(
        business_id=current_user.id,
        role=ChatRole.USER,
        content=data.message,
    )
    db.add(user_msg)
    db.commit()

    # Get AI response using RAG with conversation history
    ai_response = await financial_rag.answer_query(
        query=data.message,
        business_id=current_user.id,
        chat_history=chat_history,
    )

    # Save assistant response
    assistant_msg = ChatHistory(
        business_id=current_user.id,
        role=ChatRole.ASSISTANT,
        content=ai_response,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return assistant_msg


@router.get(
    "/history",
    response_model=List[ChatMessageResponse],
    summary="سجل المحادثات",
)
async def get_chat_history(
    limit: int = 50,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get chat history for the current business."""
    messages = (
        db.query(ChatHistory)
        .filter(ChatHistory.business_id == current_user.id)
        .order_by(ChatHistory.created_at.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(messages))
