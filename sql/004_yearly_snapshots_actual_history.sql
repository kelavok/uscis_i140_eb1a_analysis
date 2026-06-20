CREATE OR REPLACE VIEW uscis_mart.i140_yearly_total_eb1_eb2_snapshots AS
WITH eligible_historic AS (
    SELECT
        f.source_file_id,
        f.cohort_fiscal_year AS fiscal_year,
        pc.category_code AS type,
        pc.category_name AS type_name,
        cs.status_code,
        f.count_value::numeric AS count_value,
        sf.report_family,
        sf.report_fiscal_year AS source_report_fiscal_year,
        sf.report_quarter AS source_report_quarter,
        sf.file_name AS source_file_name
    FROM uscis_fact.i140_status_counts f
    JOIN uscis_raw.source_files sf ON sf.id = f.source_file_id
    JOIN uscis_dim.preference_categories pc ON pc.id = f.category_id
    JOIN uscis_dim.countries c ON c.id = f.country_id
    JOIN uscis_dim.case_statuses cs ON cs.id = f.status_id
    WHERE sf.report_family = 'preference_country'
      AND c.country_code = 'ALL'
      AND pc.category_code = ANY (ARRAY['TOTAL', 'EB1', 'EB2'])
      AND f.cohort_fiscal_year <= 2025
      AND cs.status_code = ANY (ARRAY['received', 'approved', 'denied', 'pending', 'pending_other'])
),
latest_historic_source_by_year AS (
    SELECT DISTINCT ON (fiscal_year)
        fiscal_year,
        source_file_id
    FROM eligible_historic
    ORDER BY
        fiscal_year,
        source_report_fiscal_year DESC NULLS LAST,
        source_report_quarter DESC NULLS LAST,
        source_file_id DESC
),
eligible_actual_history AS (
    SELECT
        f.source_file_id,
        f.cohort_fiscal_year AS fiscal_year,
        pc.category_code AS type,
        pc.category_name AS type_name,
        cs.status_code,
        f.count_value::numeric AS count_value,
        sf.report_family,
        sf.report_fiscal_year AS source_report_fiscal_year,
        sf.report_quarter AS source_report_quarter,
        sf.file_name AS source_file_name
    FROM uscis_fact.i140_status_counts f
    JOIN uscis_raw.source_files sf ON sf.id = f.source_file_id
    JOIN uscis_dim.preference_categories pc ON pc.id = f.category_id
    JOIN uscis_dim.countries c ON c.id = f.country_id
    JOIN uscis_dim.case_statuses cs ON cs.id = f.status_id
    WHERE sf.report_family = 'preference_country'
      AND sf.report_fiscal_year = f.cohort_fiscal_year
      AND f.cohort_fiscal_year <= 2025
      AND c.country_code = 'ALL'
      AND pc.category_code = ANY (ARRAY['TOTAL', 'EB1', 'EB2'])
      AND cs.status_code = ANY (ARRAY['received', 'approved', 'denied', 'pending', 'pending_other'])
),
latest_actual_source_by_year AS (
    SELECT DISTINCT ON (fiscal_year)
        fiscal_year,
        source_file_id
    FROM eligible_actual_history
    ORDER BY
        fiscal_year,
        source_report_quarter DESC NULLS LAST,
        source_file_id DESC
),
actual_2026 AS (
    SELECT
        f.source_file_id,
        f.cohort_fiscal_year AS fiscal_year,
        pc.category_code AS type,
        pc.category_name AS type_name,
        cs.status_code,
        f.count_value::numeric AS count_value,
        sf.report_family,
        sf.report_fiscal_year AS source_report_fiscal_year,
        sf.report_quarter AS source_report_quarter,
        sf.file_name AS source_file_name
    FROM uscis_fact.i140_status_counts f
    JOIN uscis_raw.source_files sf ON sf.id = f.source_file_id
    JOIN uscis_dim.preference_categories pc ON pc.id = f.category_id
    JOIN uscis_dim.countries c ON c.id = f.country_id
    JOIN uscis_dim.case_statuses cs ON cs.id = f.status_id
    WHERE sf.report_family = 'fy_quarter_status'
      AND sf.report_fiscal_year = 2026
      AND sf.report_quarter = 1
      AND c.country_code = 'ALL'
      AND pc.category_code = ANY (ARRAY['TOTAL', 'EB1', 'EB2'])
      AND f.cohort_fiscal_year = 2026
      AND f.cohort_quarter = 1
      AND cs.status_code = ANY (ARRAY['received', 'approved', 'denied', 'pending'])
),
base AS (
    SELECT
        'historic'::text AS snapshot_type,
        false AS is_actual,
        e.*
    FROM eligible_historic e
    JOIN latest_historic_source_by_year ls
      ON ls.fiscal_year = e.fiscal_year
     AND ls.source_file_id = e.source_file_id

    UNION ALL

    SELECT
        'actual'::text AS snapshot_type,
        true AS is_actual,
        e.*
    FROM eligible_actual_history e
    JOIN latest_actual_source_by_year ls
      ON ls.fiscal_year = e.fiscal_year
     AND ls.source_file_id = e.source_file_id

    UNION ALL

    SELECT
        'actual'::text AS snapshot_type,
        true AS is_actual,
        a.*
    FROM actual_2026 a
),
normalized AS (
    SELECT
        snapshot_type,
        is_actual,
        fiscal_year,
        type,
        type_name,
        CASE WHEN status_code = 'pending_other' THEN 'pending' ELSE status_code END AS status_code,
        count_value,
        report_family AS source_report_family,
        source_report_fiscal_year,
        source_report_quarter,
        source_file_name
    FROM base
),
pivoted AS (
    SELECT
        fiscal_year,
        snapshot_type,
        is_actual,
        type,
        type_name,
        max(count_value) FILTER (WHERE status_code = 'received') AS received,
        max(count_value) FILTER (WHERE status_code = 'approved') AS approved,
        max(count_value) FILTER (WHERE status_code = 'denied') AS denied,
        max(count_value) FILTER (WHERE status_code = 'pending') AS pending,
        max(source_report_family) AS source_report_family,
        max(source_report_fiscal_year) AS source_report_fiscal_year,
        max(source_report_quarter) AS source_report_quarter,
        string_agg(DISTINCT source_file_name, '; ' ORDER BY source_file_name) AS source_file_names
    FROM normalized
    GROUP BY fiscal_year, snapshot_type, is_actual, type, type_name
)
SELECT
    fiscal_year,
    snapshot_type,
    is_actual,
    type,
    type_name,
    received,
    approved,
    denied,
    pending,
    CASE WHEN received > 0 THEN approved / received END AS approval_rate_received_basis,
    CASE WHEN received > 0 THEN denied / received END AS denial_rate_received_basis,
    CASE WHEN approved + denied > 0 THEN approved / (approved + denied) END AS approval_rate_decided_basis,
    CASE WHEN approved + denied > 0 THEN denied / (approved + denied) END AS denial_rate_decided_basis,
    CASE WHEN received > 0 THEN pending / received END AS pending_share,
    source_report_family,
    source_report_fiscal_year,
    source_report_quarter,
    source_file_names
FROM pivoted
ORDER BY fiscal_year, is_actual, type;
