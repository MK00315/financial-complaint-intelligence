"""Reproducible CFPB analytics and text classification pipeline (CPU only)."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request
import zipfile

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, balanced_accuracy_score
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import Pipeline

VERSION = "1.1.0"
DATA_VERSION = "1.0.0"  # Cleaning/database schema are unchanged by the new profile.
SOURCE_URL = "https://files.consumerfinance.gov/f/documents/CCDB_Export_9_January_2025_through_February_2025.zip"
SOURCE_PAGE = "https://www.consumerfinance.gov/foia-requests/foia-electronic-reading-room/cfpb-consumer-complaint-database-narratives-archive/"
SOURCE_SHA256 = "11c18bb0973eed8f5e4f66e2979346af0671a3aefcb5a6b9eec73009d53cff64"
SEED = 42
PROFILES = {
    "smoke": {"train_cap_per_class": 250, "eval_cap_per_class": 80, "max_features": 18000},
    "full": {"train_cap_per_class": 15000, "eval_cap_per_class": None, "max_features": 65000},
    "uncapped": {"train_cap_per_class": None, "eval_cap_per_class": None, "max_features": 65000},
}


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def file_sha(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def normalize_text(value: str) -> str:
    """Remove redaction artifacts and variable identifiers, retaining complaint words."""
    value = str(value).lower()
    value = re.sub(r"https?://\S+|www\.\S+|\b[^\s@]+@[^\s@]+\.[^\s@]+\b", " ", value)
    value = re.sub(r"\bx{2,}\b|\d+", " ", value)
    value = re.sub(r"[^a-z\s']", " ", value)
    return " ".join(value.split())


def download_archive(root: Path) -> Path:
    target = root / "data/raw/cfpb_2025_01_02.zip"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and file_sha(target) == SOURCE_SHA256:
        print("Verified cached official archive.", flush=True)
        return target
    temporary = target.with_suffix(".download")
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=90) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
    except Exception as exc:
        # The official CDN can reject Python clients. Curl follows the same public URL.
        curl = shutil.which("curl.exe") or shutil.which("curl")
        if not curl:
            raise RuntimeError("Download failed. Upload the official archive to data/raw/cfpb_2025_01_02.zip and rerun.") from exc
        subprocess.run([curl, "--fail", "--location", "--retry", "2", "--max-time", "300", "--output", str(temporary), SOURCE_URL], check=True)
    if file_sha(temporary) != SOURCE_SHA256:
        temporary.unlink(missing_ok=True)
        raise ValueError("Source checksum changed. Inspect the new official release before using it.")
    temporary.replace(target)
    return target


def build_database(root: Path, archive_path: Path) -> dict:
    """Stream all records into SQLite; do not load the full raw CSV into RAM."""
    db_path = root / "data/complaints.sqlite"
    manifest_path = root / "reports/data_manifest.json"
    if db_path.exists() and manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("data_pipeline_version",existing.get("pipeline_version")) == DATA_VERSION and existing.get("source_sha256") == file_sha(archive_path):
            with closing(sqlite3.connect(db_path)) as con:
                if con.execute("PRAGMA quick_check").fetchone()[0] == "ok":
                    print("Reusing verified SQLite database.", flush=True)
                    return existing
    db_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = db_path.with_suffix(".building.sqlite")
    temporary.unlink(missing_ok=True)
    counts = Counter()
    csv.field_size_limit(20_000_000)
    with closing(sqlite3.connect(temporary)) as con:
        con.execute("""CREATE TABLE complaints (
            complaint_id TEXT PRIMARY KEY, date_received TEXT NOT NULL,
            product TEXT NOT NULL, issue TEXT NOT NULL, company TEXT NOT NULL,
            state TEXT NOT NULL, company_response TEXT NOT NULL, timely_response TEXT NOT NULL,
            has_narrative INTEGER NOT NULL, clean_text TEXT, text_hash TEXT)""")
        insert = "INSERT OR IGNORE INTO complaints VALUES (?,?,?,?,?,?,?,?,?,?,?)"
        batch = []
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.namelist():
                if not member.lower().endswith(".csv"):
                    continue
                with archive.open(member) as f:
                    reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig", newline=""))
                    required = {"Complaint ID", "Date received", "Product", "Consumer complaint narrative", "Issue"}
                    if not required.issubset(reader.fieldnames or []):
                        raise ValueError("Unexpected archive schema.")
                    for row in reader:
                        counts["source_rows"] += 1
                        received = row["Date received"].strip()
                        if not re.fullmatch(r"2025-(01|02)-\d\d", received):
                            raise ValueError(f"Unexpected source date: {received!r}")
                        narrative = row["Consumer complaint narrative"].strip()
                        counts["with_narrative"] += bool(narrative)
                        text = normalize_text(narrative) if narrative else ""
                        eligible = len(text.split()) >= 12
                        counts["narratives_too_short"] += bool(narrative) and not eligible
                        digest = hashlib.sha256(text.encode()).hexdigest() if eligible else None
                        batch.append((row["Complaint ID"], received, row["Product"].strip(), row["Issue"].strip(),
                                      row.get("Company", "").strip(), row.get("State", "").strip(),
                                      row.get("Company response to consumer", "").strip(), row.get("Timely response?", "").strip(),
                                      int(bool(narrative)), text if eligible else None, digest))
                        if len(batch) >= 10000:
                            con.executemany(insert, batch)
                            con.commit()
                            batch.clear()
                            if counts["source_rows"] % 100000 == 0:
                                print(f"Loaded {counts['source_rows']:,} source rows...", flush=True)
        if batch:
            con.executemany(insert, batch)
        con.execute("CREATE INDEX idx_date_product ON complaints(date_received,product)")
        con.execute("CREATE INDEX idx_text_hash ON complaints(text_hash,date_received,complaint_id)")
        con.commit()
        counts["database_rows"] = con.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
    temporary.replace(db_path)
    manifest = {
        "pipeline_version": VERSION, "data_pipeline_version": DATA_VERSION, "source_url": SOURCE_URL, "source_page": SOURCE_PAGE,
        "source_sha256": file_sha(archive_path), "source_bytes": archive_path.stat().st_size,
        "date_min": "2025-01-01", "date_max": "2025-02-28", **dict(counts),
        "duplicate_ids_removed": counts["source_rows"] - counts["database_rows"],
        "text_filter": "At least 12 normalized words; URLs, emails, digits and redaction markers removed.",
        "analytics_population": "All archived records, including records without narrative text.",
        "limitations": "Historical self-selected, unverified complaints; counts do not measure company failure rates or prove misconduct.",
    }
    write_json(manifest_path, manifest)
    return manifest


def export_analytics(root: Path) -> dict:
    output = root / "reports/analytics"
    output.mkdir(parents=True, exist_ok=True)
    queries = {
        "daily": "SELECT date_received AS date, product, COUNT(*) AS complaints, SUM(has_narrative) AS narratives FROM complaints GROUP BY 1,2 ORDER BY 1,2",
        "products": "SELECT product, COUNT(*) AS complaints, SUM(has_narrative) AS narratives, SUM(CASE WHEN timely_response='Yes' THEN 1 ELSE 0 END) AS timely, SUM(CASE WHEN timely_response IN ('Yes','No') THEN 1 ELSE 0 END) AS timeliness_known FROM complaints GROUP BY 1 ORDER BY complaints DESC",
        "issues": "SELECT product, issue, COUNT(*) AS complaints FROM complaints GROUP BY 1,2 ORDER BY complaints DESC",
        "responses": "SELECT company_response, COUNT(*) AS complaints FROM complaints GROUP BY 1 ORDER BY complaints DESC",
        "monthly": "SELECT substr(date_received,1,7) AS month, product, COUNT(*) AS complaints FROM complaints GROUP BY 1,2 ORDER BY 1,2",
        "states": "SELECT state, COUNT(*) AS complaints FROM complaints WHERE state<>'' GROUP BY 1 ORDER BY complaints DESC",
    }
    analytics = {}
    with closing(sqlite3.connect(root / "data/complaints.sqlite")) as con:
        for name, query in queries.items():
            frame = pd.read_sql_query(query, con)
            frame.to_csv(output / f"{name}.csv", index=False)
            analytics[name] = frame.to_dict(orient="records")
        weekly = pd.read_sql_query("""SELECT date(date_received, printf('-%d days',
           (CAST(strftime('%w',date_received) AS INTEGER)+6)%7)) AS week,
           product,issue,COUNT(*) AS complaints FROM complaints GROUP BY 1,2,3 ORDER BY 1,2,3""", con)
        sql_file=root/"sql/business_analysis.sql"
        if sql_file.exists():
            statements=[s.strip() for s in sql_file.read_text(encoding="utf-8").split(";") if s.strip()]
            for number,statement in enumerate(statements,1):
                pd.read_sql_query(statement,con).to_csv(output/f"sql_{number:02d}.csv",index=False)
    weekly.to_csv(output / "weekly_issues.csv", index=False)
    analytics["signals"] = detect_signals(weekly, "2025-01-01", "2025-02-28")
    complete_weeks=sorted(w for w in weekly["week"].unique() if w>="2025-01-01" and pd.Timestamp(w)+pd.Timedelta(days=6)<=pd.Timestamp("2025-02-28"))
    analytics["signal_history"]=[detect_signals(weekly,"2025-01-01",(pd.Timestamp(week)+pd.Timedelta(days=6)).strftime("%Y-%m-%d")) for week in complete_weeks[4:]]
    write_json(output / "signals.json", analytics["signals"])
    write_json(output / "signal_history.json", analytics["signal_history"])
    return analytics


def detect_signals(weekly: pd.DataFrame, date_min: str, date_max: str) -> dict:
    """Compare last complete week against four complete prior weeks; partial weeks excluded."""
    first, last = pd.Timestamp(date_min), pd.Timestamp(date_max)
    complete = sorted(w for w in weekly["week"].unique() if pd.Timestamp(w) >= first and pd.Timestamp(w) + pd.Timedelta(days=6) <= last)
    if len(complete) < 5:
        return {"status": "insufficient_history", "items": []}
    current, baseline = complete[-1], complete[-5:-1]
    totals = weekly.groupby("week")["complaints"].sum()
    current_total = int(totals[current])
    baseline_total = int(totals.loc[baseline].sum())
    recent = weekly[weekly.week == current].groupby(["product", "issue"])["complaints"].sum()
    previous = weekly[weekly.week.isin(baseline)].groupby(["product", "issue"])["complaints"].sum()
    items = []
    for (product, issue), count in recent.items():
        before = int(previous.get((product, issue), 0))
        average = before / 4
        ratio = float(count / average) if average else None
        delta_pp = 100 * (count / current_total - before / baseline_total)
        if count >= 30 and average >= 5 and ratio >= 1.5 and delta_pp >= 0.5:
            items.append({"product": product, "issue": issue, "current": int(count), "baseline_weekly_average": average,
                          "volume_ratio": round(ratio, 3), "share_change_pp": round(delta_pp, 3)})
    return {"status": "descriptive_heuristic", "week_start": current, "baseline_weeks": baseline,
            "current_week_total": current_total, "baseline_four_week_total": baseline_total,
            "rule": "count >=30, baseline weekly mean >=5, volume >=1.5x baseline, share increase >=0.5 percentage points",
            "limitations": "Exploratory signals, not statistically confirmed anomalies or proof of company misconduct. Only seven complete weeks are available.",
            "items": sorted(items, key=lambda x: -x["share_change_pp"])}


def load_model_data(root: Path):
    with closing(sqlite3.connect(root / "data/complaints.sqlite")) as con:
        frame = pd.read_sql_query("""SELECT complaint_id,date_received,product,clean_text,text_hash FROM
          (SELECT *,ROW_NUMBER() OVER(PARTITION BY text_hash ORDER BY date_received,complaint_id) AS rn
           FROM complaints WHERE clean_text IS NOT NULL) WHERE rn=1 ORDER BY date_received,complaint_id""", con)
        eligible_before = con.execute("SELECT COUNT(*) FROM complaints WHERE clean_text IS NOT NULL").fetchone()[0]
    return frame, {"eligible_before_dedup": eligible_before, "normalized_duplicates_removed": eligible_before-len(frame), "unique_eligible_narratives": len(frame)}


def cap_classes(frame: pd.DataFrame, cap: int | None):
    if cap is None:
        return frame.copy()
    selected = []
    for _, group in frame.groupby("product", sort=True):
        selected.append(group.sample(n=min(cap, len(group)), random_state=SEED))
    return pd.concat(selected).sort_values(["date_received", "complaint_id"]).reset_index(drop=True)


def membership_fingerprint(frame: pd.DataFrame) -> str:
    columns=["complaint_id","date_received","product","text_hash"]
    rows=frame[columns].astype(str).sort_values("complaint_id").values.tolist()
    return hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()


def make_splits(frame: pd.DataFrame, profile: str):
    cfg = PROFILES[profile]
    windows = {
        "train": frame[frame.date_received <= "2025-02-09"],
        "validation": frame[(frame.date_received >= "2025-02-10") & (frame.date_received <= "2025-02-16")],
        "test": frame[frame.date_received >= "2025-02-17"],
    }
    labels = sorted(windows["train"]['product'].value_counts().loc[lambda x: x >= 20].index.tolist())
    if len(labels) < 2:
        raise ValueError("Insufficient labels in training window.")
    splits = {name: cap_classes(part[part['product'].isin(labels)], cfg["train_cap_per_class"] if name=="train" else cfg["eval_cap_per_class"]) for name,part in windows.items()}
    for name, part in splits.items():
        if part.empty:
            raise ValueError(f"Empty {name} split.")
    sets = {name: set(part.text_hash) for name,part in splits.items()}
    assert not (sets["train"] & sets["validation"] or sets["train"] & sets["test"] or sets["validation"] & sets["test"]), "Duplicate leakage"
    manifest = {
        "strategy": "Chronological; keep earliest normalized text once before splitting. Vocabulary is fitted only on training text.",
        "profile": profile, "seed": SEED, "train_cap_per_class": cfg["train_cap_per_class"],
        "training_rows_before_cap": int(windows["train"]['product'].isin(labels).sum()),
        "training_rows_excluded_by_cap": int(windows["train"]['product'].isin(labels).sum())-len(splits["train"]),
        "evaluation_capped": cfg["eval_cap_per_class"] is not None,
        "evaluation_scope": ("Category-capped pipeline smoke check; not a population performance estimate." if profile=="smoke" else
                             "All retained, in-scope unique narratives in each chronological window; all eligible training-window narratives are used." if profile=="uncapped" else
                             "All retained, in-scope unique narratives in each chronological evaluation window; training is capped by category."),
        "labels": labels, "out_of_scope_rows": int((~frame['product'].isin(labels)).sum()),
        "normalized_hash_overlap": 0,
        "holdout_fingerprints": {name:membership_fingerprint(splits[name]) for name in ("validation","test")},
        "near_duplicate_limit": "Normalization catches exact and variable-identifier templates. Paraphrases and other near-duplicates may remain.",
        "splits": {name: {"rows": len(part), "date_min": part.date_received.min(), "date_max": part.date_received.max(),
                           "class_counts": {str(k):int(v) for k,v in part['product'].value_counts().items()}} for name,part in splits.items()},
    }
    return splits, manifest


def load_capped_reference(root: Path, splits: dict):
    path=root/"reference/capped_full_reference.json"
    if not path.exists():
        raise ValueError("The uncapped comparison needs reference/capped_full_reference.json from the supplied notebook or project package.")
    reference=json.loads(path.read_text(encoding="utf-8"))
    if reference["source_sha256"]!=SOURCE_SHA256:
        raise ValueError("Capped reference uses a different dataset.")
    for name in ("validation","test"):
        expected=reference["holdout_membership"][name]
        if len(splits[name])!=expected["rows"] or membership_fingerprint(splits[name])!=expected["fingerprint"]:
            raise ValueError(f"The {name} complaints differ from the capped run. Do not compare scores from different holdouts.")
    return reference


def compare_validation_to_capped(reference: dict, selected: dict):
    baseline=float(reference["selected_validation_macro_f1"])
    score=float(selected["macro_f1"])
    recommend="uncapped" if score>baseline+1e-12 else "full"
    return {"criterion":"validation macro-F1 only; test metrics do not choose the profile",
            "capped_selected_model":reference["selected_model"],"capped_training_rows":reference["training_rows"],
            "capped_validation_macro_f1":baseline,"uncapped_selected_model":selected["model"],
            "uncapped_validation_macro_f1":score,"delta_validation_macro_f1":score-baseline,
            "recommended_profile":recommend,"tie_rule":"Preserve capped model when validation macro-F1 ties.",
            "reference_archive_sha256":reference["reference_archive_sha256"],"identical_holdouts_verified":True}


def metrics(y, pred, labels):
    return {"accuracy": float(accuracy_score(y,pred)), "balanced_accuracy": float(balanced_accuracy_score(y,pred)),
            "macro_f1": float(f1_score(y,pred,labels=labels,average="macro",zero_division=0)),
            "weighted_f1": float(f1_score(y,pred,labels=labels,average="weighted",zero_division=0))}


def fit_models(root: Path, splits: dict, split_manifest: dict, profile: str, execution_environment: str):
    cfg = PROFILES[profile]
    train, valid, test = (splits[x] for x in ("train", "validation", "test"))
    labels = split_manifest["labels"]
    reference=load_capped_reference(root,splits) if profile=="uncapped" else None
    models = {
        "majority_baseline": DummyClassifier(strategy="most_frequent"),
        "complement_naive_bayes": ComplementNB(alpha=0.5),
        "logistic_regression": LogisticRegression(C=2.0, class_weight="balanced", max_iter=350, solver="lbfgs", random_state=SEED),
    }
    candidates, fitted = [], {}
    for name, estimator in models.items():
        start = time.perf_counter()
        pipeline = Pipeline([("tfidf", TfidfVectorizer(preprocessor=normalize_text, ngram_range=(1,2), min_df=2,
                                                     max_df=0.98, max_features=cfg["max_features"], sublinear_tf=True, dtype=np.float32)),
                             ("classifier", estimator)])
        pipeline.fit(train.clean_text.tolist(), train['product'].tolist())
        prediction = pipeline.predict(valid.clean_text.tolist())
        row = {"model": name, **metrics(valid['product'],prediction,labels), "fit_and_validation_seconds": round(time.perf_counter()-start,2)}
        candidates.append(row)
        fitted[name] = pipeline
        print(f"Validation: {name}: macro-F1={row['macro_f1']:.4f}",flush=True)
    winner_row = max((row for row in candidates if row["model"]!="majority_baseline"),key=lambda row:row["macro_f1"])
    winner = winner_row["model"]
    comparison=compare_validation_to_capped(reference,winner_row) if reference else None
    model = fitted[winner]
    probabilities = model.predict_proba(valid.clean_text.tolist())
    confidence = probabilities.max(axis=1)
    validation_pred = model.classes_[probabilities.argmax(axis=1)]
    threshold_rows=[]
    for threshold in np.arange(0.4,0.951,0.05):
        keep = confidence >= threshold
        threshold_rows.append({"threshold": round(float(threshold),2), "coverage": float(keep.mean()), "accepted": int(keep.sum()),
                               "accuracy_when_accepted": float(np.mean(validation_pred[keep]==valid['product'].to_numpy()[keep])) if keep.any() else None})
    acceptable = [row for row in threshold_rows if row["accepted"]>=20 and row["coverage"]>=0.1 and row["accuracy_when_accepted"]>=0.85]
    threshold = max(acceptable,key=lambda row:row["coverage"])["threshold"] if acceptable else 0.9
    test_pred = model.predict(test.clean_text.tolist())
    test_proba = model.predict_proba(test.clean_text.tolist())
    test_scores = test_proba.max(axis=1)
    accepted = test_scores >= threshold
    report = classification_report(test['product'],test_pred,labels=labels,output_dict=True,zero_division=0)
    confusion = confusion_matrix(test['product'],test_pred,labels=labels)
    results = {
        "pipeline_version": VERSION, "profile": profile, "execution_environment": execution_environment,
        "execution_time_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(), "sklearn_version": sklearn.__version__,
        "pandas_version": pd.__version__, "numpy_version": np.__version__,
        "selected_model": winner, "selection_metric": "validation macro-F1; test used only after model and routing-threshold selection",
        "training_cap_per_class":cfg["train_cap_per_class"],
        "comparison_to_capped":comparison,
        "validation_models": candidates, "test": metrics(test['product'],test_pred,labels),
        "test_baseline": metrics(test['product'],fitted["majority_baseline"].predict(test.clean_text.tolist()),labels),
        "classification_report": report, "labels": labels, "confusion_matrix": confusion.tolist(),
        "routing": {"threshold": threshold, "validation_target_accuracy":0.85, "validation_target_met": bool(acceptable),
                    "test_coverage": float(accepted.mean()), "test_accepted": int(accepted.sum()),
                    "test_accuracy_when_accepted": float(np.mean(test_pred[accepted]==test['product'].to_numpy()[accepted])) if accepted.any() else None,
                    "score_note": "Uncalibrated model score; not a guaranteed probability. Review route is a demonstration, not autonomous financial decision-making."},
        "threshold_search": threshold_rows,
        "evidence_status": (f"Smoke profile executed in {execution_environment}; small pipeline check, not final population performance." if profile=="smoke" else
                            f"{profile.title()} profile executed in {execution_environment}; interpret within documented dataset and split scope."),
    }
    models_dir = root/"models"/profile
    reports_dir = root/"reports"/profile
    models_dir.mkdir(parents=True,exist_ok=True)
    reports_dir.mkdir(parents=True,exist_ok=True)
    joblib.dump(model,models_dir/"classifier.joblib",compress=3)
    write_json(models_dir/"routing.json",results["routing"])
    write_json(reports_dir/"metrics.json",results)
    write_json(reports_dir/"split_manifest.json",split_manifest)
    if reference:
        write_json(reports_dir/"capped_reference.json",reference)
        write_json(reports_dir/"comparison_to_capped.json",comparison)
    pd.DataFrame(candidates).to_csv(reports_dir/"validation_models.csv",index=False)
    pd.DataFrame(report).transpose().to_csv(reports_dir/"classification_report.csv")
    pd.DataFrame(confusion,index=labels,columns=labels).to_csv(reports_dir/"confusion_matrix.csv")
    for name,part in splits.items():
        part[["complaint_id","date_received","product","text_hash"]].to_csv(reports_dir/f"{name}_membership.csv",index=False)
    pd.DataFrame({"complaint_id":test.complaint_id,"actual":test['product'],"predicted":test_pred,
                  "score":test_scores,"human_review":~accepted}).to_csv(reports_dir/"test_predictions.csv",index=False)
    # Verify the portable artifact immediately after writing.
    loaded = joblib.load(models_dir/"classifier.joblib")
    assert np.array_equal(loaded.predict(test.clean_text.iloc[:10].tolist()),test_pred[:10])
    write_json(models_dir/"artifact_manifest.json",{"model_sha256":file_sha(models_dir/"classifier.joblib"),
               "profile":profile,"execution_environment":execution_environment,"sklearn_version":sklearn.__version__,
               "python_version":platform.python_version(),"warning":"Only load joblib files you generated or trust."})
    return results


def publish_dashboard_data(root: Path, analytics: dict, results: dict, manifest: dict):
    data = {"source":manifest,"analytics":analytics,"model":results,
            "project":"Financial Complaint Intelligence","historical":True}
    write_json(root/"reports"/results["profile"]/"dashboard_data.json",data)


def make_figures(root: Path, results: dict):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    folder=root/"reports"/results["profile"]
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"axes.spines.top":False,"axes.spines.right":False})
    rows=results["validation_models"]
    fig,ax=plt.subplots(figsize=(8,4.8),layout="constrained")
    names=[row["model"].replace("_"," ").title() for row in rows]
    bars=ax.barh(names,[row["macro_f1"] for row in rows],color=["#b0b8c5","#5b9c9a","#123b56"])
    ax.set(xlim=(0,1),xlabel="Validation macro-F1",title=f"Model comparison | {results['profile']} profile")
    for bar,row in zip(bars,rows):
        ax.text(min(row["macro_f1"]+0.02,0.95),bar.get_y()+bar.get_height()/2,f"{row['macro_f1']:.3f}",va="center")
    fig.savefig(folder/"validation_comparison.png",dpi=180)
    plt.close(fig)
    matrix=np.asarray(results["confusion_matrix"],dtype=float)
    normalized=matrix/np.maximum(matrix.sum(axis=1,keepdims=True),1)
    labels=[x[:28]+("..." if len(x)>28 else "") for x in results["labels"]]
    fig,ax=plt.subplots(figsize=(11,9),layout="constrained")
    plotted=ax.imshow(normalized,vmin=0,vmax=1,cmap="Blues")
    ax.set(xticks=range(len(labels)),yticks=range(len(labels)),xticklabels=labels,yticklabels=labels,
           xlabel="Predicted product",ylabel="Actual product",title=f"Held-out test confusion matrix | {results['profile']} profile\nRows normalized; this does not measure business impact")
    plt.setp(ax.get_xticklabels(),rotation=65,ha="right",rotation_mode="anchor",fontsize=8)
    for i in range(len(labels)):
        for j in range(len(labels)):
            if normalized[i,j]>=0.05:
                ax.text(j,i,f"{normalized[i,j]:.2f}",ha="center",va="center",fontsize=8,color="white" if normalized[i,j]>0.55 else "#10243a")
    fig.colorbar(plotted,ax=ax,shrink=0.7,label="Fraction of actual category")
    fig.savefig(folder/"confusion_matrix.png",dpi=170)
    plt.close(fig)


def export_bundle(root: Path, profile: str) -> Path:
    target=root/f"Financial_Complaint_Results_{profile}.zip"
    with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED) as archive:
        for folder in [root/"reports"/profile,root/"reports/analytics",root/"models"/profile]:
            for path in sorted(folder.rglob("*")):
                if path.is_file():
                    archive.write(path,path.relative_to(root).as_posix())
        archive.write(root/"reports/data_manifest.json","reports/data_manifest.json")
        archive.writestr("EXECUTION_STATUS.txt",f"Profile: {profile}\nRead reports/{profile}/metrics.json for the actual execution environment and results.\nThis results archive does not include the raw archive or SQLite database.\n")
    return target


def run(root: Path, profile: str="smoke", execution_environment: str="local_cpu"):
    root=root.resolve()
    print(f"Starting {profile} profile in {execution_environment}",flush=True)
    archive=download_archive(root)
    manifest=build_database(root,archive)
    analytics=export_analytics(root)
    frame,quality=load_model_data(root)
    splits,split_manifest=make_splits(frame,profile)
    split_manifest.update(quality)
    print({name:len(part) for name,part in splits.items()},flush=True)
    results=fit_models(root,splits,split_manifest,profile,execution_environment)
    make_figures(root,results)
    publish_dashboard_data(root,analytics,results,manifest)
    bundle=export_bundle(root,profile)
    print(f"Finished. Results: {bundle}",flush=True)
    return results


if __name__=="__main__":
    # Keep pickled preprocessing functions importable under the same module name.
    import complaint_project
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile",choices=PROFILES,default="smoke")
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument("--environment",default="local_cpu")
    args=parser.parse_args()
    complaint_project.run(args.root,args.profile,args.environment)
