# Dashboard quick guide

Extract the complete project folder and double-click **Start_Dashboard.cmd**. Keep the console open. The browser opens **http://127.0.0.1:8765**. Press **Ctrl+C** in the console when finished. No Colab rerun is needed. Another computer needs Python 3.12/3.13 and internet for its first dependency setup.

## Demonstration order

1. **Overview:** show 811,019 records and 32.72% narrative coverage. Hover a chart point, or focus the chart and use arrow keys.
2. Select **Credit card**, open **Date range**, and set the end date to **January 31, 2025**. The count becomes **9,073**; the separate model test accuracy stays **79.51%**. Reset the filters.
3. **Issue explorer:** search **purchase**, change the sort and export CSV. Clear the search and open an issue to inspect its daily trend.
4. **Weekly signals:** select a historical week and expand the rules. No issues crossed the chosen thresholds. These checks use the archive-wide population independently of date/product filters.
5. **Classify complaint:** load **Credit report**, then click **Classify complaint**. The saved model suggests credit reporting with an uncalibrated score around **0.893**. This illustrative example is separate from evaluation.
6. To demonstrate review, enter: “I contacted the bank about money taken from my account after a payment and a loan collection problem, but the company has not explained the charges or corrected my credit report.” The checked model returns a score around **0.253**, below the **0.55** review threshold.
7. **Model & Data:** explain the chronological splits and validation-based selection. Sort by lowest F1 to acknowledge weaker smaller categories. Switch the confusion matrix between percentages and counts and select a cell.

## Interpretation

- Navigation supports browser back/forward. Date/product selections persist across views and appear in the URL.
- Search matches issues and products. Shares use the entire selected date/product population before search; small nonzero shares display as **<0.1%**.
- Classification text is not saved. Clear text removes the input and result. Scores are not guaranteed probabilities; every suggestion can be reviewed.
- Tables scroll inside their cards on small screens, and navigation scrolls horizontally. Reduced-motion preferences disable animations.
- Counts do not establish company failure rates, complaint validity or proven misconduct.

## Troubleshooting

- **Cannot connect:** keep the launcher console open or run Start_Dashboard.cmd again.
- **First setup is slow:** dependencies are being installed locally. This does not train a model or download the complaint dataset.
- **Version error:** use the launcher or pinned requirements instead of an unrelated Python environment.
- **Missing files:** extract the whole ZIP. Keep dashboard, models, reports and Python files together.
- **CSV scope:** its dates and product selection are included in each row. It contains aggregate counts, not narratives.
