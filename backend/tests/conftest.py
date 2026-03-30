"""
Test Fixtures — shared setup for all Wakeel AI tests.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.auth.utils import hash_password, create_access_token
from app.models.user import Business
from app.models.transaction import Transaction, TransactionSource
from app.models.invoice import Invoice
from datetime import datetime, timezone


# In-memory SQLite for tests
TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_database():
    """Create fresh tables for each test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """Provide a test database session."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    """Provide a FastAPI test client with overridden DB dependency."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_business(db) -> Business:
    """Create a test business in the database."""
    business = Business(
        name="مقهى تجريبي",
        phone="0509999999",
        email="test@wakeel.ai",
        hashed_password=hash_password("testpass123"),
        is_active=True,
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


@pytest.fixture
def auth_token(test_business) -> str:
    """Create a valid JWT token for the test business."""
    return create_access_token(data={"sub": str(test_business.id)})


@pytest.fixture
def auth_headers(auth_token) -> dict:
    """Return Authorization headers with Bearer token."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def sample_transactions(db, test_business) -> list:
    """Create sample transactions for testing."""
    now = datetime.now(timezone.utc)
    transactions = [
        Transaction(
            business_id=test_business.id,
            amount=5000,
            category="تشغيلية",
            description="توريد بن وقهوة",
            vendor="المراعي",
            date=now,
            source=TransactionSource.MANUAL,
        ),
        Transaction(
            business_id=test_business.id,
            amount=12000,
            category="تشغيلية",
            description="إيجار المحل",
            vendor="شركة العقارات",
            date=now,
            source=TransactionSource.MANUAL,
        ),
        Transaction(
            business_id=test_business.id,
            amount=45000,
            category="إيرادات",
            description="مبيعات الشهر",
            vendor="عملاء متنوعين",
            date=now,
            source=TransactionSource.MANUAL,
        ),
    ]
    for t in transactions:
        db.add(t)
    db.commit()
    for t in transactions:
        db.refresh(t)
    return transactions
