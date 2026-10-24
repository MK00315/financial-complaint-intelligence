"""Functional checks for filtered reporting, exports and fixed model evaluation."""
import csv
import io
from pathlib import Path
import sqlite3
import sys

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as session:
        yield session


@pytest.mark.parametrize("product,start,end", [
    ("Checking or savings account", "2025-01-01", "2025-01-31"),
    ("Credit card", "2025-02-10", "2025-02-16"),
    ("Debt collection", "2025-01-01", "2025-02-28"),
])
def test_filtered_counts_match_independent_source_sql(client, product, start, end):
    database = ROOT / "data/complaints.sqlite"
    if not database.exists():
        pytest.skip("Raw database is intentionally excluded from the portable app.")
    response = client.get("/api/analytics", params=dict(product=product, start=start, end=end))
    assert response.status_code == 200
    result = response.json()
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        expected = connection.execute("""SELECT COUNT(*), SUM(has_narrative),
            COUNT(DISTINCT issue) FROM complaints
            WHERE product=? AND date_received BETWEEN ? AND ?""", (product, start, end)).fetchone()
    assert (result["totals"]["complaints"], result["totals"]["narratives"], result["totals"]["issues"]) == expected
    assert sum(row["complaints"] for row in result["daily"]) == expected[0]
    assert sum(row["complaints"] for row in result["issues"]) == expected[0]
    assert result["daily"][0]["date"] == start and result["daily"][-1]["date"] == end


def test_month_filter_uses_real_calendar_days(client):
    result = client.get("/api/analytics", params={"product": "Credit card", "start": "2025-01-01", "end": "2025-01-31"}).json()
    assert result["totals"]["complaints"] == 9073
    assert len(result["daily"]) == 31
    assert result["totals"]["products"] == 1


@pytest.mark.parametrize("query", [
    {"start": "2024-12-31"}, {"end": "2025-03-01"},
    {"start": "2025-02-20", "end": "2025-02-10"},
    {"start": "not-a-date"}, {"product": "invented product"},
    {"product": "Credit card", "issue": "invented issue"},
])
def test_invalid_filters_are_rejected_with_a_useful_error(client, query):
    response = client.get("/api/analytics", params=query)
    assert response.status_code == 422
    assert response.json()["detail"]


def test_issue_detail_preserves_reported_counts(client):
    product = "Credit reporting or other personal consumer reports"
    issue = "Incorrect information on your report"
    result = client.get("/api/analytics", params={"product": product, "issue": issue}).json()
    assert result["totals"]["complaints"] == 359132
    assert sum(row["complaints"] for row in result["daily"]) == 359132
    assert len(result["issues"]) == 1
    assert result["totals"]["narratives"] == 83111


def test_csv_respects_product_date_search_and_original_denominator(client):
    query = {"kind": "issues", "product": "Credit card", "start": "2025-01-01", "end": "2025-01-31", "q": "purchase"}
    response = client.get("/api/export", params=query)
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(response.text.lstrip("\ufeff"))))
    assert rows
    for row in rows:
        assert row["product"] == "Credit card" and "purchase" in row["issue"].lower()
        assert row["period_start"] == "2025-01-01" and row["period_end"] == "2025-01-31"
        assert float(row["share_pct"]) == pytest.approx(int(row["complaints"]) / 9073 * 100)


def test_analytics_filter_does_not_change_model_evaluation(client):
    before = client.get("/api/model").json()
    client.get("/api/analytics", params={"product": "Mortgage", "start": "2025-02-01"}).raise_for_status()
    after = client.get("/api/model").json()
    assert before == after
    assert sum(map(sum, after["model"]["confusion_matrix"])) == after["split"]["splits"]["test"]["rows"] == 15390


def test_real_classification_returns_verified_profile_and_review_route(client):
    response = client.post("/api/classify", json={"text": "My credit report lists an account that does not belong to me. I disputed the incorrect information with the credit bureau, but the account still appears on my report and is affecting my credit history."})
    assert response.status_code == 200
    result = response.json()
    assert result["profile"] == "uncapped"
    assert result["category"] == "Credit reporting or other personal consumer reports"
    assert result["human_review"] is (result["score"] < 0.55)


def test_dashboard_assets_are_served_from_the_local_application(client):
    response = client.get("/")
    assert response.status_code == 200 and "text/html" in response.headers["content-type"]
    for path in ("app.js", "views.js", "views-classify.js", "views-model.js", "charts.js", "utils.js", "icons.js", "app.css", "fonts/inter.woff2", "fonts/space-grotesk.woff2", "fonts/jetbrains-mono.woff2"):
        asset = client.get("/assets/" + path)
        assert asset.status_code == 200, path
        assert len(asset.content) > 100
