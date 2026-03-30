"""
Auth API Tests.
"""

import pytest


class TestAuthEndpoints:
    """Test registration, login, and profile endpoints."""

    def test_register_new_business(self, client):
        payload = {
            "name": "مقهى جديد",
            "phone": "0551234567",
            "password": "securepass123",
            "email": "new@test.com",
        }
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_phone(self, client, test_business):
        payload = {
            "name": "مقهى آخر",
            "phone": test_business.phone,
            "password": "password123",
        }
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 409

    def test_register_short_password(self, client):
        payload = {
            "name": "مقهى",
            "phone": "0559876543",
            "password": "123",
        }
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422

    def test_login_success(self, client, test_business):
        payload = {
            "phone": "0509999999",
            "password": "testpass123",
        }
        response = client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_login_wrong_password(self, client, test_business):
        payload = {
            "phone": "0509999999",
            "password": "wrongpassword",
        }
        response = client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        payload = {
            "phone": "0500000000",
            "password": "password",
        }
        response = client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 401

    def test_get_profile(self, client, auth_headers, test_business):
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "مقهى تجريبي"
        assert data["phone"] == "0509999999"

    def test_get_profile_invalid_token(self, client):
        headers = {"Authorization": "Bearer invalidtoken123"}
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401

    def test_get_profile_no_token(self, client):
        response = client.get("/api/v1/auth/me")
        assert response.status_code in (401, 403)
