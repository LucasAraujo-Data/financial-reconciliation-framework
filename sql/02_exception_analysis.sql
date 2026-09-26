/*
===============================================================================
Financial Reconciliation Framework
02 - Exception Analysis
===============================================================================

Purpose:
    Analyze reconciliation exceptions by exception type and severity.

SQL Engine:
    DuckDB
===============================================================================
*/

WITH reconciliation AS (
    SELECT *
    FROM read_csv_auto(
        'outputs/reconciliation_results.csv',
        header = true
    )
),

exceptions AS (
    SELECT *
    FROM reconciliation
    WHERE reconciliation_status <> 'MATCHED'
),

exception_summary AS (
    SELECT
        reconciliation_status AS exception_type,
        severity,

        COUNT(DISTINCT transaction_id) AS exception_count,

        SUM(
            COALESCE(financial_exposure_usd, 0)
        ) AS total_exposure_usd,

        AVG(
            COALESCE(financial_exposure_usd, 0)
        ) AS average_exposure_usd,

        MAX(
            COALESCE(financial_exposure_usd, 0)
        ) AS maximum_exposure_usd,

        COUNT(
            DISTINCT CASE
                WHEN severity IN ('HIGH', 'CRITICAL')
                THEN transaction_id
            END
        ) AS material_exception_count,

        COUNT(
            DISTINCT CASE
                WHEN severity = 'CRITICAL'
                THEN transaction_id
            END
        ) AS critical_exception_count

    FROM exceptions

    GROUP BY
        reconciliation_status,
        severity
),

total AS (
    SELECT
        SUM(exception_count) AS total_exception_count
    FROM exception_summary
)

SELECT
    e.exception_type,
    e.severity,
    e.exception_count,

    ROUND(
        100.0 * e.exception_count
        / NULLIF(t.total_exception_count, 0),
        2
    ) AS exception_share_pct,

    ROUND(e.total_exposure_usd, 2)
        AS total_exposure_usd,

    ROUND(e.average_exposure_usd, 2)
        AS average_exposure_usd,

    ROUND(e.maximum_exposure_usd, 2)
        AS maximum_exposure_usd,

    e.material_exception_count,
    e.critical_exception_count

FROM exception_summary e
CROSS JOIN total t

ORDER BY
    e.total_exposure_usd DESC,
    e.exception_count DESC