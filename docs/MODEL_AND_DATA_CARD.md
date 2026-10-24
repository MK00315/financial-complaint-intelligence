# Model and data card

## Intended task

Suggest a financial product category from a written consumer complaint, supporting an analyst's manual review. Identify changes in reported issue volume using transparent descriptive rules.

This model does not provide financial advice, verify complaint allegations, determine compensation or make credit decisions.

## Source and population

The source is the official CFPB narratives archive for January-February 2025. The verified raw archive has 811,019 rows and 265,405 rows with written narrative text. reports/data_manifest.json records the source URL, fixed SHA-256 checksum, row counts and cleaning rules.

The analytics population includes all archived records. The classifier uses only narratives with at least 12 normalized words, then keeps the earliest normalized text once. These populations have different selection effects. Complaints and narratives are self-selected, unverified and not representative of all consumers. Company size and exposure are not measured; complaint counts are not failure rates.

## Modeling design

- Input: complaint narrative text only. Product labels, issues, company responses, timeliness flags and other post-submission metadata are not input features.
- Target: the source-provided product category. These labels reflect the consumer's selection, not an independent expert adjudication.
- Cleaning: lowercase; remove URLs, email addresses, digits, redaction markers and punctuation; retain complaint words.
- Deduplication: one earliest narrative per normalized text hash. Templates varying only in removed identifiers are grouped. Other paraphrases and near-duplicates may remain.
- Split: train through February 9; validate February 10-16; test February 17-28, 2025.
- Category scope: at least 20 unique training examples; excluded-row counts are exported.
- Training: profile-specific deterministic per-category caps; the selected uncapped run uses all eligible training-window narratives. TF-IDF vocabulary is learned only on training text.
- Models: majority baseline, Complement Naive Bayes, Logistic Regression.
- Selection: validation macro-F1 among the two useful classifiers; the baseline is retained for comparison.
- Test: evaluated after model and review-threshold selection; test results do not choose the model.

## Profiles

Smoke caps training at 250 and each evaluation partition at 80 records per category. It is a pipeline verification profile, not a population performance claim.

Full is the preserved capped profile: training is limited to 15,000 records per category, giving 60,444 training records in this dataset. Uncapped uses every eligible training-window narrative: 101,935 records. Neither larger profile caps validation or test records; both use the same 9,411 validation and 15,390 test complaints. Their membership fingerprints are verified before uncapped training. They evaluate retained, unique, narrative-bearing complaints and do not represent every consumer or every complaint.

The capped and uncapped runs were completed in Colab and their exports were returned and verified. The notebook embeds the capped metrics and holdout fingerprints in reference/capped_full_reference.json. The uncapped experiment changes the training cap while retaining the data source, cleaning rules, windows, feature limits and classifier settings. The profile recommendation uses validation macro-F1 only, with ties preserving the capped model. Test results are reported after that decision. The selected uncapped run has 79.51% test accuracy and 0.6672 test macro-F1. All 15,390 saved predictions and scores were reproduced from the original held-out text and model in the development workspace.

## Human-review demonstration

Search thresholds on validation data for at least 85% accepted-case accuracy, at least 10% coverage and at least 20 accepted examples. Choose the highest validation coverage satisfying those constraints. If none qualifies, record that the target was not met and use a conservative demonstration threshold of 0.9.

Scores are uncalibrated. The validation target is not a guarantee for the test set, new periods or arbitrary input. Report test coverage and accepted-case accuracy alongside overall metrics. The input checks are basic validation, not a validated out-of-distribution detector.

## Emerging-issue rules

Compare the last complete week with four prior complete weeks. An issue must have at least 30 current-week complaints, a baseline weekly mean of 5, volume at least 1.5 times baseline, and an increase of at least 0.5 percentage points in its share of all complaints.

Only seven complete weeks are available. There is no claim of statistical significance, seasonal adjustment, causal diagnosis or verified misconduct. New issues with little baseline history may not satisfy the minimum-history rule.

## Reproducibility and portability

The results include deterministic split membership, model checksum, package versions, profile and actual execution environment. The exported pipeline includes the vectorizer and classifier. It references normalize_text in complaint_project.py, so keep that module beside the local application. Only deserialize joblib files that you generated or trust.

## Evidence boundary

Read reports/<profile>/metrics.json for actual results. The smoke profile is local pipeline verification; the larger capped and uncapped profiles are verified Colab executions. The sky-blue dashboard is implemented and browser-checked. The separate Power BI report is saved, visually reviewed and reconciled with native DAX queries. Current public hosting verification is separate from those earlier local and training checks; see README and docs/DEPLOYMENT.md.
