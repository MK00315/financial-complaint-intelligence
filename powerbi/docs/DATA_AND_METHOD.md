# Data, calculations and interpretation

## Source and populations

Source: [CFPB historical narratives archive](https://www.consumerfinance.gov/foia-requests/foia-electronic-reading-room/cfpb-consumer-complaint-database-narratives-archive/), January–February 2025.

Original archive: [CCDB_Export_9_January_2025_through_February_2025.zip](https://files.consumerfinance.gov/f/documents/CCDB_Export_9_January_2025_through_February_2025.zip).

SHA-256: `11c18bb0973eed8f5e4f66e2979346af0671a3aefcb5a6b9eec73009d53cff64`.

Reporting covers 811,019 records, including 265,405 with written narratives, across 59 dates, 11 products and 135 product/issue combinations. The Power BI complaint fact table has 5,024 date/product/issue count rows. These are aggregates of all source records, not a 5,024-record sample. Counts include records without written text.

Modeling removes 3,301 narratives that are too short and 135,368 normalized duplicates, leaving 126,736 unique eligible narratives. Train: 101,935 (01 Jan–09 Feb); validation: 9,411 (10–16 Feb); test: 15,390 (17–28 Feb 2025). Normalized duplicates are removed before splitting; vocabulary fitting uses training text only. Other near-duplicates may remain.

## Semantic model

`Complaints` relates many-to-one to `Products`, `Issues` and `Calendar`, with single-direction dimension-to-fact filtering. Reporting measures sum stored counts; coverage divides written narratives by all complaints. Timely response rate divides reported timely counts by counts with known timeliness, so missing status is not silently treated as late.

Model-evaluation tables are disconnected from complaint filters. Signal tables use a separate week selector with an explicit latest-week default. Their full-archive baseline denominators are independent of complaint-page product/date filters. There are 13 authored tables and 36 measures. Desktop generated eight hidden automatic date tables; those system tables are not additional project data sources.

`MODEL_INVENTORY.json` lists the final authored DAX expressions. Each table's Power Query import reconstructs an embedded, compressed JSON snapshot and applies column types. CSV files are readable copies of the same inputs. No local absolute data path, database credentials or cloud account is required by the import queries.

## Model evaluation

Validation macro F1 selected TF-IDF + Logistic Regression (0.6572) over Complement NB (0.5043) and the majority baseline (0.0655). Fixed test accuracy is 79.51%, macro F1 0.6672 and balanced accuracy 71.85%.

Debt management has only 80 test examples and F1 0.284. The separate web classifier's 0.55 routing threshold uses uncalibrated scores: accepted-only accuracy is 86.55% at 79.00% coverage. That is not the model's overall accuracy. The report imports evaluation results; it does not retrain or run new-text inference.

## Emerging issue rules

Compare a complete Monday–Sunday week with the four preceding complete weeks. Require all four conditions: current issue count at least 30; baseline weekly mean at least 5; current volume at least 1.5 times baseline; archive-wide share increase at least 0.5 percentage points. Partial weeks are excluded.

Seven complete weeks permit three evaluations. No product/issue pair satisfies every rule in any of them. Latest evaluation: 17–23 February, with 74,507 archive complaints against a prior-four-week average of 97,562.5. A higher share alone is insufficient to qualify.

These are descriptive screening rules, not statistical significance tests or validated fraud detection. Complaints are self-selected and unverified; counts reflect reporting activity, not company failure rates or proven misconduct. The short historical period limits generalization.

## Verification boundary

The actual native report was opened and saved in Power BI Desktop. All four page captures were inspected. Six read-only native DAX queries reconciled full totals, a January credit-card selection (9,073 complaints / 3,992 narratives), fixed evaluation scope, two signal weeks, confusion-row normalization and small-class support. A native UI product selection also changed the cards to 15,286 / 6,958 while accuracy stayed fixed, then was cleared before saving.

Report definition validation and native rendering are separate checks. The PBIX container CRC and presence of an embedded DataModel were checked. No separate-device opening test or Power BI Service publishing was performed. Azure and Databricks remain separate setup items for the planned delivery project.
