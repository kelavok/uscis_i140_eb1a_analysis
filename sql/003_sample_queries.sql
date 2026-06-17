-- NIW maturation by snapshot. This becomes more useful after several USCIS snapshots.
SELECT
    snapshot_date,
    cohort_fiscal_year,
    cohort_quarter,
    received,
    approved,
    denied,
    pending,
    ROUND(approval_rate_received_basis * 100, 2) AS approval_rate_received_pct,
    ROUND(approval_rate_decided_basis * 100, 2) AS approval_rate_decided_pct,
    ROUND(pending_share * 100, 2) AS pending_share_pct
FROM uscis_mart.i140_rates_by_snapshot
WHERE category_code = 'NIW'
  AND country_code = 'ALL'
  AND source_file_id IN (
      SELECT id
      FROM uscis_raw.source_files
      WHERE report_family = 'fy_quarter_status'
  )
ORDER BY cohort_fiscal_year, cohort_quarter NULLS LAST, snapshot_date;

-- Current all-countries FY totals by category/status.
SELECT
    pc.category_code,
    cs.status_code,
    f.cohort_fiscal_year,
    f.count_value
FROM uscis_fact.i140_status_counts f
JOIN uscis_dim.preference_categories pc ON pc.id = f.category_id
JOIN uscis_dim.case_statuses cs ON cs.id = f.status_id
JOIN uscis_dim.countries c ON c.id = f.country_id
JOIN uscis_raw.source_files sf ON sf.id = f.source_file_id
WHERE sf.report_family = 'preference_country'
  AND c.country_code = 'ALL'
  AND f.cohort_fiscal_year = 2025
  AND f.is_total_column = false
ORDER BY pc.sort_order, cs.status_code;
