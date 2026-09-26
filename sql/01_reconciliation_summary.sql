/*
===============================================================================
Financial Reconciliation Framework
01 - Reconciliation Summary
===============================================================================

Purpose:
    Provide executive reconciliation KPIs from the transaction-level
    reconciliation output.

Expected results with the default synthetic dataset:
    Total Transactions      : 50,000
    Matched Transactions    : 47,500
    Exception Transactions  : 2,500
    Match Rate              : 95.00%
    Exception Rate          : 5.00%

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

summary AS (
    SELECT
        COUNT(DISTINCT transaction_id) AS total_transactions,

        COUNT(
            DISTINCT CASE
                WHEN reconciliation_status = 'MATCHED'
                THEN transaction_id
            END
        ) AS matched_transactions,

        COUNT(
            DISTINCT CASE
                WHEN reconciliation_status <> 'MATCHED'
                THEN transaction_id
            END
        ) AS exception_transactions

    FROM reconciliation
)

SELECT
    total_transactions,
    matched_transactions,
    exception_transactions,

    ROUND(
        100.0 * matched_transactions
        / NULLIF(total_transactions, 0),
        2
    ) AS match_rate_pct,

    ROUND(
        100.0 * exception_transactions
        / NULLIF(total_transactions, 0),
        2
    ) AS exception_rate_pct

FROM summary;