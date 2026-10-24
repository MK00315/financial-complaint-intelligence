"""Portable, aggregate-only data for the local analyst dashboard."""
from collections import defaultdict
from datetime import date, timedelta
import csv
import io
import json
from pathlib import Path
import sqlite3

from complaint_project import SOURCE_SHA256

FIRST = "2025-01-01"
LAST = "2025-02-28"
FIELDS = ("date", "product", "issue", "complaints", "narratives", "timely", "timeliness_known")


def export_dashboard_analytics(root: Path) -> dict:
    """Derive date/product/issue counts; never export complaint text or IDs."""
    source = json.loads((root / "reports/data_manifest.json").read_text(encoding="utf-8"))
    if source["source_sha256"] != SOURCE_SHA256:
        raise ValueError("Unexpected source checksum in the data manifest.")
    database = root / "data/complaints.sqlite"
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        rows = [dict(zip(FIELDS, row)) for row in connection.execute("""
            SELECT date_received, product, issue, COUNT(*), SUM(has_narrative),
                   SUM(CASE WHEN timely_response='Yes' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN timely_response IN ('Yes','No') THEN 1 ELSE 0 END)
            FROM complaints GROUP BY 1,2,3 ORDER BY 1,2,3
        """)]
    result = {"schema_version": 1, "source_sha256": source["source_sha256"],
              "date_min": FIRST, "date_max": LAST, "rows": rows}
    validate_dashboard_data(result, source)
    path = root / "reports/analytics/dashboard_analytics.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return result


def validate_dashboard_data(data: dict, source: dict) -> None:
    if data.get("schema_version") != 1 or data.get("source_sha256") != SOURCE_SHA256:
        raise ValueError("The dashboard aggregate source or schema does not match this project.")
    rows = data["rows"]
    if sum(r["complaints"] for r in rows) != source["database_rows"]:
        raise ValueError("Dashboard record totals do not match the verified source.")
    if sum(r["narratives"] for r in rows) != source["with_narrative"]:
        raise ValueError("Dashboard narrative totals do not match the verified source.")
    identities = {(r["date"], r["product"], r["issue"]) for r in rows}
    if len(identities) != len(rows):
        raise ValueError("Duplicate aggregate keys.")
    for row in rows:
        if not FIRST <= row["date"] <= LAST:
            raise ValueError("Unexpected dashboard date.")
        if not 0 <= row["timely"] <= row["timeliness_known"] <= row["complaints"]:
            raise ValueError("Invalid response-flag denominator.")
        if not 0 <= row["narratives"] <= row["complaints"]:
            raise ValueError("Invalid narrative denominator.")


def load_dashboard_data(root: Path, source: dict) -> dict:
    path = root / "reports/analytics/dashboard_analytics.json"
    if not path.exists():
        if (root / "data/complaints.sqlite").exists():
            data = export_dashboard_analytics(root)
        else:
            raise RuntimeError("Dashboard aggregates are missing. Run prepare_dashboard.py; model training is not required.")
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
    validate_dashboard_data(data, source)
    return data


def validate_filters(data: dict, product: str, start: str, end: str, issue: str = "") -> None:
    try:
        date.fromisoformat(start)
        date.fromisoformat(end)
    except ValueError as exc:
        raise ValueError("Choose valid dates in January or February 2025.") from exc
    if not FIRST <= start <= end <= LAST:
        raise ValueError("Choose an ordered date range between January 1 and February 28, 2025.")
    if product and product not in {r["product"] for r in data["rows"]}:
        raise ValueError("Choose a product in this archive.")
    if issue and not any(r["issue"] == issue and (not product or r["product"] == product) for r in data["rows"]):
        raise ValueError("Choose an issue in this product category.")


def aggregate(data: dict, product: str = "", start: str = FIRST, end: str = LAST, issue: str = "") -> dict:
    validate_filters(data, product, start, end, issue)
    selected = [r for r in data["rows"] if start <= r["date"] <= end
                and (not product or r["product"] == product) and (not issue or r["issue"] == issue)]
    dates, products, issues = defaultdict(lambda: defaultdict(int)), defaultdict(lambda: defaultdict(int)), defaultdict(lambda: defaultdict(int))
    totals = {k: 0 for k in FIELDS[3:]}
    for row in selected:
        for field in totals:
            totals[field] += row[field]
            dates[row["date"]][field] += row[field]
            products[row["product"]][field] += row[field]
            issues[(row["product"], row["issue"])][field] += row[field]
    total = totals["complaints"]

    def measures(values):
        return {**values, "share_pct": 100 * values["complaints"] / total if total else 0,
                "narrative_coverage_pct": 100 * values["narratives"] / values["complaints"] if values["complaints"] else 0,
                "timely_pct": 100 * values["timely"] / values["timeliness_known"] if values["timeliness_known"] else None}

    daily = []
    current = date.fromisoformat(start)
    while current <= date.fromisoformat(end):
        key = current.isoformat()
        daily.append({"date": key, **{field: dates[key][field] for field in totals}})
        current += timedelta(days=1)
    return {"scope": {"product": product, "start": start, "end": end, "issue": issue},
            "totals": {**measures(totals), "products": len(products), "issues": len(issues)},
            "daily": daily,
            "products": sorted(({"product": key, **measures(values)} for key, values in products.items()), key=lambda r: (-r["complaints"], r["product"])),
            "issues": sorted(({"product": key[0], "issue": key[1], **measures(values)} for key, values in issues.items()), key=lambda r: (-r["complaints"], r["product"], r["issue"]))}


def matching_issues(rows: list, query: str = "", sort: str = "count_desc") -> list:
    query = query.casefold().strip()
    result = [row for row in rows if query in (row["issue"] + " " + row["product"]).casefold()]
    if sort == "issue_asc":
        return sorted(result, key=lambda r: (r["issue"].casefold(), r["product"]))
    if sort == "count_asc":
        return sorted(result, key=lambda r: (r["complaints"], r["issue"]))
    return sorted(result, key=lambda r: (-r["complaints"], r["issue"]))


def csv_export(result: dict, kind: str, query: str = "", sort: str = "count_desc") -> str:
    columns = {
        "issues": ["product", "issue", "complaints", "share_pct", "narratives", "narrative_coverage_pct", "timely", "timeliness_known", "timely_pct"],
        "products": ["product", "complaints", "share_pct", "narratives", "narrative_coverage_pct"],
        "daily": ["date", "complaints", "narratives", "timely", "timeliness_known"],
    }
    if kind not in columns:
        raise ValueError("Choose issues, products or daily for the export.")
    rows = matching_issues(result[kind], query, sort) if kind == "issues" else result[kind]
    stream = io.StringIO(newline="")
    scope_fields = ["period_start", "period_end", "selected_product", "selected_issue"]
    writer = csv.DictWriter(stream, fieldnames=scope_fields + columns[kind])
    writer.writeheader()
    for row in rows:
        values = {key: row[key] for key in columns[kind]}
        values.update(period_start=result["scope"]["start"], period_end=result["scope"]["end"],
                      selected_product=result["scope"]["product"] or "All products", selected_issue=result["scope"]["issue"])
        for key, value in values.items():
            if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
                values[key] = "'" + value
        writer.writerow(values)
    return stream.getvalue()
