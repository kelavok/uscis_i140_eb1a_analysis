# Data Quality Notes and Known Issues

This file records what should be kept in mind before using the current PostgreSQL data for analysis.

Short version: the database is usable for exploratory analysis, but it is not a fully audited official dataset. I did not manually verify every extracted row. I verified the parser structure, database counts, coverage, and several high-value spot checks against local source files.

## What Was Actually Verified

Verified mechanically:

- The local parser ran against `data/raw/raw_by_hands`.
- The load SQL completed successfully into PostgreSQL `uscis_analysis`.
- Duplicate file hashes were skipped.
- CSV/XLSX files were preferred over same-stem PDFs.
- Source, sheet, raw-cell, dimension, and fact row counts were checked in the database.
- The Python source compiles successfully with `python -m compileall -q src`.

Spot-checked against source values:

- `quarterly_all_forms_fy2025_q4_v1.xlsx`, I-140 Q4:
  - received `66,692`
  - approved `48,882`
  - denied `8,710`
  - pending `180,439`
  - YTD received `244,843`
  - YTD approved `152,640`
  - YTD denied `24,817`
  - YTD pending `180,439`
- `Quarterly_All_Forms_FY2021Q4.csv`, I-140 Q4:
  - received `48,527`
  - approved `48,974`
  - denied `1,896`
  - pending `88,970`
  - YTD received `179,350`
  - YTD approved `137,073`
  - YTD denied `9,189`
  - YTD pending `88,970`
- `Quarterly_All_Forms_FY2021Q1.pdf`, I-140 Q1:
  - received `26,032`
  - approved `25,166`
  - denied `2,667`
  - pending `47,096`
- `Quarterly_All_Forms_FY2020Q2.pdf`, I-140 Q1/Q2:
  - Q1 received `33,077`
  - Q1 approved `30,578`
  - Q1 denied `2,683`
  - Q1 pending `45,078`
  - Q2 received `25,833`
  - Q2 approved `29,977`
  - Q2 denied `3,064`
  - Q2 pending `40,428`
- `Quarterly_All_Forms_FY2019Q4.pdf`, I-140 Q1-Q4 groups were checked against the extracted PDF text.
- `I140_FY22_Q4_REC_COB.csv`, India NIW:
  - received `1,185`
- `I140_FY22_Q4_App_COB.csv`, India NIW:
  - approved `682`
- `I140_rec_by_class_country_FY2020_Q1_Q2.pdf`, All Countries TOTAL FY2020:
  - received `60,170`
  - approved `37,488`
  - denied `1,143`
  - pending_other `21,539`

## Current Coverage by Report Family

| Report family | Min FY | Max FY | Loaded sources | Notes |
|---|---:|---:|---:|---|
| `all_forms` | 2017 | 2025 | 36 | Broadest consistent quarterly I-140 received/approved/denied/pending series. |
| `preference_country` | 2019 | 2025 | 19 | I-140 country/preference/current-status reports. Coverage is not every quarter. |
| `fy_quarter_status` | 2022 | 2025 | 15 | I-140 by fiscal year, quarter, and status. |
| `country_category` | 2022 | 2023 | 9 | Country/category receipt or approval reports, depending on file name. |

There are no local files detected with `2026`, `FY26`, or `FY2026` in the file name. The current loaded maximum is FY2025.

## Known Coverage Gaps

### No FY2026 Data Loaded

The user mentioned 2017-2026, but the local folder currently has no detected FY2026 file names. The database therefore does not contain FY2026 sources.

### `all_forms` FY2017-FY2025 Is Now Continuous by Quarter

After adding `Quarterly_All_Forms_FY2020Q2.pdf`, the all-forms I-140 quarterly series has at least one local source for every fiscal quarter from FY2017 Q1 through FY2025 Q4.

Older all-forms PDFs can include cumulative quarter groups inside one report. For example, an FY2020 Q2 report contains Q1 and Q2 columns. The database stores those rows with the source file's `report_quarter = 2`, while the actual period is in `period_quarter`.

### `preference_country` and `fy_quarter_status` Are Not Continuous from 2017

The most continuous 2017-2025 source is `all_forms`, but it is form-level and does not contain EB category/country detail.

More detailed I-140 category/country reports begin later:

- `preference_country`: loaded from FY2019-FY2025, not every quarter.
- `fy_quarter_status`: loaded from FY2022-FY2025.
- `country_category`: loaded from FY2022-FY2023.

So, there is no complete 2017-2025 quarterly country/category panel in the current local files.

## Parsing Assumptions

### `snapshot_date`

For local files, `snapshot_date` is currently inferred as fiscal quarter end:

- FY Q1: December 31 of the prior calendar year
- FY Q2: March 31
- FY Q3: June 30
- FY Q4: September 30

This is not the same as USCIS publication date and not the same as the user's manual download date.

This is good enough for ordering snapshots by reporting period, but not good enough if the analysis needs precise publication lag or exact date of data availability.

### Local Source URLs

Because the current workflow is local-only, `source_url` values for manually collected files use `local_hand://filename` pseudo-URLs. The real USCIS URL is not preserved unless it exists elsewhere in source metadata.

### Country Codes

Only `ALL` is a semantic code. Other `country_code` values are normalized labels, not authoritative ISO codes. Example: a country label is uppercased and stripped into a database-safe code.

Before serious country-level reporting, add ISO normalization or a reviewed country mapping table.

### Form Codes

All-forms parsing infers form codes from the first column. It handles common USCIS footnote artifacts, but form-code extraction should be reviewed for obscure forms before using non-I-140 form data seriously.

The I-140 all-forms row has been spot-checked more carefully than other forms.

### EB Category Mapping

Category mapping uses labels and, for some country/category CSV formats, column position fallback:

`E11`, `E12`, `E13`, `E21`, `NIW`, `E31`, `E32`, `EW3`, `TOTAL`

This is reasonable for the current source layout but should be reviewed before expanding to new layouts.

### `country_category` Status Detection

For `country_category` files, the status is inferred from the file name:

- `App` / `Approvals` -> `approved`
- otherwise -> `received`

Those files do not provide denied/pending by country/category in the same simple way. Do not read `country_category` as a full status panel.

### PDF Parsing

PDFs are parsed through text extraction, not visual table recognition.

This creates risks:

- rows can wrap unpredictably;
- columns can be flattened into a single line;
- footnote numbers can look like data;
- multi-page table order can be fragile.

For all-forms PDFs, the parser is deliberately conservative and extracts only `TOTAL` and `I-140` rows. CSV/XLSX all-forms files are parsed more broadly.

For older I-140 PDFs, some preference/country rows are parsed from text with heuristic row merging. These are usable but not as reliable as XLSX/CSV.

## Data Model Caveats

### Two Fact Tables Mean Two Different Analytical Surfaces

`uscis_fact.form_status_counts`:

- best for broad I-140 quarterly received/approved/denied/pending across 2017-2025;
- form-level only;
- no EB category or country detail.

`uscis_fact.i140_status_counts`:

- best for EB category/country/cohort detail;
- less continuous historically;
- combines several I-140 report families with different structures.

Do not blindly join the two fact tables as if they are the same grain.

### `received`, `approved`, `denied`, and `pending` Can Mean Different Things by Report Family

In all-forms quarterly reports, `approved` and `denied` are usually completions during the reporting period.

In current-status reports, `approved`, `denied`, and `pending_other` can describe current status for petitions received in a fiscal year.

This is a major conceptual difference. Rates should be calculated within a single report family unless there is a specific reconciliation step.

### `pending_other` Is Not Always the Same as `pending`

The I-140 fiscal-year/current-status reports often use `Pending, Other`. The mart view groups `pending` and `pending_other` together into `pending`, but source-level analysis may need to keep the distinction.

### YTD Rows and Quarter Rows Coexist

`form_status_counts` has `period_scope`:

- `quarter`
- `ytd`

For trend charts, filter to `period_scope = 'quarter'` unless you explicitly need fiscal-year-to-date totals.

### Aggregates and Subcategories Can Double Count

I-140 facts include both aggregate rows and subcategory rows:

- `TOTAL`
- `EB1`, `EB2`, `EB3`
- `E11`, `E12`, `E13`, etc.

Do not sum `TOTAL` plus EB groups plus subcategories together. Use category filters deliberately.

## Known Parser/Load Behavior

### Staged Rows Can Exceed Inserted Rows

The pipeline stages more rows than are finally inserted because database unique constraints and `ON CONFLICT DO NOTHING` remove duplicate logical facts.

This is expected, but it means staging counts are not final database counts.

### Source Files Are Upserted by Hash

If the same content is loaded again under the same hash, the source row is updated rather than duplicated.

### Raw Cells Are Rebuilt per Source

When reloading, facts for staged source hashes are deleted and reinserted. Raw sheet/cell rows are upserted.

## Recommended Next Checks Before Serious Analysis

1. Build a source coverage matrix by report family, fiscal year, and quarter.
2. For each family, define the analytical grain in writing.
3. Add automated reconciliation tests for known I-140 all-forms values.
4. Add tests that `approved + denied + pending` relationships make sense where the source family supports that check.
5. Review country normalization and add ISO mapping.
6. Review a sample of PDF-derived rows, especially older preference/country PDFs.
7. Decide whether `snapshot_date` should remain fiscal quarter end or be replaced with a manual collection/publication date field.
8. Add explicit `data_quality_status` or use `reviewed=true` once a source has been manually checked.

## Bottom Line

The database is ready for cautious exploratory analysis.

It is not yet ready to be treated as a fully audited research dataset without additional validation, especially for:

- PDF-derived rows;
- country-level historical detail;
- cross-family rate comparisons;
- precise snapshot/publication-date analysis;
- any claim requiring complete FY2017-FY2026 coverage.
