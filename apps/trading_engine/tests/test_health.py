from fastapi.testclient import TestClient

from trading_engine.main import app


def test_health():
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "trading_engine"


def test_kill_switch_toggle():
    with TestClient(app) as client:
        r = client.post("/admin/kill")
        assert r.status_code == 200
        assert r.json()["engaged"] is True

        r = client.get("/admin/status")
        assert r.json()["kill_switch"]["engaged"] is True

        r = client.post("/admin/resume")
        assert r.status_code == 200
        assert r.json()["engaged"] is False
