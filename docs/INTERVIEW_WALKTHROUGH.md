# Interview walkthrough

## The business problem

An analyst cannot manually read every written complaint immediately. This project organizes complaints by financial product and surfaces reporting patterns that deserve inspection. A model suggests categories; an analyst remains responsible for interpretation.

## The data flow

The pipeline downloads one fixed official archive and checks its SHA-256 hash. It streams the CSV into SQLite and exports real business metrics using SQL. Modeling uses only sufficiently long written complaints and keeps repeated normalized text once. TF-IDF transforms the text into numeric features, the models are compared on validation data, and the selected classifier is evaluated on a later test period. The exported results provide the model and actual dashboard data.

## Terms in plain language

- **TF-IDF:** describe a complaint using weights for words and pairs of words. Words useful for distinguishing complaints receive more weight than words repeated everywhere.
- **Baseline:** a deliberately simple reference that always predicts the most common training category. A useful model should improve on it.
- **Precision:** among complaints predicted as a category, how many actually have that source label?
- **Recall:** among complaints actually labeled as that category, how many did the model find?
- **F1:** a combined precision/recall score.
- **Macro-F1:** average F1 with equal importance for every category, so the largest category cannot dominate the score.
- **Chronological split:** train on earlier complaints and test on later ones to resemble future use more closely than a random split.
- **Leakage:** information that would not legitimately be available to the model, such as labels, future responses or copied complaints in both training and testing.
- **Review threshold:** a chosen score cutoff below which a complaint is sent for manual review. More automatic coverage can come with more mistakes.

## Questions you should answer

1. Why are there more analytics records than modeling records? Not every complaint has narrative text, some are too short and normalized duplicates are excluded from modeling.
2. Why not report accuracy alone? The categories are imbalanced. A model can look accurate by favoring the largest class while missing smaller classes.
3. How did you select the model? By validation macro-F1, before looking at test results.
4. Does this eliminate every duplicate? No. Normalized identical templates are excluded; other near-duplicates and paraphrases may remain.
5. Is a 0.9 score a 90% guarantee? No. These are uncalibrated model scores; coverage and actual accepted-case accuracy must also be evaluated.
6. What is an emerging issue? A category/issue meeting explicit count, relative-growth and share-growth thresholds against four complete prior weeks. It is an investigation signal, not proof of wrongdoing.
7. Why is timeliness not response duration? The source supplies a yes/no timely-response flag. The project does not invent a closure timestamp or calculate an unsupported duration.
8. Does a company with more complaints perform worse? This dataset lacks market-share and customer-exposure denominators. Complaint volume alone cannot establish that.
9. What did you run in Colab? Answer using the exported execution_environment and profile. A local smoke run is not a full Colab run.
10. What would improve the project? More time coverage, stronger near-duplicate grouping, externally verified labels, calibrated scores, broader validation and monitored human-review workflows.

## Demonstration order

1. Explain the source and observation dates.
2. Show real SQL-based complaint trends and denominators.
3. Show the weekly signal result, its rule/baseline and the absence of qualifying issues.
4. Classify an authored example and explain the score and review route.
5. Show model comparison, chronological split, held-out results and one limitation.

Use docs/DASHBOARD_USER_GUIDE.md for the concrete demonstration sequence, including the 9,073-record January credit-card selection, an actual model prediction and the human-review example. The Power BI report is included under powerbi/ with four native report pages and verified DAX results. Use README for the current public demo link and hosting status. Explain the Python web app and Power BI report as separate interfaces over the same verified historical results.
