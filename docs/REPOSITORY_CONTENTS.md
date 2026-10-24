# Repository contents

This repository combines the verified web application, reproducible modeling pipeline and separate native Power BI report.

The selected classifier is under `models/uncapped/`; the preserved `full` capped and `smoke` artifacts support comparison and integration checks. The model checksum is verified before deserialization. Do not replace these artifacts with files from an untrusted source.

`reports/analytics/dashboard_analytics.json` contains 5,024 date/product/issue aggregates representing all 811,019 source complaints. Other CSVs and JSON files contain aggregate analysis or model evaluation. Record-level membership exports, test prediction exports, the original narrative archive, SQLite database, environments and account files are excluded.

The compact `tests/fixtures/smoke_results.zip` contains genuine smoke-run model and summary artifacts for importer tests. Record-level CSV exports were omitted from that fixture; the included model bytes and reported results are unchanged. Earlier full result archives remain outside this repository.

`docs/DASHBOARD_VERIFICATION.md`, `docs/DELIVERY_VERIFICATION.json` and the Power BI verification files describe the checks performed on the earlier local deliveries. Current publication and hosting checks are recorded separately. Machine-specific workspace prefixes in readable public verification metadata were replaced with `<local-workspace>`; metrics, counts and model checksums were preserved.

The report at `powerbi/Financial_Complaint_Intelligence.pbix` has embedded aggregate data and opens in Power BI Desktop. Its editable PBIP/TMDL/PBIR source, CSV inputs and screenshots are included beside it. Local Power BI cache files and private editor state are excluded.

The model, data, dashboard and report are a portfolio demonstration using historical CFPB data. No financial institution connection, live complaint feed or financial decision service is represented.
