from fastapi.testclient import TestClient

from ml_service.main import app


def test_health():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_predict_stub():
    client = TestClient(app)
    r = client.post("/inference/predict", json={"symbol": "btcusdt", "horizon_minutes": 60})
    assert r.status_code == 200
    body = r.json()
    assert body["symbol"] == "BTCUSDT"
    assert body["horizon_minutes"] == 60
