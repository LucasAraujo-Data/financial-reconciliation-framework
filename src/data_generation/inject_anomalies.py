from pathlib import Path

import numpy as np
import pandas as pd
import yaml


GROUND_TRUTH_PATH = Path(
    "data/processed/ground_truth_transactions.csv"
)

CONFIG_PATH = Path(
    "configs/anomaly_generation.yml"
)

SOURCE_OUTPUT_PATH = Path(
    "data/raw/source_transactions.csv"
)

ACCOUNTING_OUTPUT_PATH = Path(
    "data/raw/accounting_transactions.csv"
)

ANOMALY_OUTPUT_PATH = Path(
    "data/processed/expected_anomalies.csv"
)


def load_config(config_path: Path) -> dict:
    """Load anomaly generation settings from YAML."""
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_ground_truth(path: Path) -> pd.DataFrame:
    """Load the clean synthetic ground-truth dataset."""
    return pd.read_csv(
        path,
        parse_dates=[
            "transaction_date",
            "processing_timestamp",
        ],
    )


def select_transactions(
    available_ids: set[str],
    count: int,
    rng: np.random.Generator,
) -> list[str]:
    """Select transaction IDs without reusing previous selections."""

    if count > len(available_ids):
        raise ValueError(
            "Not enough available transactions "
            "to inject the requested anomalies."
        )

    candidates = sorted(available_ids)

    selected = rng.choice(
        candidates,
        size=count,
        replace=False,
    ).tolist()

    available_ids.difference_update(selected)

    return selected


def create_manifest_records(
    transaction_ids: list[str],
    anomaly_type: str,
    affected_system: str,
) -> list[dict]:
    """Create expected anomaly manifest records."""

    return [
        {
            "transaction_id": transaction_id,
            "expected_status": anomaly_type,
            "affected_system": affected_system,
        }
        for transaction_id in transaction_ids
    ]


def inject_amount_mismatch(
    accounting: pd.DataFrame,
    transaction_ids: list[str],
    rng: np.random.Generator,
    min_change: float,
    max_change: float,
) -> None:
    """Modify accounting transaction amounts."""

    mask = accounting["transaction_id"].isin(transaction_ids)

    changes = rng.uniform(
        min_change,
        max_change,
        size=mask.sum(),
    )

    directions = rng.choice(
        [-1, 1],
        size=mask.sum(),
    )

    factors = 1 + (changes * directions)

    accounting.loc[mask, "original_amount"] = np.round(
        accounting.loc[mask, "original_amount"].to_numpy()
        * factors,
        2,
    )

    accounting.loc[mask, "converted_amount_usd"] = np.round(
        accounting.loc[mask, "original_amount"].to_numpy()
        * accounting.loc[mask, "exchange_rate"].to_numpy(),
        2,
    )


def inject_fx_difference(
    accounting: pd.DataFrame,
    transaction_ids: list[str],
    rng: np.random.Generator,
    min_change: float,
    max_change: float,
) -> None:
    """Modify exchange rates in the accounting system."""

    mask = accounting["transaction_id"].isin(transaction_ids)

    changes = rng.uniform(
        min_change,
        max_change,
        size=mask.sum(),
    )

    directions = rng.choice(
        [-1, 1],
        size=mask.sum(),
    )

    factors = 1 + (changes * directions)

    accounting.loc[mask, "exchange_rate"] = np.round(
        accounting.loc[mask, "exchange_rate"].to_numpy()
        * factors,
        6,
    )

    accounting.loc[mask, "converted_amount_usd"] = np.round(
        accounting.loc[mask, "original_amount"].to_numpy()
        * accounting.loc[mask, "exchange_rate"].to_numpy(),
        2,
    )


def inject_period_mismatch(
    accounting: pd.DataFrame,
    transaction_ids: list[str],
) -> None:
    """Move selected accounting records to the following period."""

    mask = accounting["transaction_id"].isin(transaction_ids)

    periods = pd.PeriodIndex(
        accounting.loc[mask, "accounting_period"],
        freq="M",
    )

    accounting.loc[mask, "accounting_period"] = (
        periods + 1
    ).astype(str)


def inject_mapping_error(
    accounting: pd.DataFrame,
    transaction_ids: list[str],
    rng: np.random.Generator,
) -> None:
    """Assign an incorrect counterparty to selected transactions."""

    counterparties = (
        accounting["counterparty_id"]
        .dropna()
        .unique()
    )

    for transaction_id in transaction_ids:

        mask = accounting["transaction_id"] == transaction_id

        current_counterparty = accounting.loc[
            mask,
            "counterparty_id",
        ].iloc[0]

        alternatives = counterparties[
            counterparties != current_counterparty
        ]

        accounting.loc[
            mask,
            "counterparty_id",
        ] = rng.choice(alternatives)


def inject_reprocessed_transaction(
    accounting: pd.DataFrame,
    transaction_ids: list[str],
) -> None:
    """Move processing timestamps forward for reprocessed records."""

    mask = accounting["transaction_id"].isin(transaction_ids)

    accounting.loc[mask, "processing_timestamp"] = (
        accounting.loc[mask, "processing_timestamp"]
        + pd.Timedelta(days=7)
    )


def inject_duplicate_transactions(
    accounting: pd.DataFrame,
    transaction_ids: list[str],
) -> pd.DataFrame:
    """Duplicate selected accounting records."""

    duplicates = accounting[
        accounting["transaction_id"].isin(transaction_ids)
    ].copy()

    return pd.concat(
        [accounting, duplicates],
        ignore_index=True,
    )


def save_dataset(
    dataframe: pd.DataFrame,
    output_path: Path,
) -> None:
    """Save a DataFrame to CSV."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_csv(
        output_path,
        index=False,
    )


def main() -> None:
    """Generate source and accounting datasets with known anomalies."""

    config = load_config(CONFIG_PATH)

    ground_truth = load_ground_truth(
        GROUND_TRUTH_PATH
    )

    source = ground_truth.copy()
    accounting = ground_truth.copy()

    rng = np.random.default_rng(
        config["random_seed"]
    )

    available_ids = set(
        ground_truth["transaction_id"]
    )

    manifest_records = []

    # --------------------------------------------------------------
    # Amount mismatch
    # --------------------------------------------------------------

    settings = config["anomalies"]["amount_mismatch"]

    selected_ids = select_transactions(
        available_ids,
        settings["count"],
        rng,
    )

    inject_amount_mismatch(
        accounting=accounting,
        transaction_ids=selected_ids,
        rng=rng,
        min_change=settings["min_change_percentage"],
        max_change=settings["max_change_percentage"],
    )

    manifest_records.extend(
        create_manifest_records(
            selected_ids,
            "AMOUNT_MISMATCH",
            "ACCOUNTING",
        )
    )

    # --------------------------------------------------------------
    # Missing in accounting
    # --------------------------------------------------------------

    settings = config["anomalies"]["missing_in_accounting"]

    selected_ids = select_transactions(
        available_ids,
        settings["count"],
        rng,
    )

    accounting = accounting[
        ~accounting["transaction_id"].isin(selected_ids)
    ].copy()

    manifest_records.extend(
        create_manifest_records(
            selected_ids,
            "MISSING_IN_ACCOUNTING",
            "ACCOUNTING",
        )
    )

    # --------------------------------------------------------------
    # Missing in source
    # --------------------------------------------------------------

    settings = config["anomalies"]["missing_in_source"]

    selected_ids = select_transactions(
        available_ids,
        settings["count"],
        rng,
    )

    source = source[
        ~source["transaction_id"].isin(selected_ids)
    ].copy()

    manifest_records.extend(
        create_manifest_records(
            selected_ids,
            "MISSING_IN_SOURCE",
            "SOURCE",
        )
    )

    # --------------------------------------------------------------
    # Duplicate transaction
    # --------------------------------------------------------------

    settings = config["anomalies"]["duplicate_transaction"]

    selected_ids = select_transactions(
        available_ids,
        settings["count"],
        rng,
    )

    accounting = inject_duplicate_transactions(
        accounting,
        selected_ids,
    )

    manifest_records.extend(
        create_manifest_records(
            selected_ids,
            "DUPLICATE_TRANSACTION",
            "ACCOUNTING",
        )
    )

    # --------------------------------------------------------------
    # FX difference
    # --------------------------------------------------------------

    settings = config["anomalies"]["fx_difference"]

    selected_ids = select_transactions(
        available_ids,
        settings["count"],
        rng,
    )

    inject_fx_difference(
        accounting=accounting,
        transaction_ids=selected_ids,
        rng=rng,
        min_change=settings["min_change_percentage"],
        max_change=settings["max_change_percentage"],
    )

    manifest_records.extend(
        create_manifest_records(
            selected_ids,
            "FX_DIFFERENCE",
            "ACCOUNTING",
        )
    )

    # --------------------------------------------------------------
    # Accounting period mismatch
    # --------------------------------------------------------------

    settings = config["anomalies"]["period_mismatch"]

    selected_ids = select_transactions(
        available_ids,
        settings["count"],
        rng,
    )

    inject_period_mismatch(
        accounting,
        selected_ids,
    )

    manifest_records.extend(
        create_manifest_records(
            selected_ids,
            "PERIOD_MISMATCH",
            "ACCOUNTING",
        )
    )

    # --------------------------------------------------------------
    # Mapping error
    # --------------------------------------------------------------

    settings = config["anomalies"]["mapping_error"]

    selected_ids = select_transactions(
        available_ids,
        settings["count"],
        rng,
    )

    inject_mapping_error(
        accounting,
        selected_ids,
        rng,
    )

    manifest_records.extend(
        create_manifest_records(
            selected_ids,
            "MAPPING_ERROR",
            "ACCOUNTING",
        )
    )

    # --------------------------------------------------------------
    # Reprocessed transaction
    # --------------------------------------------------------------

    settings = config["anomalies"]["reprocessed_transaction"]

    selected_ids = select_transactions(
        available_ids,
        settings["count"],
        rng,
    )

    inject_reprocessed_transaction(
        accounting,
        selected_ids,
    )

    manifest_records.extend(
        create_manifest_records(
            selected_ids,
            "REPROCESSED_TRANSACTION",
            "ACCOUNTING",
        )
    )

    # --------------------------------------------------------------
    # Build expected anomaly manifest
    # --------------------------------------------------------------

    anomaly_manifest = pd.DataFrame(
        manifest_records
    ).sort_values(
        ["expected_status", "transaction_id"]
    )

    # --------------------------------------------------------------
    # Save datasets
    # --------------------------------------------------------------

    save_dataset(
        source,
        SOURCE_OUTPUT_PATH,
    )

    save_dataset(
        accounting,
        ACCOUNTING_OUTPUT_PATH,
    )

    save_dataset(
        anomaly_manifest,
        ANOMALY_OUTPUT_PATH,
    )

    # --------------------------------------------------------------
    # Execution summary
    # --------------------------------------------------------------

    print(
        "\nAnomaly injection completed successfully."
    )

    print(
        f"\nGround truth rows: {len(ground_truth):,}"
    )

    print(
        f"Source system rows: {len(source):,}"
    )

    print(
        f"Accounting system rows: {len(accounting):,}"
    )

    print(
        f"Expected anomalies: {len(anomaly_manifest):,}"
    )

    print("\nExpected anomaly distribution:")

    print(
        anomaly_manifest["expected_status"]
        .value_counts()
    )


if __name__ == "__main__":
    main()