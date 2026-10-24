# Using and presenting the Power BI report

1. Open `Financial_Complaint_Intelligence.pbix`. Choose the bottom **Overview** tab if necessary. The default totals are 811,019 complaints and 265,405 written narratives.
2. Open the Product dropdown and select **Credit card**. For the full date range, totals become **15,286 complaints** and **6,958 narratives**. The test accuracy stays **79.51%** because evaluation is separate from reporting filters. Uncheck Credit card to return to all products.
3. Change the received-date range to examine a shorter period. Dates are displayed according to the report's US locale. The date range is inclusive. Restore **1/1/2025–2/28/2025** after exploring.
4. Open **Issue Explorer** using the bottom tab. Its product, issue and date slicers control that page. Select a table row to focus the other visuals, then click it again to clear the selection. Scroll inside the table for further issues. Overview and Issue Explorer slicers are independent.
5. Open **Emerging Issues**. With no single week selected, measures use **17–23 February 2025**, the latest complete week. Select 03 or 10 February to inspect an earlier week. The week volume and baseline change; the archive-wide signal calculation is independent of complaint-page filters. A rank or positive share change alone is not a flag.
6. Open **Model & Data**. Read the model score together with macro F1 and the per-class chart. The matrix shows percentages of each actual product row; displayed rounding may prevent a row from adding to exactly 100.0%. Codes below the matrix identify predicted products.

Header navigation buttons use **Ctrl+click** in Desktop editing mode. Bottom tabs use a normal click. Hover charts for native tooltips. Scroll within long tables and bar charts to see all categories. If needed, use **View → Page view → Fit to page**.

## A short demonstration

- Explain that this is a historical CFPB snapshot, with all-record reporting and a separate narrative classification model.
- Show Overview totals and one product filter. Explain why the model score stays fixed.
- Use Issue Explorer to identify a high-volume product/issue pair, then discuss narrative availability and reported response timeliness.
- Show the Emerging Issues rules and the honest result: no issue qualifies in any evaluable week. Explain that increasing share can coexist with falling volume.
- Finish with Model & Data: validation selected Logistic Regression; the chronological test set was held out; macro F1 and the small debt-management category reveal limitations that accuracy alone hides.

To classify new text, use the separate version-4 web dashboard's **Classify Complaint** page. The Power BI report does not execute the Python classifier.
