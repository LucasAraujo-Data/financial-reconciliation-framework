# Data Dictionary

## source_transactions

Operational system transactions.

| Column | Type | Description |
|----------|----------|----------|
| transaction_id | string | Unique transaction identifier |
| contract_id | string | Contract identifier |
| counterparty_id | string | Counterparty identifier |
| transaction_type | string | Premium, Claim or Commission |
| accounting_period | string | Accounting month (YYYY-MM) |
| transaction_date | date | Business transaction date |
| currency | string | Transaction currency |
| original_amount | decimal | Original amount |
| exchange_rate | decimal | Exchange rate to USD |
| converted_amount_usd | decimal | Amount converted to USD |
| processing_timestamp | datetime | Processing timestamp |

---

## accounting_transactions

Accounting system transactions.

| Column | Type | Description |
|----------|----------|----------|
| transaction_id | string | Unique transaction identifier |
| contract_id | string | Contract identifier |
| counterparty_id | string | Counterparty identifier |
| transaction_type | string | Premium, Claim or Commission |
| accounting_period | string | Accounting month (YYYY-MM) |
| transaction_date | date | Business transaction date |
| currency | string | Transaction currency |
| original_amount | decimal | Original amount |
| exchange_rate | decimal | Exchange rate to USD |
| converted_amount_usd | decimal | Amount converted to USD |
| processing_timestamp | datetime | Processing timestamp |

---

## reconciliation_results

Final reconciliation output.

| Column | Type | Description |
|----------|----------|----------|
| reconciliation_id | string | Unique reconciliation identifier |
| transaction_id | string | Transaction identifier |
| reconciliation_status | string | Match result |
| absolute_difference | decimal | Absolute difference |
| relative_difference | decimal | Relative difference |
| severity | string | Low, Medium, High or Critical |
| run_id | string | Pipeline execution identifier |
| execution_timestamp | datetime | Pipeline execution timestamp |