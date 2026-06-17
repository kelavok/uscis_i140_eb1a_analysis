# EB1A / E11 Research Export Pack

This folder contains exported charts from the local EB1A / E11 trend analysis. The charts are based on local CSV exports from the USCIS PostgreSQL project, not on live USCIS web access.

## Data Sources

- `data/analysis_tables/eb1eb2_total_radp.csv`
  - Quarterly RADP-style data for `TOTAL`, `EB1`, `E11`, `EB2`, and `NIW`.
  - Coverage: FY2022 through FY2026 Q1.
  - Main use here: direct E11 / EB1A quarterly flow and rate analysis.
- `data/analysis_tables/i140_yearly_total_eb1_eb2_snapshots.csv`
  - Yearly current-status snapshots for `TOTAL`, `EB1`, and `EB2`.
  - Main use here: EB1 proxy context and scenario forecasting.
- `data/exports/i140_status_counts.csv` plus dimension tables
  - Normalized fact and dimension exports.
  - Main use here: reconstructing EB1 snapshot-to-snapshot changes from FY2025 Q4 to FY2026 Q1.

## Research Question

The working question is whether the EB1A / E11 adjudication environment became materially less favorable in FY2025 and FY2026 Q1, and whether recent pending inventory is likely to resolve into denials at a higher rate than earlier periods.

## Key Notes Before Reading the Charts

- `E11` is EB1A / Aliens with Extraordinary Ability.
- `EB1` is broader than E11 and also includes E12 and E13.
- Direct E11 quarterly data exists from FY2022 through FY2026 Q1 in the RADP-style table.
- Direct E11 cohort-level pending conversion is not observable in the current dataset.
- EB1 is used only as a proxy for pending-resolution behavior.
- `pending` in RADP should be read as inventory/current status, not as a clean same-quarter cohort flow.
- FY2026 currently means FY2026 Q1 only.

## Chart Guide

### [01_e11_quarterly_flows.png](01_e11_quarterly_flows.png)

**What it shows:** E11 quarterly received, approved, and denied counts.

**Why it matters:** Shows the direct EB1A flow signal from FY2022 through FY2026 Q1. The key visual question is whether denials rise while approvals weaken.

### [02_e11_pending_inventory.png](02_e11_pending_inventory.png)

**What it shows:** E11 pending inventory.

**Why it matters:** Shows that pending inventory rose sharply into FY2025/FY2026. This supports the idea that fresh quarters cannot be read only through approvals and denials.

### [03_e11_denial_rates.png](03_e11_denial_rates.png)

**What it shows:** E11 quarterly denial rates.

**Why it matters:** Compares denial rate on received basis and decided basis. The decided-basis line is cleaner for adjudication severity because it excludes pending from the denominator.

### [04_e11_q1_rate_comparison.png](04_e11_q1_rate_comparison.png)

**What it shows:** E11 Q1 comparison across FY2022-FY2026.

**Why it matters:** FY2022-FY2025 Q1 denied/decided stays near 25-27%, while FY2026 Q1 jumps to 52.5%. Approval/received also falls to 28.1% in FY2026 Q1. This is the strongest like-for-like seasonal check.

### [05_e11_annual_denial_share.png](05_e11_annual_denial_share.png)

**What it shows:** Annual E11 decided-basis denial share.

**Why it matters:** Aggregates quarterly E11 outcomes by fiscal year. FY2026 is marked as Q1 only and should not be treated as a full-year result.

### [06_eb1_pending_resolution_proxy.png](06_eb1_pending_resolution_proxy.png)

**What it shows:** EB1 proxy pending-resolution transition.

**Why it matters:** Between FY2025 Q4 and FY2026 Q1 snapshots, the EB1 FY2025 cohort had 2,617 additional approvals and 2,455 additional denials; the denial share of newly resolved outcomes was 48.4%. For EB1 FY2024 the comparable share was 22.1%.

### [07_eb1_proxy_forecast_scenarios.png](07_eb1_proxy_forecast_scenarios.png)

**What it shows:** EB1 proxy scenario forecast.

**Why it matters:** Stress-tests final denial share under optimistic, observed-base, and pessimistic pending-to-denial assumptions. This is a proxy model, not a direct E11 cohort forecast.

## Numeric Anchors

### E11 Q1 Like-for-Like Comparison

- FY2022 Q1: approved/received 56.8%; denied/received 20.1%; denied/decided 26.1%.
- FY2023 Q1: approved/received 68.4%; denied/received 23.8%; denied/decided 25.8%.
- FY2024 Q1: approved/received 62.2%; denied/received 22.7%; denied/decided 26.7%.
- FY2025 Q1: approved/received 43.8%; denied/received 14.8%; denied/decided 25.3%.
- FY2026 Q1: approved/received 28.1%; denied/received 31.1%; denied/decided 52.5%.

### Annual E11 Summary

- FY2022: decided-basis denial share 22.2%; pending at last observed quarter 6,281.
- FY2023: decided-basis denial share 28.6%; pending at last observed quarter 7,657.
- FY2024: decided-basis denial share 27.8%; pending at last observed quarter 10,586.
- FY2025: decided-basis denial share 33.1%; pending at last observed quarter 21,157.
- FY2026 Q1 only: decided-basis denial share 52.5%; pending at last observed quarter 24,653.

### EB1 Pending-Resolution Proxy

- EB1 FY2024 cohort, FY2025 Q4 to FY2026 Q1 snapshot transition: approval increase 558; denial increase 158; denial share of newly resolved outcomes 22.1%.
- EB1 FY2025 cohort, FY2025 Q4 to FY2026 Q1 snapshot transition: approval increase 2,617; denial increase 2,455; denial share of newly resolved outcomes 48.4%.

## Main Interpretation

The direct E11 data supports the hypothesis that the EB1A environment worsened in FY2025 and especially FY2026 Q1. The strongest direct evidence is the Q1 like-for-like comparison: approval/received drops sharply from FY2024 Q1 to FY2026 Q1, while FY2026 Q1 denial pressure is much higher.

The EB1 proxy adds a second signal: between the FY2025 Q4 and FY2026 Q1 snapshots, newly resolved EB1 FY2025 outcomes were split much more negatively than the comparable FY2024 transition. This is not exact E11 pending conversion, but it is directionally consistent with the hypothesis that FY2025 pending inventory may resolve with elevated denial share.

## Caveats

- The package does not prove that FY2026 Q1 denials came from FY2025 RFE cases; RFE status is not present in the aggregate USCIS files.
- EB1 proxy results can be distorted by E12 and E13 behavior.
- Snapshot transitions can include USCIS reporting revisions, not only true adjudication changes.
- FY2026 Q1 should not be annualized mechanically.
- Pending inventory should not be treated as if it were a clean received cohort.

## Rebuild

Run this from the project root to regenerate the package:

```powershell
python scripts\export_eb1a_research_package.py
```
