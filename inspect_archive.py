"""Profile an official CFPB archive without extracting raw complaint text."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile


def profile_archive(archive_path: Path) -> dict:
    csv.field_size_limit(20_000_000)
    summary = {
        "source": "CFPB official narratives archive",
        "source_page": "https://www.consumerfinance.gov/foia-requests/foia-electronic-reading-room/cfpb-consumer-complaint-database-narratives-archive/",
        "download_url": "https://files.consumerfinance.gov/f/documents/CCDB_Export_9_January_2025_through_February_2025.zip",
        "archive": archive_path.name,
        "archive_bytes": archive_path.stat().st_size,
        "sha256": hashlib.file_digest(archive_path.open("rb"), "sha256").hexdigest(),
        "total_rows": 0,
        "rows_with_narrative": 0,
        "narrative_product_counts": Counter(),
        "all_product_counts": Counter(),
        "monthly_counts": Counter(),
        "narrative_monthly_counts": Counter(),
        "narrative_length_characters": {"minimum": None, "maximum": 0, "sum": 0},
        "date_received_min": None,
        "date_received_max": None,
        "csv_members": [],
    }
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            if not member.filename.lower().endswith(".csv"):
                continue
            summary["csv_members"].append({"name": member.filename, "uncompressed_bytes": member.file_size})
            with archive.open(member) as raw:
                reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
                summary["columns"] = reader.fieldnames
                if not reader.fieldnames or "Consumer complaint narrative" not in reader.fieldnames:
                    raise ValueError(f"Expected complaint narrative column; found {reader.fieldnames!r}")
                for row in reader:
                    summary["total_rows"] += 1
                    product = row.get("Product", "").strip()
                    received = row.get("Date received", "").strip()
                    summary["all_product_counts"][product] += 1
                    if received:
                        summary["monthly_counts"][received[:7]] += 1
                        summary["date_received_min"] = min(received, summary["date_received_min"] or received)
                        summary["date_received_max"] = max(received, summary["date_received_max"] or received)
                    narrative = row.get("Consumer complaint narrative", "").strip()
                    if narrative:
                        summary["rows_with_narrative"] += 1
                        summary["narrative_product_counts"][product] += 1
                        summary["narrative_monthly_counts"][received[:7]] += 1
                        lengths = summary["narrative_length_characters"]
                        lengths["minimum"] = min(len(narrative), lengths["minimum"] or len(narrative))
                        lengths["maximum"] = max(len(narrative), lengths["maximum"])
                        lengths["sum"] += len(narrative)
    n = summary["rows_with_narrative"]
    summary["narrative_coverage_pct"] = round(100 * n / summary["total_rows"], 2) if summary["total_rows"] else 0
    summary["narrative_length_characters"]["mean"] = round(summary["narrative_length_characters"]["sum"] / n, 1) if n else 0
    summary["status"] = "Source profiling only. No model trained or dashboard built yet."
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=Path("data/raw/cfpb_2025_01_02.zip"))
    parser.add_argument("--output", type=Path, default=Path("reports/source_profile.json"))
    args = parser.parse_args()
    result = profile_archive(args.archive)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "narrative_length_characters"}, indent=2))
