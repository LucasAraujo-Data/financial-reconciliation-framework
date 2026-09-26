/*
===============================================================================
Financial Reconciliation Framework
04 - Counterparty Risk Analysis
===============================================================================

Purpose:
    Identify counterparties associated with the highest reconciliation
    financial exposure.

Business Questions:
    - Which counterparties generate the greatest exception exposure?
    - How many exceptions are associated with each counterparty?
    - How many are material?
    - How concentrated is financial exposure?
    - Which counterparties should receive investigation priority?

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
    SELECT
        *,

        COALESCE(
            NULLIF(TRIM(counterparty_id_source), ''),
            NULLIF(TRIM(counterparty_id_accounting), ''),
            'UNKNOWN'
        ) AS counterparty_id

    FROM reconciliation

    WHERE reconciliation_status <> 'MATCHED'
),

overall_exposure AS (
    SELECT
        SUM(
            COALESCE(financial_exposure_usd, 0)
        ) AS total_exception_exposure_usd

    FROM exceptions
),

counterparty_summary AS (
    SELECT
        counterparty_id,

        COUNT(
            DISTINCT transaction_id
        ) AS exception_count,

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

        SUM(
            CASE
                WHEN severity IN ('HIGH', 'CRITICAL')
                THEN COALESCE(financial_exposure_usd, 0)
                ELSE 0
            END
        ) AS material_exposure_usd,

        COUNT(
            DISTINCT CASE
                WHEN severity = 'CRITICAL'
                THEN transaction_id
            END
        ) AS critical_exception_count

    FROM exceptions

    GROUP BY counterparty_id
),

ranked_counterparties AS (
    SELECT
        *,

        DENSE_RANK() OVER (
            ORDER BY total_exposure_usd DESC
        ) AS exposure_rank

    FROM counterparty_summary
)

SELECT
    exposure_rank,
    counterparty_id,
    exception_count,

    ROUND(
        total_exposure_usd,
        2
    ) AS total_exposure_usd,

    ROUND(
        100.0 * total_exposure_usd
        / NULLIF(
            overall_exposure.total_exception_exposure_usd,
            0
        ),
        2
    ) AS exposure_share_pct,

    ROUND(
        average_exposure_usd,
        2
    ) AS average_exposure_usd,

    ROUND(
        maximum_exposure_usd,
        2
    ) AS maximum_exposure_usd,

    material_exception_count,

    ROUND(
        material_exposure_usd,
        2
    ) AS material_exposure_usd,

    critical_exception_count

FROM ranked_counterparties

CROSS JOIN overall_exposure

ORDER BY
    exposure_rank,
    counterparty_id;