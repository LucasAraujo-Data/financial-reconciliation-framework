from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RECONCILIATION_RESULTS_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "reconciliation_results.csv"
)

OVERALL_SUMMARY_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "reconciliation_summary.csv"
)

STATUS_SUMMARY_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "exception_summary_by_status.csv"
)

SEVERITY_SUMMARY_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "exception_summary_by_severity.csv"
)


def load_reconciliation_results(
    path: Path,
) -> pd.DataFrame:
    """Load reconciliation results."""
    return pd.read_csv(path)


def validate_input(
    dataframe: pd.DataFrame,
) -> None:
    """Validate columns required by the reporting layer."""

    required_columns = [
        "transaction_id",
        "reconciliation_status",
        "severity",
        "financial_exposure_usd",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Reconciliation results are missing "
            f"required columns: {missing_columns}"
        )

    if dataframe.empty:
        raise ValueError(
            "Reconciliation results are empty."
        )


def build_overall_summary(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate executive reconciliation KPIs."""

    total_transactions = len(dataframe)

    matched_transactions = (
        dataframe[
            "reconciliation_status"
        ]
        .eq("MATCHED")
        .sum()
    )

    exception_transactions = (
        total_transactions
        - matched_transactions
    )

    match_rate = (
        matched_transactions
        / total_transactions
    )

    exception_rate = (
        exception_transactions
        / total_transactions
    )

    exceptions = dataframe[
        dataframe[
            "reconciliation_status"
        ]
        != "MATCHED"
    ]

    total_exception_exposure = (
        exceptions[
            "financial_exposure_usd"
        ]
        .sum()
    )

    critical_exceptions = (
        exceptions[
            "severity"
        ]
        .eq("CRITICAL")
        .sum()
    )

    high_exceptions = (
        exceptions[
            "severity"
        ]
        .eq("HIGH")
        .sum()
    )

    material_exceptions = (
        exceptions[
            "severity"
        ]
        .isin(
            [
                "HIGH",
                "CRITICAL",
            ]
        )
        .sum()
    )

    material_exposure = (
        exceptions.loc[
            exceptions[
                "severity"
            ].isin(
                [
                    "HIGH",
                    "CRITICAL",
                ]
            ),
            "financial_exposure_usd",
        ]
        .sum()
    )

    average_exception_exposure = (
        total_exception_exposure
        / exception_transactions
        if exception_transactions > 0
        else 0
    )

    summary = pd.DataFrame(
        [
            {
                "total_transactions":
                    total_transactions,

                "matched_transactions":
                    matched_transactions,

                "exception_transactions":
                    exception_transactions,

                "match_rate":
                    round(match_rate, 6),

                "exception_rate":
                    round(exception_rate, 6),

                "total_exception_exposure_usd":
                    round(
                        total_exception_exposure,
                        2,
                    ),

                "average_exception_exposure_usd":
                    round(
                        average_exception_exposure,
                        2,
                    ),

                "high_exceptions":
                    high_exceptions,

                "critical_exceptions":
                    critical_exceptions,

                "material_exceptions":
                    material_exceptions,

                "material_exposure_usd":
                    round(
                        material_exposure,
                        2,
                    ),
            }
        ]
    )

    return summary


def build_status_summary(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize exceptions by reconciliation status."""

    exceptions = dataframe[
        dataframe[
            "reconciliation_status"
        ]
        != "MATCHED"
    ].copy()

    summary = (
        exceptions
        .groupby(
            "reconciliation_status",
            as_index=False,
        )
        .agg(
            exception_count=(
                "transaction_id",
                "count",
            ),
            total_exposure_usd=(
                "financial_exposure_usd",
                "sum",
            ),
            average_exposure_usd=(
                "financial_exposure_usd",
                "mean",
            ),
            maximum_exposure_usd=(
                "financial_exposure_usd",
                "max",
            ),
        )
    )

    total_exceptions = len(exceptions)

    summary[
        "exception_percentage"
    ] = (
        summary[
            "exception_count"
        ]
        / total_exceptions
    )

    summary[
        "total_exposure_usd"
    ] = (
        summary[
            "total_exposure_usd"
        ]
        .round(2)
    )

    summary[
        "average_exposure_usd"
    ] = (
        summary[
            "average_exposure_usd"
        ]
        .round(2)
    )

    summary[
        "maximum_exposure_usd"
    ] = (
        summary[
            "maximum_exposure_usd"
        ]
        .round(2)
    )

    summary[
        "exception_percentage"
    ] = (
        summary[
            "exception_percentage"
        ]
        .round(6)
    )

    return (
        summary
        .sort_values(
            "total_exposure_usd",
            ascending=False,
        )
        .reset_index(drop=True)
    )


def build_severity_summary(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize exceptions by severity."""

    exceptions = dataframe[
        dataframe[
            "reconciliation_status"
        ]
        != "MATCHED"
    ].copy()

    summary = (
        exceptions
        .groupby(
            "severity",
            as_index=False,
        )
        .agg(
            exception_count=(
                "transaction_id",
                "count",
            ),
            total_exposure_usd=(
                "financial_exposure_usd",
                "sum",
            ),
            average_exposure_usd=(
                "financial_exposure_usd",
                "mean",
            ),
            maximum_exposure_usd=(
                "financial_exposure_usd",
                "max",
            ),
        )
    )

    severity_order = {
        "CRITICAL": 1,
        "HIGH": 2,
        "MEDIUM": 3,
        "LOW": 4,
    }

    summary[
        "severity_order"
    ] = (
        summary[
            "severity"
        ]
        .map(severity_order)
    )

    summary[
        "total_exposure_usd"
    ] = (
        summary[
            "total_exposure_usd"
        ]
        .round(2)
    )

    summary[
        "average_exposure_usd"
    ] = (
        summary[
            "average_exposure_usd"
        ]
        .round(2)
    )

    summary[
        "maximum_exposure_usd"
    ] = (
        summary[
            "maximum_exposure_usd"
        ]
        .round(2)
    )

    return (
        summary
        .sort_values(
            "severity_order"
        )
        .drop(
            columns=[
                "severity_order"
            ]
        )
        .reset_index(drop=True)
    )


def save_dataframe(
    dataframe: pd.DataFrame,
    path: Path,
) -> None:
    """Save reporting dataset to CSV."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_csv(
        path,
        index=False,
    )


def print_summary(
    overall_summary: pd.DataFrame,
    status_summary: pd.DataFrame,
    severity_summary: pd.DataFrame,
) -> None:
    """Print reporting results."""

    row = overall_summary.iloc[0]

    print(
        "\nReporting layer generated successfully."
    )

    print(
        f"\nTotal transactions: "
        f"{int(row['total_transactions']):,}"
    )

    print(
        f"Matched transactions: "
        f"{int(row['matched_transactions']):,}"
    )

    print(
        f"Exception transactions: "
        f"{int(row['exception_transactions']):,}"
    )

    print(
        f"Match rate: "
        f"{row['match_rate']:.2%}"
    )

    print(
        f"Total exception exposure: "
        f"${row['total_exception_exposure_usd']:,.2f}"
    )

    print(
        f"Material exposure: "
        f"${row['material_exposure_usd']:,.2f}"
    )

    print(
        "\nExceptions by status:"
    )

    print(
        status_summary.to_string(
            index=False
        )
    )

    print(
        "\nExceptions by severity:"
    )

    print(
        severity_summary.to_string(
            index=False
        )
    )


def main() -> None:
    """Generate reporting datasets."""

    reconciliation_results = (
        load_reconciliation_results(
            RECONCILIATION_RESULTS_PATH
        )
    )

    validate_input(
        reconciliation_results
    )

    overall_summary = (
        build_overall_summary(
            reconciliation_results
        )
    )

    status_summary = (
        build_status_summary(
            reconciliation_results
        )
    )

    severity_summary = (
        build_severity_summary(
            reconciliation_results
        )
    )

    save_dataframe(
        overall_summary,
        OVERALL_SUMMARY_PATH,
    )

    save_dataframe(
        status_summary,
        STATUS_SUMMARY_PATH,
    )

    save_dataframe(
        severity_summary,
        SEVERITY_SUMMARY_PATH,
    )

    print_summary(
        overall_summary,
        status_summary,
        severity_summary,
    )


if __name__ == "__main__":
    main()