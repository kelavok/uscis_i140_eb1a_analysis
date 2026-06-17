INSERT INTO uscis_dim.forms (form_code, form_name)
VALUES
('I-140', 'Immigrant Petition for Alien Worker'),
('TOTAL', 'Total - All Forms')
ON CONFLICT (form_code) DO UPDATE SET form_name = EXCLUDED.form_name;

INSERT INTO uscis_dim.report_families (report_family_code, report_family_name, description)
VALUES
('fy_quarter_status', 'Form I-140 by Fiscal Year, Quarter and Case Status', 'Quarterly I-140 receipts/current status by employment preference.'),
('preference_country', 'Form I-140 Receipts and Current Status by Preference and Country', 'I-140 receipts/current status by preference and country/fiscal year.')
,
('country_category', 'Form I-140 Receipts or Approvals by Country and Category', 'I-140 receipts/approvals by beneficiary country of birth and EB category.'),
('all_forms', 'Quarterly All Forms', 'Service-wide quarterly form status counts by form number.')
ON CONFLICT (report_family_code) DO UPDATE
SET report_family_name = EXCLUDED.report_family_name,
    description = EXCLUDED.description;

INSERT INTO uscis_dim.case_statuses (status_code, status_name, is_outcome, is_current_status, notes)
VALUES
('received', 'Received', false, false, 'New applications received and entered into case-tracking system.'),
('approved', 'Approved', true, true, NULL),
('denied', 'Denied', true, true, NULL),
('pending', 'Pending', false, true, NULL),
('pending_other', 'Pending, Other', false, true, 'USCIS label often used in fiscal-year/current-status reports.')
ON CONFLICT (status_code) DO UPDATE
SET status_name = EXCLUDED.status_name,
    is_outcome = EXCLUDED.is_outcome,
    is_current_status = EXCLUDED.is_current_status,
    notes = EXCLUDED.notes;

INSERT INTO uscis_dim.countries (country_code, country_name, uscis_country_label)
VALUES ('ALL', 'All Countries', 'All Countries')
ON CONFLICT (country_code) DO UPDATE
SET country_name = EXCLUDED.country_name,
    uscis_country_label = EXCLUDED.uscis_country_label;

INSERT INTO uscis_dim.preference_categories
    (category_code, parent_category_code, category_name, category_level, sort_order, notes)
VALUES
('TOTAL', NULL, 'Total', 'total', 0, NULL),
('EB1', NULL, 'First Preference', 'preference', 10, NULL),
('E11', 'EB1', 'Aliens with Extraordinary Ability', 'approval_category', 11, NULL),
('E12', 'EB1', 'Outstanding Professors or Researchers', 'approval_category', 12, NULL),
('E13', 'EB1', 'Multinational Executives or Managers', 'approval_category', 13, NULL),
('EB2', NULL, 'Second Preference', 'preference', 20, NULL),
('E21', 'EB2', 'Professionals with Advanced Degrees', 'approval_category', 21, NULL),
('NIW', 'EB2', 'National Interest Waiver', 'approval_category', 22, NULL),
('EB3', NULL, 'Third Preference', 'preference', 30, NULL),
('E31', 'EB3', 'Skilled Workers', 'approval_category', 31, NULL),
('E32', 'EB3', 'Professionals with Baccalaureate Degrees', 'approval_category', 32, NULL),
('EW3', 'EB3', 'Unskilled Workers', 'approval_category', 33, NULL),
('OTHER_UNKNOWN', NULL, 'Other and Unknown', 'unknown', 90, NULL)
ON CONFLICT (category_code) DO UPDATE
SET parent_category_code = EXCLUDED.parent_category_code,
    category_name = EXCLUDED.category_name,
    category_level = EXCLUDED.category_level,
    sort_order = EXCLUDED.sort_order,
    notes = EXCLUDED.notes;
