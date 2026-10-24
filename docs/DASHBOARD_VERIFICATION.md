# Local dashboard verification

Verified on October 24, 2026. This report describes the implemented local application, separately from the earlier design-only previews and Colab runs.

## Data and model

- The selected uncapped Logistic Regression model is loaded with its required scikit-learn version and SHA-256 verification.
- Analytics cover all 811,019 archived complaints and 265,405 written narratives.
- Portable counts consist of 5,024 date/product/issue rows; no raw narratives or identifiers are needed by the dashboard.
- Model evaluation remains fixed: 15,390 held-out complaints, 79.51% accuracy, macro-F1 0.6672.
- The historical uncapped import verification independently reproduced every test prediction and score from the saved model and original test text.

## Automated checks

The full development workspace passed **40 tests**. Checks include source/portable-model consistency, time windows, duplicate leakage, runtime restart behavior, imports, actual inference, static asset serving, date/product filtering against independent SQLite queries, issue drilldown, CSV scope/search/denominators and fixed evaluation behavior.

The test adapter emits one Starlette deprecation warning about its httpx integration. It does not affect the passing checks or the running application.

The assembled portable delivery was checked separately: **37 tests passed and 3 source-SQL comparisons skipped** because the large SQLite database is deliberately excluded. The launcher readiness check passed using the existing compatible environment. The actual packaged application was served and browser-checked without the raw database, including a real model prediction. A new dependency installation on a clean computer was not performed during this check.

## Observed browser behavior

- January credit-card filtering shows 9,073 complaints, 3,992 narratives and 31 daily observations. Model test accuracy remains 79.51%.
- The narrative chart switches to the actual 3,992-record series. Keyboard inspection of January 2 shows 127 narratives.
- Search for purchase yields three issue/product combinations. A real CSV download, sorted ascending, contains the exact counts 1, 303 and 2,775 and the selected dates.
- Empty search, clearing search, sorting and page 2 of 14 behave correctly.
- The leading credit-reporting issue opens a modal with 359,132 complaints, 83,111 narratives and all 59 daily points. Escape closes the modal.
- Selecting the February 3 signal week shows 95,532 archive-wide complaints and a baseline weekly mean of 111,340.75, with no qualifying issue flags.
- The illustrative credit-report text produces a real credit-reporting prediction with top score approximately 0.893. The ambiguous bank/payment/report example produces approximately 0.253 and a human-review recommendation.
- Short input and unrecognizable vocabulary show useful errors. Editing text clears a previous prediction.
- Model details display all 11 category reports and 121 confusion-matrix cells. Sorting by lowest F1 exposes the weaker debt/credit-management category. Selecting actual credit reporting / predicted debt collection shows 867 complaints and 10.1% of that actual category.
- Browser back/forward navigation works. Desktop (1440px), tablet (768px) and mobile (390px) layouts were inspected; the tablet/mobile pages have no page-level horizontal overflow.
- Browser error logs were empty in the inspected run.
- The browser parsed the reduced-motion rule, including important animation-name none and transition none overrides. No OS motion preference was changed during QA.

The live development server is a temporary local QA process. The delivered Start_Dashboard.cmd launcher starts the application for normal use. This report does not claim public hosting, production readiness or a Power BI implementation.
