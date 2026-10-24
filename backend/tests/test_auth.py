import pytest

from app.utils.security import hash_password, verify_password


def test_password_hashes_remain_bcrypt_compatible():
    hashed = hash_password("TestPassword123!")
    assert hashed.startswith("$2b$")
    assert verify_password("TestPassword123!", hashed)
    assert not verify_password("WrongPassword", hashed)
    assert not verify_password("TestPassword123!", "invalid-hash")


@pytest.mark.asyncio
async def test_register_and_login_with_native_database(override_db):
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/register", json={
            "email": "native@example.com", "password": "TestPassword123!", "full_name": "Native Test",
        })
        assert response.status_code == 201
        login = await client.post("/api/v1/auth/login", json={
            "email": "native@example.com", "password": "TestPassword123!",
        })
        assert login.status_code == 200
        assert login.json()["access_token"]
