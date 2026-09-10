from pathlib import Path

import pandas as pd
import pytest
import yaml


GROUND_TRUTH_PATH = Path(
    "data/processed/ground_truth_transactions.csv"
)

SOURCE_PATH = Path(
    "data/raw/source_transactions.csv"
)

ACCOUNTING_PATH = Path(
    "data/raw/accounting_transactions.csv"
)

ANOMALY_MANIFEST_PATH = Path(
    "data/processed/expected_anomalies.csv"
)

CONFIG_PATH = Path(
    "configs/anomaly_generation.yml"
)


@pytest.fixture
def ground_truth() -> pd.DataFrame:
    """Load the clean ground-truth dataset."""
    return pd.read_csv(GROUND_TRUTH_PATH)


@pytest.fixture
def source() -> pd.DataFrame:
    """Load the simulated source-system dataset."""
    return pd.read_csv(SOURCE_PATH)


@pytest.fixture
def accounting() -> pd.DataFrame:
    """Load the simulated accounting-system dataset."""
    return pd.read_csv(ACCOUNTING_PATH)


@pytest.fixture
def anomaly_manifest() -> pd.DataFrame:
    """Load the expected anomaly manifest."""
    return pd.read_csv(ANOMALY_MANIFEST_PATH)


@pytest.fixture
def config() -> dict:
    """Load anomaly-generation configuration."""
    with CONFIG_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return yaml.safe_load(file)


def test_ground_truth_has_unique_transaction_ids(
    ground_truth: pd.DataFrame,
) -> None:
    """Ground truth must contain unique transaction IDs."""
    assert ground_truth["transaction_id"].is_unique


def test_source_missing_transaction_count(
    ground_truth: pd.DataFrame,
    source: pd.DataFrame,
    config: dict,
) -> None:
    """Source row reduction must match configured missing records."""
    expected_missing = (
        config["anomalies"]["missing_in_source"]["count"]
    )

    assert len(ground_truth) - len(source) == expected_missing


def test_accounting_row_count(
    ground_truth: pd.DataFrame,
    accounting: pd.DataFrame,
    config: dict,
) -> None:
    """Accounting row count must reflect removals and duplicates."""
    missing_count = (
        config["anomalies"]["missing_in_accounting"]["count"]
    )

    duplicate_count = (
        config["anomalies"]["duplicate_transaction"]["count"]
    )

    expected_rows = (
        len(ground_truth)
        - missing_count
        + duplicate_count
    )

    assert len(accounting) == expected_rows


def test_accounting_duplicate_count(
    accounting: pd.DataFrame,
    config: dict,
) -> None:
    """Accounting duplicate count must match configuration."""
    expected_duplicates = (
        config["anomalies"]["duplicate_transaction"]["count"]
    )

    actual_duplicates = accounting.duplicated(
        subset=["transaction_id"],
        keep="first",
    ).sum()

    assert actual_duplicates == expected_duplicates


def test_manifest_total_anomaly_count(
    anomaly_manifest: pd.DataFrame,
    config: dict,
) -> None:
    """Manifest total must equal all configured anomaly counts."""
    expected_total = sum(
        settings["count"]
        for settings in config["anomalies"].values()
    )

    assert len(anomaly_manifest) == expected_total


def test_manifest_transaction_ids_are_unique(
    anomaly_manifest: pd.DataFrame,
) -> None:
    """Each transaction must have one expected anomaly."""
    assert anomaly_manifest["transaction_id"].is_unique


def test_manifest_distribution_matches_config(
    anomaly_manifest: pd.DataFrame,
    config: dict,
) -> None:
    """Manifest status counts must match configured anomaly counts."""

    expected_counts = {
        "AMOUNT_MISMATCH":
            config["anomalies"]["amount_mismatch"]["count"],

        "MISSING_IN_ACCOUNTING":
            config["anomalies"]["missing_in_accounting"]["count"],

        "MISSING_IN_SOURCE":
            config["anomalies"]["missing_in_source"]["count"],

        "DUPLICATE_TRANSACTION":
            config["anomalies"]["duplicate_transaction"]["count"],

        "FX_DIFFERENCE":
            config["anomalies"]["fx_difference"]["count"],

        "PERIOD_MISMATCH":
            config["anomalies"]["period_mismatch"]["count"],

        "MAPPING_ERROR":
            config["anomalies"]["mapping_error"]["count"],

        "REPROCESSED_TRANSACTION":
            config["anomalies"]["reprocessed_transaction"]["count"],
    }

    actual_counts = (
        anomaly_manifest["expected_status"]
        .value_counts()
        .to_dict()
    )

    assert actual_counts == expected_counts


def test_missing_in_source_transactions_are_absent(
    source: pd.DataFrame,
    anomaly_manifest: pd.DataFrame,
) -> None:
    """Transactions marked missing in source must not exist there."""

    expected_missing_ids = set(
        anomaly_manifest.loc[
            anomaly_manifest["expected_status"]
            == "MISSING_IN_SOURCE",
            "transaction_id",
        ]
    )

    source_ids = set(source["transaction_id"])

    assert expected_missing_ids.isdisjoint(source_ids)


def test_missing_in_accounting_transactions_are_absent(
    accounting: pd.DataFrame,
    anomaly_manifest: pd.DataFrame,
) -> None:
    """Transactions marked missing in accounting must not exist there."""

    expected_missing_ids = set(
        anomaly_manifest.loc[
            anomaly_manifest["expected_status"]
            == "MISSING_IN_ACCOUNTING",
            "transaction_id",
        ]
    )

    accounting_ids = set(accounting["transaction_id"])

    assert expected_missing_ids.isdisjoint(accounting_ids)