# Financial Complaint Intelligence — Power BI

Open **Financial_Complaint_Intelligence.pbix** in Power BI Desktop. The report is already populated and saved on Overview with all products and dates selected. No Colab training, Azure subscription, Python setup or Power BI Service sign-in is needed to view this local file.

## Report pages

| Page | What you can explore |
|---|---|
| Overview | Complaint and narrative totals, reporting trends, product mix and leading issues |
| Issue Explorer | Product, issue and date filters; detailed counts, narrative coverage and reported response timeliness |
| Emerging Issues | Three evaluable complete weeks, four-week baselines, growth candidates and explicit screening rules |
| Model & Data | Fixed test metrics, all 11 class F1 scores, row-percentage confusion matrix, model selection and evaluation limits |

Use the page tabs at the bottom to navigate. In Desktop editing mode, hold **Ctrl** while clicking the navigation buttons across the report header. Charts and long tables have their own scroll areas. Use **View → Page view → Fit to page** if the canvas appears too small.

## Verified results

| Result | Value |
|---|---:|
| Archived complaints | 811,019 |
| Written narratives | 265,405 |
| Narrative coverage | 32.72% |
| Reporting dates | 01 Jan–28 Feb 2025 |
| Product categories / product-issue combinations | 11 / 135 |
| Uncapped train / validation / test narratives | 101,935 / 9,411 / 15,390 |
| Selected model | TF-IDF + Logistic Regression |
| Held-out test accuracy / macro F1 | 79.51% / 0.6672 |
| Balanced accuracy | 71.85% |
| Issues meeting all screening rules | 0 in each of the three evaluable weeks |

Analytics use all 811,019 archived records. Model training uses cleaned, deduplicated narratives within the training period; it does not train on every archive record. Complaint filters do not change the fixed test scores.

## How Power BI is used

The report uses Power Query M import transformations, a semantic model with 13 authored tables, three business relationships, 36 DAX measures, native visuals and interactive slicers. Desktop also generated hidden automatic date tables and their relationships.

The model embeds compact aggregate snapshots in Power Query. The 5,024 complaint count rows preserve the totals for all archive records by date, product and issue. Model and signal result tables are also embedded. The CSV copies in `data/` make these inputs inspectable; editing a CSV does not automatically change the embedded Power Query snapshot. **Refresh reloads this historical snapshot; it does not download new complaints or retrain the model.**

The original project's separate local web dashboard provides live text classification with the saved model. This Power BI report presents analytics and evaluation results. Azure and Databricks are not used by this report.

## Files

- `Financial_Complaint_Intelligence.pbix`: ready-to-open native report, including its imported data.
- `Complaint.pbip`, `Complaint.Report/`, `Complaint.SemanticModel/`: editable native project definitions. Keep these together when opening the PBIP source.
- `data/`: 13 aggregate and result CSV tables; no individual complaint narratives or complaint identifiers.
- `screenshots/`: all four pages captured from Power BI Desktop.
- `docs/USER_GUIDE.md`: navigation, filters and a short presentation walkthrough.
- `docs/DATA_AND_METHOD.md`: source, model structure and interpretation limits.
- `docs/DELIVERY_VERIFICATION.json`, `NATIVE_DAX_VERIFICATION.json`, `PBIR_VALIDATION.json`: saved-file, calculation and report-definition checks.
- `docs/MODEL_INVENTORY.json`: table columns and final DAX expressions.

The historical source is the CFPB January–February 2025 narratives archive. The source checksum and each CSV checksum are recorded in `docs/DATA_RECONCILIATION.json`. The earlier web dashboard deliverable is preserved separately as version 4.

Verified on Power BI Desktop 2.159.883.0 on this laptop. A separate-device opening test has not been performed. Public publishing and resume edits are outside this delivery.

Source validation returned zero errors and one schema-availability warning: this Desktop build saved some visuals with a Microsoft schema URL that currently returns 404. Native page rendering and all six DAX checks passed. Details are retained in the verification files.
