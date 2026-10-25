# Deployment

The main demo is **https://complaint-intelligence-mk.vercel.app/**. Vercel serves the static interface and bundled fonts. Requests under `/api/` are forwarded to the existing **https://financial-complaint-intelligence.onrender.com** Python service. The original Render link still serves its dashboard and API; no service was deleted or replaced.

## Connection screen

The first HTML response contains the complete sky-blue connection screen, with the workspace hidden. It checks the real service health, including project identity and the selected uncapped profile, before loading summary, model details and any analytics required by the requested initial page. A live elapsed-time counter and actual startup steps replace fake progress percentages.

Requests have bounded timeouts and serial retry delays. After three minutes without a complete startup, polling stops and **Try again** is available. Offline startup shows a reconnect message. The screen fades into the workspace only after its initial data is ready and respects reduced-motion settings. There is no continuous keep-alive job.

Free Render hosting can sleep after inactivity and take about a minute to wake. This split keeps the frontend available during that wait; it does not eliminate backend startup time. Provider availability and free-plan limits still apply.

## Update the frontend

From the repository root, with the official Vercel CLI signed into the existing `mk00315` team:

```powershell
npx --yes vercel@latest deploy --cwd dashboard --project complaint-intelligence-mk --prod --yes --scope mk00315
```

Deploy **only `dashboard/`**. This is a static deployment with no framework, build or package-install step. The deployment contains HTML, browser scripts, CSS, fonts and the favicon; model files, data, native reports and Python are not uploaded to Vercel. No frontend secret or API key is required.

`dashboard/vercel.json` forwards `/api/:path*` to Render, preserving queries and POST requests under the same browser origin. API caching is disabled. The browser does not need wildcard CORS. All fonts are bundled locally and the content-security policy restricts scripts and network requests to the site's own origin.

The current Vercel release was deployed directly with the CLI. **GitHub Actions runs tests; it does not deploy either host.** GitHub is not connected for automatic Vercel deployments. Redeploy explicitly after future frontend changes.

## Existing Render backend

Keep the existing Python service, saved model and configuration. Its checked-in `render.yaml` specifies:

- Build: `pip install -r requirements.txt`
- Start: `uvicorn api:app --host 0.0.0.0 --port $PORT --workers 1 --no-access-log`
- Health: `/api/health`
- `COMPLAINT_PROFILE=uncapped`, `COMPLAINT_HOSTED=1` and single-thread numeric-library settings.

This frontend split required no Render redeployment, model retraining, cloud-data migration, account upgrade or paid service. Future API/model changes need their own Render deployment and verification.

## Processing and storage

Classification text travels through Vercel to the existing hosted model. The application does not save complaint input or train on it, and access logging remains disabled in the configured server command. Visitors should use illustrative or anonymized complaints. Infrastructure request metadata is governed by the hosting providers' policies.

Historical aggregates and trusted saved model artifacts remain on Render. The existing Windows launcher still runs the complete application locally with the local-processing disclosure. The new connection client expects the selected uncapped profile. Opening the dashboard does not require Colab, Azure or Databricks.

## Verify an update

1. Open the production Vercel URL without signing in. Check the static connection screen, then the four routes.
2. Confirm `/api/health` returns `status: ok`, project `Financial Complaint Intelligence`, and `profile: uncapped`.
3. Check `/api/summary`: 811,019 source records.
4. Query `/api/analytics?product=Credit%20card&start=2025-01-01&end=2025-01-31`: 9,073 complaints and 3,992 narratives.
5. Classify the illustrative credit-report example: three suggestions and top score about 0.893. Short input must remain a readable 422 validation error.
6. Download a filtered CSV; check that the period, product and totals match.
7. Confirm the old Render URL still works. Check that the new production URL has no Vercel sign-in redirect.

Local checks: `python -m pytest tests -q` and `node --test tests/connection.test.cjs`. The portable copy intentionally skips three SQL comparisons requiring the excluded raw database. The existing full-workspace raw-data verification remains separate.

The Power BI report remains a downloadable local file in `powerbi/`. No Power BI Service publication is included.

References: [Vercel external rewrites](https://vercel.com/docs/routing/rewrites), [Render FastAPI](https://render.com/docs/deploy-fastapi), [Render free-service behavior](https://render.com/docs/free).
