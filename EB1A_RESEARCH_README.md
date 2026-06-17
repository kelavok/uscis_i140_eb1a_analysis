# EB1A / E11 Research README

## Purpose

This research analyzes USCIS I-140 data to understand whether the EB1A / E11 adjudication environment has become less favorable in recent fiscal years, especially FY2025 and FY2026 Q1.

The main focus is the trend in:

- E11 receipts;
- E11 approvals;
- E11 denials;
- E11 pending inventory;
- approval and denial rates;
- proxy pending-conversion behavior using EB1 current-status snapshots.

The practical goal is to estimate whether recent pending inventory is likely to resolve into approvals or denials at historical rates, or whether a more negative forecast is justified.

## Main Hypothesis

The working hypothesis is:

1. EB1A / E11 denial pressure increased in FY2025 and became especially visible in FY2026 Q1.
2. Many denials appearing in FY2026 Q1 may correspond to older pending/RFE-affected cases rather than only petitions received in FY2026 Q1.
3. If approvals tend to arrive faster than RFE-heavy or denial-prone cases, then a drop in Q1 approval share combined with high pending inventory may be an early warning signal.
4. Pending inventory from FY2025 may eventually resolve into denials at a higher rate than earlier historical cohorts.

The data cannot directly observe RFE events, so the RFE mechanism is treated as an interpretation to test indirectly, not as an observed variable.

## Data Used

The analysis uses local CSV exports generated from the project's PostgreSQL database.

### Main Analysis Tables

`data/analysis_tables/eb1eb2_total_radp.csv`

This is the main quarterly RADP-style table. It includes:

- `TOTAL`
- `EB1`
- `E11`
- `EB2`
- `NIW`

Coverage:

- FY2022 through FY2026 Q1
- quarterly rows
- `received`, `approved`, `denied`, `pending`

This is the primary table for direct E11 / EB1A flow analysis.

`data/analysis_tables/i140_yearly_total_eb1_eb2_snapshots.csv`

This is the yearly current-status table. It includes:

- `TOTAL`
- `EB1`
- `EB2`

Coverage:

- `historic`: FY2009-FY2025, using the latest available yearly snapshot for each cohort year;
- `actual`: FY2026 Q1, using RADP Q1 data.

This table is useful for high-level annual context but does not provide direct E11 cohort conversion.

### Raw Fact Tables

`data/exports/i140_status_counts.csv`

Used with dimension tables to reconstruct current-status snapshots and estimate EB1 pending conversion.

Supporting dimension/source tables:

- `source_files.csv`
- `preference_categories.csv`
- `case_statuses.csv`
- `countries.csv`

## Important Data Limitation

Direct E11 pending conversion is not observable in the current USCIS files.

The quarterly RADP table gives:

- E11 quarterly received;
- E11 quarterly approved;
- E11 quarterly denied;
- E11 pending inventory at the end of the quarter.

But it does not track a specific E11 pending cohort from one snapshot to the next.

Therefore:

- direct E11 analysis uses quarterly flows and pending stock;
- pending-conversion analysis uses EB1 as a proxy, because EB1 has full current-status snapshots over time.

This distinction is central. E11 flow analysis and EB1 pending-conversion proxy should not be presented as the same measurement.

## Analysis Notebook

Main notebook:

`eb1a_trend_analysis.ipynb`

The notebook contains:

1. Data loading and setup.
2. E11 quarterly flow analysis.
3. E11 approval and denial rate analysis.
4. E11 annual aggregation from quarterly RADP.
5. Q1 comparison across FY2024, FY2025, and FY2026.
6. EB1 proxy pending-conversion analysis.
7. Scenario forecast using EB1 pending-resolution behavior.
8. Final interpretation and caveats.

## Step-by-Step Method

### Step 1. Load Local Analysis Tables

The notebook loads:

- `eb1eb2_total_radp.csv`
- `i140_yearly_total_eb1_eb2_snapshots.csv`
- `i140_status_counts.csv`
- dimension tables

No web access is required.

### Step 2. Build E11 Quarterly Metrics

For E11, calculate:

- `decided = approved + denied`
- `approval_received = approved / received`
- `denial_received = denied / received`
- `approval_decided = approved / (approved + denied)`
- `denial_decided = denied / (approved + denied)`

These metrics are calculated quarterly.

### Step 3. Plot E11 Quarterly Flows

Charts:

- E11 `received`, `approved`, `denied` by quarter;
- E11 `pending` by quarter.

Pending is plotted separately because it is a stock, not a flow.

### Step 4. Compare Approval and Denial Rates

The notebook plots:

- received-basis approval and denial rates;
- decided-basis approval and denial rates.

Decided-basis denial rate is treated as the cleaner measure of adjudication strictness among completed decisions.

### Step 5. Aggregate E11 by Fiscal Year

For FY2022-FY2025:

- sum quarterly received;
- sum quarterly approved;
- sum quarterly denied;
- take year-end pending from Q4.

FY2026 is treated as Q1-only, not a full year.

### Step 6. Compare Q1 Across Years

The notebook compares E11 Q1 for:

- FY2024;
- FY2025;
- FY2026.

This is a strong simple test because it compares the same fiscal quarter across years.

### Step 7. Estimate Pending Conversion with EB1 Proxy

The notebook reconstructs EB1 current-status snapshots from raw fact exports.

For consecutive snapshots, it computes:

- `pending_drop = pending_t - pending_t+1`
- `approved_inc = approved_t+1 - approved_t`
- `denied_inc = denied_t+1 - denied_t`
- `denied_share_resolved = denied_inc / (approved_inc + denied_inc)`

This provides an EB1-level proxy for how pending inventory is resolving.

### Step 8. Scenario Forecast

Because direct E11 pending conversion is unavailable, the forecast uses EB1 proxy behavior.

Scenarios:

- optimistic: 35% of remaining pending resolves as denial;
- base: observed EB1 FY2025 pending-resolution split from FY2025 Q4 to FY2026 Q1;
- pessimistic: 55% of remaining pending resolves as denial.

The forecast is directional, not deterministic.

## Key Preliminary Findings

### E11 Denial Share Increased

Annual E11 decided-basis denial share:

- FY2022: about 22%
- FY2023: about 29%
- FY2024: about 28%
- FY2025: about 33%
- FY2026 Q1 only: about 53%

FY2026 is partial-year, but the Q1 signal is unusually negative.

### Q1 Comparison Supports Worsening Hypothesis

E11 Q1 approval/received:

- FY2024 Q1: about 62%
- FY2025 Q1: about 44%
- FY2026 Q1: about 28%

E11 Q1 denial/received:

- FY2024 Q1: about 23%
- FY2025 Q1: about 15%
- FY2026 Q1: about 31%

On a decided basis, FY2026 Q1 E11 has more denials than approvals.

### Pending Inventory Increased

E11 pending:

- FY2024 Q4: 10,586
- FY2025 Q4: 21,157
- FY2026 Q1: 24,653

This is consistent with increased backlog or slower resolution, but the data does not directly identify RFE.

### EB1 Proxy Shows High Denial Share Among Newly Resolved FY2025 Pending

For EB1 FY2025, from the FY2025 Q4 report to the FY2026 Q1 report:

- pending dropped by about 5,044;
- approvals increased by about 2,617;
- denials increased by about 2,455;
- denial share among newly resolved EB1 pending was about 48%.

This is a strong negative proxy signal.

## Interpretation

The direct E11 flow data and EB1 pending-resolution proxy point in the same direction:

- FY2025 looks worse than FY2022-FY2024;
- FY2026 Q1 looks substantially worse than prior Q1 periods;
- pending inventory is elevated;
- recent pending may be resolving into denials at a higher rate than earlier historical expectations.

This supports the hypothesis of a worsening EB1A adjudication environment, but the conclusion must remain cautious because exact E11 cohort pending conversion is not directly observable.

## Caveats

- FY2026 contains only Q1 and should not be annualized mechanically.
- RFE is not directly observed.
- EB1 is a proxy for E11, not an exact substitute.
- USCIS revises historical counts, so snapshot deltas can include reporting corrections.
- Pending is a stock, not a quarterly flow.
- Some rates on received basis can look strange when pending is very large.

## Recommended Next Work

1. Repeat the same analysis for NIW.
2. Add confidence intervals around E11 decided-basis denial rates.
3. Backtest EB1 proxy forecasts using older cohorts.
4. Compare E11 with E12/E13 if reliable subcategory data becomes available.
5. Keep FY2026 marked as partial-year/Q1-only in all charts.
6. Re-run the notebook when FY2026 Q2 data is added.
7. Build a dashboard view with E11, EB1, EB2, NIW, and proxy forecast metrics.

