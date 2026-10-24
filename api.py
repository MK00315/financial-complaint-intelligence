"""Analyst dashboard and checksum-verified model-serving API."""
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path

import joblib
import numpy as np
import sklearn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field

from complaint_project import file_sha, normalize_text
from dashboard_data import FIRST, LAST, aggregate, csv_export, load_dashboard_data

ROOT = Path(__file__).resolve().parent


def load_artifacts(root=ROOT, profile=None):
    profile = profile or os.environ.get("COMPLAINT_PROFILE")
    if not profile:
        if (root/"reports/uncapped/metrics.json").exists():
            result=json.loads((root/"reports/uncapped/metrics.json").read_text(encoding="utf-8"))
            recommendation=(result.get("comparison_to_capped") or {}).get("recommended_profile","uncapped")
            if recommendation=="full" and not (root/"models/full/classifier.joblib").exists():
                raise RuntimeError("The validation comparison recommends the preserved capped model. Import its full results before serving predictions.")
            profile=recommendation
        else:
            profile="full" if (root/"reports/full/metrics.json").exists() else "smoke"
    model_dir=root/"models"/profile
    manifest=json.loads((model_dir/"artifact_manifest.json").read_text(encoding="utf-8"))
    if manifest["sklearn_version"] != sklearn.__version__:
        raise RuntimeError(f"Model needs scikit-learn {manifest['sklearn_version']}; current version is {sklearn.__version__}.")
    if file_sha(model_dir/"classifier.joblib") != manifest["model_sha256"]:
        raise RuntimeError("Model checksum verification failed.")
    return {
        "profile":profile,
        "model":joblib.load(model_dir/"classifier.joblib"),
        "routing":json.loads((model_dir/"routing.json").read_text(encoding="utf-8")),
        "data":json.loads((root/"reports"/profile/"dashboard_data.json").read_text(encoding="utf-8")),
    }


@asynccontextmanager
async def lifespan(app):
    app.state.artifacts=load_artifacts()
    app.state.analytics=load_dashboard_data(ROOT,app.state.artifacts["data"]["source"])
    profile=app.state.artifacts["profile"]
    app.state.split=json.loads((ROOT/"reports"/profile/"split_manifest.json").read_text(encoding="utf-8"))
    yield


app=FastAPI(title="Financial Complaint Intelligence",version="1.2.0",lifespan=lifespan)
app.add_middleware(GZipMiddleware,minimum_size=1000)


@app.middleware("http")
async def response_headers(request, call_next):
    response=await call_next(request)
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["Referrer-Policy"]="no-referrer"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"]="no-store"
    return response


class Complaint(BaseModel):
    text: str = Field(min_length=30,max_length=12000)


def predict_text(artifacts, text):
    cleaned=normalize_text(text)
    if len(cleaned.split())<12:
        raise ValueError("Enter a financial complaint with at least 12 words after removing identifiers.")
    vectorizer=artifacts["model"].named_steps["tfidf"]
    if vectorizer.transform([text]).nnz<3:
        raise ValueError("Too little recognizable financial complaint vocabulary; human review is needed.")
    scores=artifacts["model"].predict_proba([text])[0]
    order=np.argsort(scores)[::-1][:3]
    top=float(scores[order[0]])
    review=top<artifacts["routing"]["threshold"]
    return {"category":str(artifacts["model"].classes_[order[0]]),"score":top,
            "human_review":review,"route":"Human review" if review else "Suggested category",
            "alternatives":[{"category":str(artifacts["model"].classes_[i]),"score":float(scores[i])} for i in order],
            "profile":artifacts["profile"],"score_note":artifacts["routing"]["score_note"]}


@app.get("/api/health")
def health():
    return {"status":"ok","profile":app.state.artifacts["profile"],"project":"Financial Complaint Intelligence","app_version":"1.2.0"}


@app.get("/api/summary")
def summary():
    return app.state.artifacts["data"]


@app.get("/api/model")
def model_details():
    hosted=os.environ.get("COMPLAINT_HOSTED", "").strip() == "1"
    return {"profile":app.state.artifacts["profile"], "model":app.state.artifacts["data"]["model"],
            "split":app.state.split, "source":app.state.artifacts["data"]["source"],
            "serving":{"mode":"hosted" if hosted else "local",
                       "label":"HOSTED MODEL" if hosted else "LOCAL PROCESSING",
                       "text_note":("Your text is sent to the hosted model for analysis. This application does not save the text. Use illustrative or anonymized complaints."
                                    if hosted else "Your text is processed by the local model and is not saved by this application.")}}


@app.get("/api/analytics")
def analytics(product:str="",start:str=FIRST,end:str=LAST,issue:str=""):
    try:
        return aggregate(app.state.analytics,product,start,end,issue)
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc


@app.get("/api/export")
def export(kind:str="issues",product:str="",start:str=FIRST,end:str=LAST,issue:str="",q:str=Query(default="",max_length=300),sort:str="count_desc"):
    try:
        result=aggregate(app.state.analytics,product,start,end,issue)
        content=csv_export(result,kind,q,sort)
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc
    return Response(content="\ufeff"+content,media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition":f'attachment; filename="Financial_Complaints_{kind}_{start}_{end}.csv"'})


@app.post("/api/classify")
def classify(complaint:Complaint):
    try:
        return predict_text(app.state.artifacts,complaint.text)
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc


@app.get("/",include_in_schema=False)
def dashboard():
    return FileResponse(ROOT/"dashboard/index.html",headers={"Cache-Control":"no-cache"})


@app.get("/favicon.svg",include_in_schema=False)
def favicon():
    return FileResponse(ROOT/"dashboard/assets/favicon.svg")


app.mount("/assets",StaticFiles(directory=ROOT/"dashboard/assets"),name="assets")


# The Windows launcher stays on loopback. render.yaml supplies the hosted command.
if __name__=="__main__":
    import uvicorn
    print("Financial Complaint Intelligence: http://127.0.0.1:8765",flush=True)
    uvicorn.run("api:app",host="127.0.0.1",port=8765,reload=False)
