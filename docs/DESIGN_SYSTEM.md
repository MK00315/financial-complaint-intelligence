# Financial Complaint Intelligence - dashboard design system

## Primary style source

The interface uses a light sky-blue palette, thin dividers, white panels and compact horizontal navigation. Reporting stays visually quiet so totals, trends and issue comparisons receive attention. The initial layout exploration used Superdesign; the implemented screens use the project-specific styles and interactions documented here.

## Product and audience

Financial Complaint Intelligence is a browser dashboard for complaint analysts and a student portfolio demonstration. It connects real SQL analytics with a verified text classifier. The primary task is inspecting complaint reporting patterns, exploring issues and getting a reviewable product-category suggestion from complaint text.

The four implemented views are Overview, Issue explorer, Classify complaint, and Model & Data.

## Identity and typography

- Identity: the text wordmark `Financial Complaint Intelligence`. No logo or brand assets have been supplied.
- Headings: Space Grotesk, 500-600, with restrained tracking. Screen heading 28px, section headings 17-19px.
- Body: Inter or the matching system sans-serif fallback, 14px with 1.5 line height.
- Numeric values: tabular numerals, 30-34px for KPI values, 13-14px for tables.
- Small metadata: JetBrains Mono sparingly at 10-11px; ordinary labels remain readable sans-serif.
- Font weights: 400 body, 500 controls, 600 emphasis.

## Color tokens - user-requested sky blue

- Canvas: #F3F9FE, a very pale sky-blue white.
- Surface and navigation: #FFFFFF.
- Primary text: #16324F.
- Muted text: #566F85.
- Bright sky accent: #0EA5E9; use for chart strokes, icons and decorative emphasis.
- Primary action: #0369A1 with white text for readable button contrast.
- Primary action hover: #075985.
- Soft sky fill: #E0F2FE.
- Lightest sky: #F0F9FF.
- Border: #D8EAF7.
- Grid lines: #EAF3FA.
- Amber for uncertainty: #A96C13 with #FFF7E6 surface.
- Charts: sky-blue primary stroke, pale blue area, slate-blue secondary labels. Use text alongside color.
- Large dark sidebar panels and the old teal/green palette are not part of this revision.

## Layout and components - refined wider workspace

- Desktop design: 1440px wide, centered content about 1280px wide.
- Use a compact white horizontal top navigation with text project identity and four sections: Overview, Issue explorer, Classify complaint, Model and data. Overview is selected.
- A spacious heading/context row and a unified date/product/action toolbar precede four KPI cards.
- A 12-column content grid allocates about eight columns to the daily-volume chart and four to product mix. The volume chart should be less vertically stretched than the first design.
- A readable issues table and a concise weekly-signals panel follow; reduce unused empty space while keeping scanability.
- Spacing scale: 4, 8, 12, 16, 24, 32, 40px.
- Cards: white surfaces, 10-12px radii, thin cool-blue borders and subtle low-opacity shadows. The first KPI may use a soft pale-blue surface.
- KPI values: 30-34px, tabular numerals, clear labels. Small icon accents are sky blue.
- Primary buttons: deep accessible sky blue, white text, 40px height, 8px radius.
- Responsive behavior: navigation condenses to a readable horizontal or mobile control, metric cards wrap, charts stack, table scrolling is contained.
- Accessibility: readable contrast, visible focus and descriptive controls.

## Motion

- Purposeful 150-250ms transitions for hover, selection, filters, panel entry and navigation.
- Gentle one-time content entrance with at most a small stagger. Keep final metric values readable immediately.
- No looping decorative movement, fake live updates, simulated activity or randomly fluctuating numbers.
- Respect prefers-reduced-motion. Preserve chart axes during transitions.

## Exact evidence and copy

Use `docs/VERIFIED_DASHBOARD_CONTENT.json` as the sole data source for displayed values and chart points.

- Historical observation window: January 1-February 28, 2025.
- All archived complaints: 811,019.
- Narratives: 265,405, representing 32.72% of archived complaints.
- Product categories: 11.
- Selected uncapped Logistic Regression model: test accuracy 79.51%, macro-F1 0.6672, based on 15,390 held-out test complaints.
- Training size: 101,935 eligible narratives. This differs from the all-record analytics population.
- Latest complete signal week: February 17-23, 2025. Zero issues meet the rule. Show a professional empty state instead of invented alerts.
- Model evaluation is fixed to the held-out test set and does not change with complaint filters.
- Complaint counts represent reporting activity, not company failure rates or proven misconduct.

## Overview content structure

1. Header: `Complaint overview`, short analytical subtitle, historical snapshot badge, observed date range, product filter and `Classify a complaint` action.
2. KPI row: Total complaints 811,019; Narrative coverage 32.72% with `265,405 written complaints`; Product categories 11; Test accuracy 79.51% with a distinct `Model` label and held-out scope.
3. Complaint volume: actual daily series from the evidence file, labeled axes and dates, sky-blue line/area on a white surface.
4. Product mix: five actual leading product groups plus an explicitly computed `Other products` group; show counts and shares of 811,019.
5. Top reported issues: actual leading issue labels, their source product category and counts. No invented change percentages or sparklines.
6. Weekly signals: `No issues crossed the signal thresholds` with the latest complete week and a small explanation of comparison against four preceding complete weeks.
7. Data/source footer: CFPB historical complaint archive, January-February 2025; link/entry to Model and data for limitations.

The interface should feel like a finished analytical workspace. Source provenance belongs in concise, useful labels, without implementation/debug details in the main user flow.
