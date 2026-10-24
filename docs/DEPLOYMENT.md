# Deployment

The app serves its dashboard and Python API from the same origin. It loads the saved uncapped classifier and aggregate counts at startup. Hosting does not download the CFPB dataset or train a new model.

## Render configuration

`render.yaml` defines one **free Python web service** with:

- Python 3.13.16, matching the training runtime's Python minor version.
- Build: `pip install -r requirements.txt`.
- Start: `uvicorn api:app --host 0.0.0.0 --port $PORT --workers 1 --no-access-log`.
- Health check: `/api/health`.
- `COMPLAINT_PROFILE=uncapped` and `COMPLAINT_HOSTED=1`.
- One numerical-library thread per worker to limit resource use.

Connect this repository to Render and use the Blueprint configuration, or create a Python Web Service using those settings. Select the **Free** instance. No paid plan or persistent database is required by this demonstration. A service URL is a completed result only after Render reports a successful deployment and the HTTP checks pass.

Render's free web service sleeps after 15 minutes without incoming traffic and can take about a minute to start on the next visit. Monthly free usage limits also apply. Open the demo before an interview so it is ready when the presentation begins. No artificial keep-alive jobs are configured.

## Processing and storage

The hosted classification page explicitly says input is sent to the hosted model. The application does not save complaint input, train on it, or include it in its access logs. Visitors should use illustrative or anonymized complaints. Infrastructure request metadata is governed by the hosting provider's policies.

The repository includes read-only historical aggregates and trusted saved model artifacts. No database creation, background training or user-file upload is required. Local execution uses the existing Windows launcher and keeps the local processing description.

## Verification after deployment

1. Confirm `/api/health` returns `status: ok` and `profile: uncapped`.
2. Confirm `/api/summary` reports 811,019 records and the correct test metrics.
3. Query `/api/analytics?product=Credit%20card&start=2025-01-01&end=2025-01-31`; expect 9,073 complaints and 3,992 narratives.
4. Submit the illustrative credit-report example to `/api/classify`; verify real inference, three product matches and an explicit review route.
5. Visit the four browser views, inspect the hosted processing notice, filters, CSV export and navigation.

The Power BI report remains a downloadable local file in `powerbi/`. No Power BI Service or Publish to web deployment is included.

References: [Render FastAPI guide](https://render.com/docs/deploy-fastapi), [Python version selection](https://render.com/docs/python-version), [free service behavior](https://render.com/docs/free).
