from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "LieSpy API is running", "docs": "/docs"}

def test_scan_page():
    payload = {
        "url": "https://example.com",
        "candidates": ["This pill cures cancer", "Buy now for 50% off"]
    }
    response = client.post("/api/v1/scan/page", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "scan_id" in data
    assert "result" in data
    assert data["result"]["page_risk"] in ["low", "medium", "high"]

def test_scan_text():
    payload = {
        "text": "Only today 90% off",
        "url": "https://example.com"
    }
    response = client.post("/api/v1/scan/text", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert float(data["result"]["claims"][0]["confidence"]) > 0
