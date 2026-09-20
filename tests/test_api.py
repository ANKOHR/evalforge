from __future__ import annotations

from fastapi.testclient import TestClient

from evalforge import main


def test_health_endpoint():
    with TestClient(main.app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_demo_summary_requires_report(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "REPORT_PATH", tmp_path / "missing.json")
    with TestClient(main.app) as client:
        response = client.get("/api/demo/summary")
    assert response.status_code == 404


def test_demo_run_requires_report(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "REPORT_PATH", tmp_path / "missing.json")
    with TestClient(main.app) as client:
        response = client.get("/api/demo/run/baseline")
    assert response.status_code == 404


def test_demo_comparison_requires_report(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "REPORT_PATH", tmp_path / "missing.json")
    with TestClient(main.app) as client:
        response = client.get("/api/demo/comparison")
    assert response.status_code == 404
