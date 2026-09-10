from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SOURCE_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "source_transactions.csv"
)

ACCOUNTING_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "accounting_transactions.csv"
)

CONFIG_PATH = (
    PROJECT_ROOT
    / "configs"
    / "reconciliation_rules.yml"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "reconciliation_results.csv"
)


REQUIRED_COLUMNS = [
    "transaction_id",
    "contract_id",
    "counterparty_id",
    "transaction_type",
    "accounting_period",
    "transaction_date",
    "currency",
    "original_amount",
    "exchange_rate",
    "converted_amount_usd",
    "processing_timestamp",
]


def load_config(config_path: Path) -> dict[str, Any]:
    """Load reconciliation rules from YAML."""
    with config_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return yaml.safe_load(file)


def load_transactions(path: Path) -> pd.DataFrame:
    """Load transaction data using expected data types."""
    return pd.read_csv(
        path,
        dtype={
            "transaction_id": "string",
            "contract_id": "string",
            "counterparty_id": "string",
            "transaction_type": "string",
            "accounting_period": "string",
            "currency": "string",
        },
        parse_dates=[
            "transaction_date",
            "processing_timestamp",
        ],
    )


def validate_schema(
    dataframe: pd.DataFrame,
    dataset_name: str,
) -> None:
    """Validate presence of all required columns."""

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            f"{dataset_name} is missing required columns: "
            f"{missing_columns}"
        )


def identify_duplicate_ids(
    dataframe: pd.DataFrame,
) -> set[str]:
    """Return transaction IDs occurring more than once."""

    counts = (
        dataframe["transaction_id"]
        .value_counts()
    )

    return set(
        counts[
            counts > 1
        ].index.astype(str)
    )


def remove_duplicate_rows_for_matching(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Keep one representative record for each transaction.

    Duplicate detection occurs separately. Removing repeated rows before
    joining prevents accidental many-to-many reconciliation joins.
    """

    return (
        dataframe
        .drop_duplicates(
            subset=["transaction_id"],
            keep="first",
        )
        .copy()
    )


def build_reconciliation_dataset(
    source: pd.DataFrame,
    accounting: pd.DataFrame,
) -> pd.DataFrame:
    """Outer join source and accounting transactions."""

    source_unique = remove_duplicate_rows_for_matching(
        source
    )

    accounting_unique = remove_duplicate_rows_for_matching(
        accounting
    )

    reconciliation = source_unique.merge(
        accounting_unique,
        on="transaction_id",
        how="outer",
        suffixes=(
            "_source",
            "_accounting",
        ),
        indicator=True,
        validate="one_to_one",
    )

    return reconciliation


def calculate_differences(
    reconciliation: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate financial, FX and processing differences."""

    reconciliation[
        "amount_difference_usd"
    ] = (
        reconciliation[
            "converted_amount_usd_accounting"
        ]
        - reconciliation[
            "converted_amount_usd_source"
        ]
    )

    reconciliation[
        "absolute_difference_usd"
    ] = (
        reconciliation[
            "amount_difference_usd"
        ].abs()
    )

    source_amount = (
        reconciliation[
            "converted_amount_usd_source"
        ].abs()
    )

    reconciliation[
        "relative_difference"
    ] = np.where(
        source_amount > 0,
        (
            reconciliation[
                "absolute_difference_usd"
            ]
            / source_amount
        ),
        np.where(
            reconciliation[
                "absolute_difference_usd"
            ] > 0,
            np.inf,
            0.0,
        ),
    )

    reconciliation[
        "exchange_rate_difference"
    ] = (
        reconciliation[
            "exchange_rate_accounting"
        ]
        - reconciliation[
            "exchange_rate_source"
        ]
    ).abs()

    reconciliation[
        "processing_delay_hours"
    ] = (
        (
            reconciliation[
                "processing_timestamp_accounting"
            ]
            - reconciliation[
                "processing_timestamp_source"
            ]
        )
        .dt.total_seconds()
        / 3600
    )

    return reconciliation


def values_different(
    left: pd.Series,
    right: pd.Series,
) -> pd.Series:
    """
    Compare two Series while treating two missing values as equal.
    """

    return ~(
        left.eq(right)
        | (
            left.isna()
            & right.isna()
        )
    )


def classify_reconciliation_status(
    reconciliation: pd.DataFrame,
    duplicate_ids: set[str],
    config: dict[str, Any],
) -> pd.DataFrame:
    """Classify transactions according to reconciliation rules."""

    absolute_tolerance = (
        config[
            "tolerances"
        ][
            "absolute_amount_usd"
        ]
    )

    relative_tolerance = (
        config[
            "tolerances"
        ][
            "relative_amount_percentage"
        ]
    )

    fx_tolerance = (
        config[
            "tolerances"
        ][
            "exchange_rate"
        ]
    )

    reconciliation[
        "reconciliation_status"
    ] = "MATCHED"

    missing_in_accounting = (
        reconciliation["_merge"]
        == "left_only"
    )

    missing_in_source = (
        reconciliation["_merge"]
        == "right_only"
    )

    present_in_both = (
        reconciliation["_merge"]
        == "both"
    )

    duplicate_transaction = (
        reconciliation[
            "transaction_id"
        ]
        .astype(str)
        .isin(duplicate_ids)
    )

    contract_mismatch = (
        present_in_both
        & values_different(
            reconciliation[
                "contract_id_source"
            ],
            reconciliation[
                "contract_id_accounting"
            ],
        )
    )

    counterparty_mismatch = (
        present_in_both
        & values_different(
            reconciliation[
                "counterparty_id_source"
            ],
            reconciliation[
                "counterparty_id_accounting"
            ],
        )
    )

    mapping_error = (
        contract_mismatch
        | counterparty_mismatch
    )

    period_mismatch = (
        present_in_both
        & values_different(
            reconciliation[
                "accounting_period_source"
            ],
            reconciliation[
                "accounting_period_accounting"
            ],
        )
    )

    transaction_type_mismatch = (
        present_in_both
        & values_different(
            reconciliation[
                "transaction_type_source"
            ],
            reconciliation[
                "transaction_type_accounting"
            ],
        )
    )

    currency_mismatch = (
        present_in_both
        & values_different(
            reconciliation[
                "currency_source"
            ],
            reconciliation[
                "currency_accounting"
            ],
        )
    )

    fx_difference = (
        present_in_both
        & (
            reconciliation[
                "exchange_rate_difference"
            ]
            > fx_tolerance
        )
        & ~mapping_error
        & ~period_mismatch
        & ~transaction_type_mismatch
        & ~currency_mismatch
    )

    amount_difference = (
        present_in_both
        & (
            reconciliation[
                "absolute_difference_usd"
            ]
            > absolute_tolerance
        )
        & (
            reconciliation[
                "relative_difference"
            ]
            > relative_tolerance
        )
        & ~fx_difference
        & ~mapping_error
        & ~period_mismatch
        & ~transaction_type_mismatch
        & ~currency_mismatch
    )

    reprocessed_transaction = (
        present_in_both
        & (
            reconciliation[
                "processing_delay_hours"
            ]
            >= 24
        )
        & ~mapping_error
        & ~period_mismatch
        & ~fx_difference
        & ~amount_difference
        & ~transaction_type_mismatch
        & ~currency_mismatch
    )

    reconciliation.loc[
        amount_difference,
        "reconciliation_status",
    ] = "AMOUNT_MISMATCH"

    reconciliation.loc[
        fx_difference,
        "reconciliation_status",
    ] = "FX_DIFFERENCE"

    reconciliation.loc[
        reprocessed_transaction,
        "reconciliation_status",
    ] = "REPROCESSED_TRANSACTION"

    reconciliation.loc[
        period_mismatch,
        "reconciliation_status",
    ] = "PERIOD_MISMATCH"

    reconciliation.loc[
        (
            mapping_error
            | transaction_type_mismatch
            | currency_mismatch
        ),
        "reconciliation_status",
    ] = "MAPPING_ERROR"

    reconciliation.loc[
        missing_in_accounting,
        "reconciliation_status",
    ] = "MISSING_IN_ACCOUNTING"

    reconciliation.loc[
        missing_in_source,
        "reconciliation_status",
    ] = "MISSING_IN_SOURCE"

    reconciliation.loc[
        duplicate_transaction,
        "reconciliation_status",
    ] = "DUPLICATE_TRANSACTION"

    return reconciliation


def calculate_financial_exposure(
    reconciliation: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate the financial amount potentially affected by each exception.

    Financial exposure represents the monetary value potentially affected
    by an exception and is intentionally different from the mathematical
    difference between systems.
    """

    source_amount = pd.to_numeric(
        reconciliation[
            "converted_amount_usd_source"
        ],
        errors="coerce",
    ).abs()

    accounting_amount = pd.to_numeric(
        reconciliation[
            "converted_amount_usd_accounting"
        ],
        errors="coerce",
    ).abs()

    absolute_difference = pd.to_numeric(
        reconciliation[
            "absolute_difference_usd"
        ],
        errors="coerce",
    ).fillna(0).abs()

    reconciliation[
        "financial_exposure_usd"
    ] = absolute_difference

    matched_mask = (
        reconciliation[
            "reconciliation_status"
        ]
        == "MATCHED"
    )

    missing_in_accounting_mask = (
        reconciliation[
            "reconciliation_status"
        ]
        == "MISSING_IN_ACCOUNTING"
    )

    missing_in_source_mask = (
        reconciliation[
            "reconciliation_status"
        ]
        == "MISSING_IN_SOURCE"
    )

    duplicate_mask = (
        reconciliation[
            "reconciliation_status"
        ]
        == "DUPLICATE_TRANSACTION"
    )

    mapping_error_mask = (
        reconciliation[
            "reconciliation_status"
        ]
        == "MAPPING_ERROR"
    )

    period_mismatch_mask = (
        reconciliation[
            "reconciliation_status"
        ]
        == "PERIOD_MISMATCH"
    )

    reconciliation.loc[
        matched_mask,
        "financial_exposure_usd",
    ] = 0.0

    reconciliation.loc[
        missing_in_accounting_mask,
        "financial_exposure_usd",
    ] = source_amount[
        missing_in_accounting_mask
    ]

    reconciliation.loc[
        missing_in_source_mask,
        "financial_exposure_usd",
    ] = accounting_amount[
        missing_in_source_mask
    ]

    transaction_value = pd.concat(
        [
            source_amount,
            accounting_amount,
        ],
        axis=1,
    ).max(axis=1)

    reconciliation.loc[
        duplicate_mask,
        "financial_exposure_usd",
    ] = transaction_value[
        duplicate_mask
    ]

    reconciliation.loc[
        mapping_error_mask,
        "financial_exposure_usd",
    ] = transaction_value[
        mapping_error_mask
    ]

    reconciliation.loc[
        period_mismatch_mask,
        "financial_exposure_usd",
    ] = transaction_value[
        period_mismatch_mask
    ]

    reconciliation[
        "financial_exposure_usd"
    ] = pd.to_numeric(
        reconciliation[
            "financial_exposure_usd"
        ],
        errors="coerce",
    ).fillna(0).round(2)

    return reconciliation


def assign_severity(
    reconciliation: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Assign severity using financial exposure."""

    low_max = (
        config[
            "severity"
        ][
            "low_max_usd"
        ]
    )

    medium_max = (
        config[
            "severity"
        ][
            "medium_max_usd"
        ]
    )

    high_max = (
        config[
            "severity"
        ][
            "high_max_usd"
        ]
    )

    exposure = pd.to_numeric(
        reconciliation[
            "financial_exposure_usd"
        ],
        errors="coerce",
    ).fillna(0)

    matched = (
        reconciliation[
            "reconciliation_status"
        ]
        == "MATCHED"
    )

    reconciliation[
        "severity"
    ] = np.select(
        [
            matched,
            exposure <= low_max,
            exposure <= medium_max,
            exposure <= high_max,
        ],
        [
            "NONE",
            "LOW",
            "MEDIUM",
            "HIGH",
        ],
        default="CRITICAL",
    )

    return reconciliation


def build_final_output(
    reconciliation: pd.DataFrame,
) -> pd.DataFrame:
    """Build the final reconciliation result table."""

    output = pd.DataFrame(
        {
            "transaction_id":
                reconciliation[
                    "transaction_id"
                ],

            "reconciliation_status":
                reconciliation[
                    "reconciliation_status"
                ],

            "severity":
                reconciliation[
                    "severity"
                ],

            "contract_id_source":
                reconciliation[
                    "contract_id_source"
                ],

            "contract_id_accounting":
                reconciliation[
                    "contract_id_accounting"
                ],

            "counterparty_id_source":
                reconciliation[
                    "counterparty_id_source"
                ],

            "counterparty_id_accounting":
                reconciliation[
                    "counterparty_id_accounting"
                ],

            "transaction_type_source":
                reconciliation[
                    "transaction_type_source"
                ],

            "transaction_type_accounting":
                reconciliation[
                    "transaction_type_accounting"
                ],

            "accounting_period_source":
                reconciliation[
                    "accounting_period_source"
                ],

            "accounting_period_accounting":
                reconciliation[
                    "accounting_period_accounting"
                ],

            "currency_source":
                reconciliation[
                    "currency_source"
                ],

            "currency_accounting":
                reconciliation[
                    "currency_accounting"
                ],

            "original_amount_source":
                reconciliation[
                    "original_amount_source"
                ],

            "original_amount_accounting":
                reconciliation[
                    "original_amount_accounting"
                ],

            "exchange_rate_source":
                reconciliation[
                    "exchange_rate_source"
                ],

            "exchange_rate_accounting":
                reconciliation[
                    "exchange_rate_accounting"
                ],

            "converted_amount_usd_source":
                reconciliation[
                    "converted_amount_usd_source"
                ],

            "converted_amount_usd_accounting":
                reconciliation[
                    "converted_amount_usd_accounting"
                ],

            "amount_difference_usd":
                reconciliation[
                    "amount_difference_usd"
                ],

            "absolute_difference_usd":
                reconciliation[
                    "absolute_difference_usd"
                ],

            "financial_exposure_usd":
                reconciliation[
                    "financial_exposure_usd"
                ],

            "relative_difference":
                reconciliation[
                    "relative_difference"
                ],

            "processing_timestamp_source":
                reconciliation[
                    "processing_timestamp_source"
                ],

            "processing_timestamp_accounting":
                reconciliation[
                    "processing_timestamp_accounting"
                ],

            "processing_delay_hours":
                reconciliation[
                    "processing_delay_hours"
                ],
        }
    )

    return (
        output
        .sort_values(
            [
                "reconciliation_status",
                "transaction_id",
            ]
        )
        .reset_index(drop=True)
    )


def validate_output(
    reconciliation_results: pd.DataFrame,
) -> None:
    """Validate structural properties of reconciliation results."""

    if reconciliation_results.empty:
        raise ValueError(
            "Reconciliation output is empty."
        )

    if not reconciliation_results[
        "transaction_id"
    ].is_unique:
        raise ValueError(
            "Final reconciliation results contain "
            "duplicate transaction IDs."
        )

    if reconciliation_results[
        "reconciliation_status"
    ].isna().any():
        raise ValueError(
            "Some transactions have no reconciliation status."
        )

    if reconciliation_results[
        "financial_exposure_usd"
    ].isna().any():
        raise ValueError(
            "Some transactions have no financial exposure value."
        )

    if (
        reconciliation_results[
            "financial_exposure_usd"
        ]
        < 0
    ).any():
        raise ValueError(
            "Financial exposure cannot be negative."
        )


def save_results(
    dataframe: pd.DataFrame,
    output_path: Path,
) -> None:
    """Save reconciliation results to CSV."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_csv(
        output_path,
        index=False,
    )


def print_summary(
    reconciliation_results: pd.DataFrame,
) -> None:
    """Print reconciliation execution summary."""

    total_transactions = len(
        reconciliation_results
    )

    status_counts = (
        reconciliation_results[
            "reconciliation_status"
        ]
        .value_counts()
    )

    severity_counts = (
        reconciliation_results[
            "severity"
        ]
        .value_counts()
    )

    matched_transactions = int(
        status_counts.get(
            "MATCHED",
            0,
        )
    )

    exception_transactions = (
        total_transactions
        - matched_transactions
    )

    match_rate = (
        matched_transactions
        / total_transactions
        * 100
    )

    total_exception_exposure = (
        reconciliation_results.loc[
            reconciliation_results[
                "reconciliation_status"
            ]
            != "MATCHED",
            "financial_exposure_usd",
        ]
        .sum()
    )

    print(
        "\nReconciliation completed successfully."
    )

    print(
        f"\nTransactions reconciled: "
        f"{total_transactions:,}"
    )

    print(
        f"Matched transactions: "
        f"{matched_transactions:,}"
    )

    print(
        f"Exception transactions: "
        f"{exception_transactions:,}"
    )

    print(
        f"Match rate: "
        f"{match_rate:.2f}%"
    )

    print(
        f"Total exception exposure: "
        f"${total_exception_exposure:,.2f}"
    )

    print(
        "\nReconciliation status distribution:"
    )

    print(status_counts)

    print(
        "\nSeverity distribution:"
    )

    print(severity_counts)


def main() -> None:
    """Execute the financial reconciliation pipeline."""

    config = load_config(
        CONFIG_PATH
    )

    source = load_transactions(
        SOURCE_PATH
    )

    accounting = load_transactions(
        ACCOUNTING_PATH
    )

    validate_schema(
        source,
        "Source",
    )

    validate_schema(
        accounting,
        "Accounting",
    )

    source_duplicate_ids = identify_duplicate_ids(
        source
    )

    accounting_duplicate_ids = identify_duplicate_ids(
        accounting
    )

    duplicate_ids = (
        source_duplicate_ids
        | accounting_duplicate_ids
    )

    reconciliation = build_reconciliation_dataset(
        source=source,
        accounting=accounting,
    )

    reconciliation = calculate_differences(
        reconciliation
    )

    reconciliation = classify_reconciliation_status(
        reconciliation=reconciliation,
        duplicate_ids=duplicate_ids,
        config=config,
    )

    reconciliation = calculate_financial_exposure(
        reconciliation
    )

    reconciliation = assign_severity(
        reconciliation=reconciliation,
        config=config,
    )

    reconciliation_results = build_final_output(
        reconciliation
    )

    validate_output(
        reconciliation_results
    )

    save_results(
        reconciliation_results,
        OUTPUT_PATH,
    )

    print_summary(
        reconciliation_results
    )

    print(
        f"\nOutput file: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()