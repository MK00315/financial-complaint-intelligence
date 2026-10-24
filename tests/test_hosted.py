"""Deployment-specific behavior, using the real saved model and portable counts."""
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api import app


@pytest.mark.parametrize("hosted,mode,label", [("1", "hosted", "HOSTED MODEL"), ("", "local", "LOCAL PROCESSING")])
def test_processing_disclosure_matches_execution_mode(monkeypatch, hosted, mode, label):
    monkeypatch.setenv("COMPLAINT_HOSTED", hosted)
    with TestClient(app) as client:
        serving = client.get("/api/model").json()["serving"]
        assert serving["mode"] == mode
        assert serving["label"] == label
        assert "does not save" in serving["text_note"] or "not saved" in serving["text_note"]
        if hosted:
            assert "sent to the hosted model" in serving["text_note"]


def test_hosted_service_uses_real_counts_and_inference(monkeypatch):
    monkeypatch.setenv("COMPLAINT_HOSTED", "1")
    monkeypatch.setenv("COMPLAINT_PROFILE", "uncapped")
    with TestClient(app) as client:
        assert client.get("/api/health").json()["profile"] == "uncapped"
        summary = client.get("/api/summary").json()
        assert summary["source"]["database_rows"] == 811019
        response = client.post("/api/classify", json={"text": "My credit report lists an account that does not belong to me. I disputed the incorrect information with the credit bureau, but the account still appears on my report and is affecting my credit history."})
        assert response.status_code == 200
        assert response.json()["category"] == "Credit reporting or other personal consumer reports"
        assert response.json()["score"] == pytest.approx(0.893, abs=0.01)
        assert response.headers["Cache-Control"] == "no-store"
