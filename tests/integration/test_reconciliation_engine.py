from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RECONCILIATION_RESULTS_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "reconciliation_results.csv"
)

EXPECTED_ANOMALIES_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "expected_anomalies.csv"
)


@pytest.fixture
def reconciliation_results() -> pd.DataFrame:
    """Load reconciliation engine results."""
    return pd.read_csv(
        RECONCILIATION_RESULTS_PATH,
        dtype={
            "transaction_id": "string",
            "reconciliation_status": "string",
        },
    )


@pytest.fixture
def expected_anomalies() -> pd.DataFrame:
    """Load the known anomaly manifest."""
    return pd.read_csv(
        EXPECTED_ANOMALIES_PATH,
        dtype={
            "transaction_id": "string",
            "expected_status": "string",
        },
    )


def test_reconciliation_contains_50000_transactions(
    reconciliation_results: pd.DataFrame,
) -> None:
    """The engine must produce one result per transaction ID."""
    assert len(reconciliation_results) == 50000


def test_reconciliation_transaction_ids_are_unique(
    reconciliation_results: pd.DataFrame,
) -> None:
    """Final reconciliation table must have unique transaction IDs."""
    assert reconciliation_results[
        "transaction_id"
    ].is_unique


def test_total_detected_exception_count(
    reconciliation_results: pd.DataFrame,
    expected_anomalies: pd.DataFrame,
) -> None:
    """Detected exception total must equal expected anomaly total."""

    detected_exceptions = reconciliation_results[
        reconciliation_results["reconciliation_status"]
        != "MATCHED"
    ]

    assert len(detected_exceptions) == len(
        expected_anomalies
    )


def test_detected_exception_ids_match_expected_ids(
    reconciliation_results: pd.DataFrame,
    expected_anomalies: pd.DataFrame,
) -> None:
    """Every expected anomalous transaction must be detected."""

    detected_ids = set(
        reconciliation_results.loc[
            reconciliation_results[
                "reconciliation_status"
            ] != "MATCHED",
            "transaction_id",
        ]
    )

    expected_ids = set(
        expected_anomalies["transaction_id"]
    )

    assert detected_ids == expected_ids


def test_no_false_positive_exceptions(
    reconciliation_results: pd.DataFrame,
    expected_anomalies: pd.DataFrame,
) -> None:
    """No clean transaction may be incorrectly classified as an exception."""

    expected_ids = set(
        expected_anomalies["transaction_id"]
    )

    detected_exception_ids = set(
        reconciliation_results.loc[
            reconciliation_results[
                "reconciliation_status"
            ] != "MATCHED",
            "transaction_id",
        ]
    )

    false_positives = (
        detected_exception_ids
        - expected_ids
    )

    assert false_positives == set()


def test_no_false_negative_exceptions(
    reconciliation_results: pd.DataFrame,
    expected_anomalies: pd.DataFrame,
) -> None:
    """No known anomaly may be incorrectly classified as matched."""

    expected_ids = set(
        expected_anomalies["transaction_id"]
    )

    matched_ids = set(
        reconciliation_results.loc[
            reconciliation_results[
                "reconciliation_status"
            ] == "MATCHED",
            "transaction_id",
        ]
    )

    false_negatives = (
        expected_ids
        & matched_ids
    )

    assert false_negatives == set()


def test_exact_status_classification(
    reconciliation_results: pd.DataFrame,
    expected_anomalies: pd.DataFrame,
) -> None:
    """
    Every anomalous transaction must receive exactly
    the expected reconciliation status.
    """

    detected = reconciliation_results[
        [
            "transaction_id",
            "reconciliation_status",
        ]
    ]

    comparison = expected_anomalies[
        [
            "transaction_id",
            "expected_status",
        ]
    ].merge(
        detected,
        on="transaction_id",
        how="left",
        validate="one_to_one",
    )

    incorrect_classifications = comparison[
        comparison["expected_status"]
        != comparison["reconciliation_status"]
    ]

    assert incorrect_classifications.empty, (
        "\nIncorrect classifications found:\n"
        f"{incorrect_classifications.to_string(index=False)}"
    )


def test_exact_status_distribution(
    reconciliation_results: pd.DataFrame,
    expected_anomalies: pd.DataFrame,
) -> None:
    """Detected exception distribution must match expected distribution."""

    expected_distribution = (
        expected_anomalies["expected_status"]
        .value_counts()
        .sort_index()
    )

    detected_distribution = (
        reconciliation_results.loc[
            reconciliation_results[
                "reconciliation_status"
            ] != "MATCHED",
            "reconciliation_status",
        ]
        .value_counts()
        .sort_index()
    )

    pd.testing.assert_series_equal(
        detected_distribution,
        expected_distribution,
        check_names=False,
    )


def test_match_rate_is_95_percent(
    reconciliation_results: pd.DataFrame,
) -> None:
    """Synthetic reconciliation scenario should produce a 95% match rate."""

    total_transactions = len(
        reconciliation_results
    )

    matched_transactions = (
        reconciliation_results[
            "reconciliation_status"
        ]
        .eq("MATCHED")
        .sum()
    )

    match_rate = (
        matched_transactions
        / total_transactions
    )

    assert match_rate == pytest.approx(
        0.95,
        abs=0.000001,
    )