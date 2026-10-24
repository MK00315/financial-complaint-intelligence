"""Rebuild portable dashboard counts from the official archive, without training."""
from pathlib import Path
from complaint_project import download_archive, build_database
from dashboard_data import export_dashboard_analytics

if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    archive = download_archive(root)
    build_database(root, archive)
    data = export_dashboard_analytics(root)
    print(f"Dashboard ready: {sum(r['complaints'] for r in data['rows']):,} records in {len(data['rows']):,} aggregate rows. No model was trained.")
