import os
import sys
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from web.app import app, generate_session_token, COOKIE_NAME
from config import settings


def test_web_app():
    client = TestClient(app)

    # 1. Test unauthenticated redirect to login
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"
    print("  [OK] Unauthenticated redirect to /login")

    # 2. Test Login page loads
    resp = client.get("/login")
    assert resp.status_code == 200
    assert "AI-Moderator" in resp.text
    print("  [OK] Login page renders")

    # 3. Test Successful Login
    token = generate_session_token(settings.ADMIN_PASSWORD)
    client.cookies.set(COOKIE_NAME, token)

    # 4. Test Dashboard page
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Tizim ko'rsatkichlari" in resp.text
    assert "dailyTrendChart" in resp.text
    print("  [OK] Dashboard renders with KPI cards and charts")

    # 5. Test Messages page
    resp = client.get("/messages")
    assert resp.status_code == 200
    assert "Xabarlar jurnali" in resp.text
    print("  [OK] Messages log page renders with data table")

    # 6. Test Reports page
    resp = client.get("/reports")
    assert resp.status_code == 200
    assert "Shikoyatlar" in resp.text
    print("  [OK] Reports queue page renders")

    # 7. Test Tester page
    resp = client.get("/tester")
    assert resp.status_code == 200
    assert "Test Laboratoriyasi" in resp.text
    print("  [OK] Tester page renders")

    # 8. Test /api/test endpoint
    resp = client.post("/api/test", json={"text": "Daromad olish uchun lichkaga yozing"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_violation"] is True
    assert data["violation_type"] == "CTA"
    assert "translated_uz" in data
    assert "translated_ru" in data
    print(f"  [OK] /api/test endpoint works: violation={data['is_violation']}, type={data['violation_type']}")

    # 9. Test Settings page
    resp = client.get("/settings")
    assert resp.status_code == 200
    assert "Tizim sozlamalari" in resp.text
    print("  [OK] Settings page renders")

    print("\n[OK] BARCHA WEB TESTLARI MUVAFFAQIYATLI O'TDI!")


if __name__ == "__main__":
    test_web_app()
