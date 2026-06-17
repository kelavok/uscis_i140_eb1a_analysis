BEGIN;

CREATE TEMP TABLE stg_source_files (
    file_hash_sha256 text, source_name text, form_type text, report_family text,
    report_title text, file_name text, source_url text, local_path text,
    report_fiscal_year text, report_quarter text, fiscal_year_label text,
    published_date text, snapshot_date date, parser_version text,
    parse_status text, parse_notes text
);
\copy stg_source_files FROM 'source_files.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')

CREATE TEMP TABLE stg_sheets (
    file_hash_sha256 text, sheet_index int, sheet_name text, max_row int,
    max_column int, detected_table_type text, detection_confidence numeric
);
\copy stg_sheets FROM 'workbook_sheets.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')

CREATE TEMP TABLE stg_cells (
    file_hash_sha256 text, sheet_index int, row_num int, col_num int,
    cell_address text, raw_value text, normalized_value text,
    is_merged boolean, merged_range text
);
\copy stg_cells FROM 'sheet_cells.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')

CREATE TEMP TABLE stg_countries (
    country_code text, country_name text, uscis_country_label text
);
\copy stg_countries FROM 'countries.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')

CREATE TEMP TABLE stg_facts (
    file_hash_sha256 text, sheet_index int, category_code text, country_code text,
    status_code text, cohort_fiscal_year int, cohort_quarter text,
    report_fiscal_year text, report_quarter text, snapshot_date date,
    count_value int, value_type text, is_total_row boolean, is_total_column boolean,
    raw_row_label text, raw_column_label text, raw_cell_address text,
    extraction_method text, extraction_confidence numeric, reviewed boolean
);
\copy stg_facts FROM 'facts.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')

CREATE TEMP TABLE stg_form_facts (
    file_hash_sha256 text, sheet_index int, form_code text, form_name text,
    status_code text, report_fiscal_year text, report_quarter text,
    snapshot_date date, period_scope text, period_quarter text,
    count_value numeric, form_category text, form_description text,
    raw_row_label text, raw_column_label text, raw_cell_address text,
    extraction_method text, extraction_confidence numeric, reviewed boolean
);
\copy stg_form_facts FROM 'form_facts.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')

INSERT INTO uscis_dim.countries (country_code, country_name, uscis_country_label)
SELECT DISTINCT country_code, country_name, uscis_country_label
FROM stg_countries
ON CONFLICT (country_code) DO UPDATE
SET country_name = EXCLUDED.country_name,
    uscis_country_label = EXCLUDED.uscis_country_label;

INSERT INTO uscis_raw.source_files (
    file_hash_sha256, source_name, form_type, report_family, report_title,
    file_name, source_url, local_path, report_fiscal_year, report_quarter,
    fiscal_year_label, published_date, snapshot_date, parser_version,
    parse_status, parse_notes
)
SELECT
    file_hash_sha256, source_name, form_type, report_family, report_title,
    file_name, source_url, local_path,
    NULLIF(report_fiscal_year, '')::int,
    NULLIF(report_quarter, '')::int,
    fiscal_year_label,
    NULLIF(published_date, '')::date,
    snapshot_date, parser_version, parse_status, parse_notes
FROM stg_source_files
ON CONFLICT (file_hash_sha256) DO UPDATE
SET local_path = EXCLUDED.local_path,
    snapshot_date = EXCLUDED.snapshot_date,
    parser_version = EXCLUDED.parser_version,
    parse_status = EXCLUDED.parse_status,
    parse_notes = EXCLUDED.parse_notes;

INSERT INTO uscis_raw.workbook_sheets (
    source_file_id, sheet_name, sheet_index, max_row, max_column,
    detected_table_type, detection_confidence
)
SELECT sf.id, s.sheet_name, s.sheet_index, s.max_row, s.max_column,
       s.detected_table_type, s.detection_confidence
FROM stg_sheets s
JOIN uscis_raw.source_files sf ON sf.file_hash_sha256 = s.file_hash_sha256
ON CONFLICT (source_file_id, sheet_index) DO UPDATE
SET sheet_name = EXCLUDED.sheet_name,
    max_row = EXCLUDED.max_row,
    max_column = EXCLUDED.max_column,
    detected_table_type = EXCLUDED.detected_table_type,
    detection_confidence = EXCLUDED.detection_confidence;

INSERT INTO uscis_raw.sheet_cells (
    sheet_id, row_num, col_num, cell_address, raw_value,
    normalized_value, is_merged, merged_range
)
SELECT ws.id, c.row_num, c.col_num, c.cell_address, c.raw_value,
       c.normalized_value, c.is_merged, c.merged_range
FROM stg_cells c
JOIN uscis_raw.source_files sf ON sf.file_hash_sha256 = c.file_hash_sha256
JOIN uscis_raw.workbook_sheets ws ON ws.source_file_id = sf.id AND ws.sheet_index = c.sheet_index
ON CONFLICT (sheet_id, row_num, col_num) DO UPDATE
SET raw_value = EXCLUDED.raw_value,
    normalized_value = EXCLUDED.normalized_value,
    is_merged = EXCLUDED.is_merged,
    merged_range = EXCLUDED.merged_range;

DELETE FROM uscis_fact.i140_status_counts f
USING uscis_raw.source_files sf, stg_source_files stg
WHERE f.source_file_id = sf.id
  AND sf.file_hash_sha256 = stg.file_hash_sha256;

DELETE FROM uscis_fact.form_status_counts f
USING uscis_raw.source_files sf, stg_source_files stg
WHERE f.source_file_id = sf.id
  AND sf.file_hash_sha256 = stg.file_hash_sha256;

INSERT INTO uscis_fact.i140_status_counts (
    source_file_id, sheet_id, form_id, report_family_id, category_id,
    country_id, status_id, cohort_fiscal_year, cohort_quarter,
    report_fiscal_year, report_quarter, snapshot_date, count_value,
    value_type, is_total_row, is_total_column, raw_row_label,
    raw_column_label, raw_cell_address, extraction_method,
    extraction_confidence, reviewed
)
SELECT
    sf.id, ws.id, frm.id, rf.id, pc.id, co.id, cs.id,
    f.cohort_fiscal_year, NULLIF(f.cohort_quarter, '')::int,
    NULLIF(f.report_fiscal_year, '')::int,
    NULLIF(f.report_quarter, '')::int,
    f.snapshot_date, f.count_value, f.value_type,
    f.is_total_row, f.is_total_column, f.raw_row_label,
    f.raw_column_label, f.raw_cell_address, f.extraction_method,
    f.extraction_confidence, f.reviewed
FROM stg_facts f
JOIN uscis_raw.source_files sf ON sf.file_hash_sha256 = f.file_hash_sha256
JOIN uscis_raw.workbook_sheets ws ON ws.source_file_id = sf.id AND ws.sheet_index = f.sheet_index
JOIN uscis_dim.forms frm ON frm.form_code = 'I-140'
JOIN uscis_dim.report_families rf ON rf.report_family_code = sf.report_family
JOIN uscis_dim.preference_categories pc ON pc.category_code = f.category_code
JOIN uscis_dim.countries co ON co.country_code = f.country_code
JOIN uscis_dim.case_statuses cs ON cs.status_code = f.status_code
ON CONFLICT DO NOTHING;

INSERT INTO uscis_dim.forms (form_code, form_name)
SELECT
    form_code,
    MAX(COALESCE(NULLIF(form_name, ''), NULLIF(form_description, ''), form_code)) AS form_name
FROM stg_form_facts
WHERE form_code IS NOT NULL AND form_code <> ''
GROUP BY form_code
ON CONFLICT (form_code) DO UPDATE
SET form_name = COALESCE(EXCLUDED.form_name, uscis_dim.forms.form_name);

INSERT INTO uscis_fact.form_status_counts (
    source_file_id, sheet_id, form_id, status_id, report_fiscal_year,
    report_quarter, snapshot_date, period_scope, period_quarter,
    count_value, form_category, form_description, raw_row_label,
    raw_column_label, raw_cell_address, extraction_method,
    extraction_confidence, reviewed
)
SELECT
    sf.id, ws.id, frm.id, cs.id,
    NULLIF(f.report_fiscal_year, '')::int,
    NULLIF(f.report_quarter, '')::int,
    f.snapshot_date, f.period_scope,
    NULLIF(f.period_quarter, '')::int,
    f.count_value, f.form_category, f.form_description,
    f.raw_row_label, f.raw_column_label, f.raw_cell_address,
    f.extraction_method, f.extraction_confidence, f.reviewed
FROM stg_form_facts f
JOIN uscis_raw.source_files sf ON sf.file_hash_sha256 = f.file_hash_sha256
JOIN uscis_raw.workbook_sheets ws ON ws.source_file_id = sf.id AND ws.sheet_index = f.sheet_index
JOIN uscis_dim.forms frm ON frm.form_code = f.form_code
JOIN uscis_dim.case_statuses cs ON cs.status_code = f.status_code
ON CONFLICT DO NOTHING;

COMMIT;
