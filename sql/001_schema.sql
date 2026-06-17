CREATE SCHEMA IF NOT EXISTS uscis_raw;
CREATE SCHEMA IF NOT EXISTS uscis_dim;
CREATE SCHEMA IF NOT EXISTS uscis_fact;
CREATE SCHEMA IF NOT EXISTS uscis_mart;

CREATE TABLE IF NOT EXISTS uscis_raw.source_files (
    id BIGSERIAL PRIMARY KEY,
    source_name TEXT NOT NULL DEFAULT 'USCIS',
    form_type TEXT NOT NULL,
    report_family TEXT NOT NULL,
    report_title TEXT NOT NULL,
    file_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    local_path TEXT,
    report_fiscal_year INT,
    report_quarter INT,
    fiscal_year_label TEXT,
    published_date DATE,
    downloaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    snapshot_date DATE NOT NULL,
    file_hash_sha256 TEXT NOT NULL UNIQUE,
    parser_version TEXT,
    parse_status TEXT NOT NULL DEFAULT 'new',
    parse_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS uscis_raw.workbook_sheets (
    id BIGSERIAL PRIMARY KEY,
    source_file_id BIGINT NOT NULL REFERENCES uscis_raw.source_files(id) ON DELETE CASCADE,
    sheet_name TEXT NOT NULL,
    sheet_index INT NOT NULL,
    max_row INT,
    max_column INT,
    detected_table_type TEXT,
    detection_confidence NUMERIC(5,4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_file_id, sheet_index)
);

CREATE TABLE IF NOT EXISTS uscis_raw.sheet_cells (
    id BIGSERIAL PRIMARY KEY,
    sheet_id BIGINT NOT NULL REFERENCES uscis_raw.workbook_sheets(id) ON DELETE CASCADE,
    row_num INT NOT NULL,
    col_num INT NOT NULL,
    cell_address TEXT,
    raw_value TEXT,
    normalized_value TEXT,
    is_merged BOOLEAN NOT NULL DEFAULT FALSE,
    merged_range TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (sheet_id, row_num, col_num)
);

CREATE TABLE IF NOT EXISTS uscis_dim.forms (
    id BIGSERIAL PRIMARY KEY,
    form_code TEXT NOT NULL UNIQUE,
    form_name TEXT
);

CREATE TABLE IF NOT EXISTS uscis_dim.preference_categories (
    id BIGSERIAL PRIMARY KEY,
    category_code TEXT NOT NULL UNIQUE,
    parent_category_code TEXT,
    category_name TEXT NOT NULL,
    category_level TEXT NOT NULL,
    is_employment_based BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS uscis_dim.case_statuses (
    id BIGSERIAL PRIMARY KEY,
    status_code TEXT NOT NULL UNIQUE,
    status_name TEXT NOT NULL,
    is_outcome BOOLEAN NOT NULL DEFAULT FALSE,
    is_current_status BOOLEAN NOT NULL DEFAULT TRUE,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS uscis_dim.countries (
    id BIGSERIAL PRIMARY KEY,
    country_code TEXT NOT NULL UNIQUE,
    country_name TEXT NOT NULL,
    iso_alpha2 TEXT,
    iso_alpha3 TEXT,
    uscis_country_label TEXT,
    notes TEXT
);

ALTER TABLE uscis_dim.countries ADD COLUMN IF NOT EXISTS country_code TEXT;
UPDATE uscis_dim.countries
SET country_code = CASE
    WHEN country_name = 'All Countries' THEN 'ALL'
    ELSE upper(left(regexp_replace(country_name, '[^A-Za-z0-9]+', '_', 'g'), 40))
END
WHERE country_code IS NULL;
ALTER TABLE uscis_dim.countries ALTER COLUMN country_code SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS countries_country_code_key ON uscis_dim.countries(country_code);

CREATE TABLE IF NOT EXISTS uscis_dim.report_families (
    id BIGSERIAL PRIMARY KEY,
    report_family_code TEXT NOT NULL UNIQUE,
    report_family_name TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS uscis_fact.i140_status_counts (
    id BIGSERIAL PRIMARY KEY,
    source_file_id BIGINT NOT NULL REFERENCES uscis_raw.source_files(id) ON DELETE CASCADE,
    sheet_id BIGINT REFERENCES uscis_raw.workbook_sheets(id) ON DELETE CASCADE,
    form_id BIGINT NOT NULL REFERENCES uscis_dim.forms(id),
    report_family_id BIGINT REFERENCES uscis_dim.report_families(id),
    category_id BIGINT NOT NULL REFERENCES uscis_dim.preference_categories(id),
    country_id BIGINT REFERENCES uscis_dim.countries(id),
    status_id BIGINT NOT NULL REFERENCES uscis_dim.case_statuses(id),
    cohort_fiscal_year INT NOT NULL,
    cohort_quarter INT,
    report_fiscal_year INT,
    report_quarter INT,
    snapshot_date DATE NOT NULL,
    count_value INT NOT NULL,
    value_type TEXT NOT NULL DEFAULT 'count',
    is_total_row BOOLEAN NOT NULL DEFAULT FALSE,
    is_total_column BOOLEAN NOT NULL DEFAULT FALSE,
    raw_row_label TEXT,
    raw_column_label TEXT,
    raw_cell_address TEXT,
    extraction_method TEXT NOT NULL DEFAULT 'script',
    extraction_confidence NUMERIC(5,4),
    reviewed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (
        source_file_id, sheet_id, category_id, country_id, status_id,
        cohort_fiscal_year, cohort_quarter, snapshot_date, value_type,
        raw_row_label, raw_column_label, raw_cell_address
    )
);

CREATE TABLE IF NOT EXISTS uscis_fact.form_status_counts (
    id BIGSERIAL PRIMARY KEY,
    source_file_id BIGINT NOT NULL REFERENCES uscis_raw.source_files(id) ON DELETE CASCADE,
    sheet_id BIGINT REFERENCES uscis_raw.workbook_sheets(id) ON DELETE CASCADE,
    form_id BIGINT NOT NULL REFERENCES uscis_dim.forms(id),
    status_id BIGINT NOT NULL REFERENCES uscis_dim.case_statuses(id),
    report_fiscal_year INT,
    report_quarter INT,
    snapshot_date DATE NOT NULL,
    period_scope TEXT NOT NULL,
    period_quarter INT,
    count_value NUMERIC(18,3) NOT NULL,
    form_category TEXT,
    form_description TEXT,
    raw_row_label TEXT,
    raw_column_label TEXT,
    raw_cell_address TEXT,
    extraction_method TEXT NOT NULL DEFAULT 'script',
    extraction_confidence NUMERIC(5,4),
    reviewed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (
        source_file_id, sheet_id, form_id, status_id, report_fiscal_year,
        report_quarter, period_scope, period_quarter, raw_column_label
    )
);

CREATE TABLE IF NOT EXISTS uscis_raw.extraction_corrections (
    id BIGSERIAL PRIMARY KEY,
    source_file_id BIGINT NOT NULL REFERENCES uscis_raw.source_files(id) ON DELETE CASCADE,
    sheet_id BIGINT REFERENCES uscis_raw.workbook_sheets(id) ON DELETE CASCADE,
    target_fact_id BIGINT REFERENCES uscis_fact.i140_status_counts(id) ON DELETE SET NULL,
    correction_type TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    reason TEXT,
    corrected_by TEXT,
    corrected_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

DROP VIEW IF EXISTS uscis_mart.i140_rates_by_snapshot;

CREATE VIEW uscis_mart.i140_rates_by_snapshot AS
SELECT
    f.source_file_id,
    f.category_id,
    pc.category_code,
    f.country_id,
    c.country_code,
    c.country_name,
    f.cohort_fiscal_year,
    f.cohort_quarter,
    f.snapshot_date,
    SUM(CASE WHEN cs.status_code = 'received' THEN f.count_value ELSE 0 END) AS received,
    SUM(CASE WHEN cs.status_code = 'approved' THEN f.count_value ELSE 0 END) AS approved,
    SUM(CASE WHEN cs.status_code = 'denied' THEN f.count_value ELSE 0 END) AS denied,
    SUM(CASE WHEN cs.status_code IN ('pending', 'pending_other') THEN f.count_value ELSE 0 END) AS pending,
    CASE
        WHEN SUM(CASE WHEN cs.status_code = 'received' THEN f.count_value ELSE 0 END) > 0
        THEN SUM(CASE WHEN cs.status_code = 'approved' THEN f.count_value ELSE 0 END)::numeric
             / SUM(CASE WHEN cs.status_code = 'received' THEN f.count_value ELSE 0 END)
    END AS approval_rate_received_basis,
    CASE
        WHEN SUM(CASE WHEN cs.status_code IN ('approved', 'denied') THEN f.count_value ELSE 0 END) > 0
        THEN SUM(CASE WHEN cs.status_code = 'approved' THEN f.count_value ELSE 0 END)::numeric
             / SUM(CASE WHEN cs.status_code IN ('approved', 'denied') THEN f.count_value ELSE 0 END)
    END AS approval_rate_decided_basis,
    CASE
        WHEN SUM(CASE WHEN cs.status_code = 'received' THEN f.count_value ELSE 0 END) > 0
        THEN SUM(CASE WHEN cs.status_code IN ('pending', 'pending_other') THEN f.count_value ELSE 0 END)::numeric
             / SUM(CASE WHEN cs.status_code = 'received' THEN f.count_value ELSE 0 END)
    END AS pending_share
FROM uscis_fact.i140_status_counts f
JOIN uscis_dim.case_statuses cs ON cs.id = f.status_id
JOIN uscis_dim.preference_categories pc ON pc.id = f.category_id
LEFT JOIN uscis_dim.countries c ON c.id = f.country_id
GROUP BY
    f.source_file_id, f.category_id, pc.category_code, f.country_id,
    c.country_code, c.country_name, f.cohort_fiscal_year,
    f.cohort_quarter, f.snapshot_date;

CREATE INDEX IF NOT EXISTS idx_i140_status_counts_snapshot
    ON uscis_fact.i140_status_counts (snapshot_date, cohort_fiscal_year, cohort_quarter);

CREATE INDEX IF NOT EXISTS idx_i140_status_counts_dims
    ON uscis_fact.i140_status_counts (category_id, country_id, status_id);

CREATE INDEX IF NOT EXISTS idx_form_status_counts_snapshot
    ON uscis_fact.form_status_counts (snapshot_date, report_fiscal_year, report_quarter, form_id, status_id);
