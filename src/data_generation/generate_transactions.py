from pathlib import Path

import numpy as np
import pandas as pd
import yaml


CONFIG_PATH = Path("configs/data_generation.yml")
OUTPUT_PATH = Path("data/processed/ground_truth_transactions.csv")


def load_config(config_path: Path) -> dict:
    """Load synthetic data generation settings from a YAML file."""
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def generate_ids(
    prefix: str,
    count: int,
    width: int = 6,
) -> list[str]:
    """Generate sequential identifiers with a fixed-width numeric suffix."""
    return [
        f"{prefix}{number:0{width}d}"
        for number in range(1, count + 1)
    ]


def generate_dates(
    rng: np.random.Generator,
    start_date: str,
    end_date: str,
    count: int,
) -> pd.DatetimeIndex:
    """Generate random dates within a specified date range."""
    date_range = pd.date_range(
        start=start_date,
        end=end_date,
        freq="D",
    )

    return pd.DatetimeIndex(
        rng.choice(date_range, size=count)
    )


def generate_processing_timestamps(
    rng: np.random.Generator,
    transaction_dates: pd.DatetimeIndex,
) -> pd.DatetimeIndex:
    """Generate processing timestamps up to 72 hours after transaction date."""
    hours_after_transaction = rng.integers(
        low=0,
        high=73,
        size=len(transaction_dates),
    )

    minutes_after_hour = rng.integers(
        low=0,
        high=60,
        size=len(transaction_dates),
    )

    processing_timestamps = (
        transaction_dates
        + pd.to_timedelta(hours_after_transaction, unit="h")
        + pd.to_timedelta(minutes_after_hour, unit="m")
    )

    return pd.DatetimeIndex(processing_timestamps)


def generate_amounts(
    rng: np.random.Generator,
    transaction_types: np.ndarray,
) -> np.ndarray:
    """Generate synthetic amounts based on transaction type."""
    amounts = np.empty(len(transaction_types))

    for transaction_type in ["PREMIUM", "CLAIM", "COMMISSION"]:
        mask = transaction_types == transaction_type
        count = mask.sum()

        if transaction_type == "PREMIUM":
            amounts[mask] = rng.lognormal(
                mean=9.0,
                sigma=0.8,
                size=count,
            )

        elif transaction_type == "CLAIM":
            amounts[mask] = rng.lognormal(
                mean=9.5,
                sigma=1.0,
                size=count,
            )

        elif transaction_type == "COMMISSION":
            amounts[mask] = rng.lognormal(
                mean=7.5,
                sigma=0.6,
                size=count,
            )

    return np.round(amounts, 2)


def generate_transactions(config: dict) -> pd.DataFrame:
    """Generate the clean synthetic ground-truth transaction dataset."""
    random_seed = config["random_seed"]

    number_of_transactions = (
        config["dataset"]["number_of_transactions"]
    )

    number_of_contracts = (
        config["dataset"]["number_of_contracts"]
    )

    number_of_counterparties = (
        config["dataset"]["number_of_counterparties"]
    )

    rng = np.random.default_rng(random_seed)

    transaction_ids = generate_ids(
        prefix="TX",
        count=number_of_transactions,
    )

    contract_ids = generate_ids(
        prefix="CTR",
        count=number_of_contracts,
        width=4,
    )

    counterparty_ids = generate_ids(
        prefix="CP",
        count=number_of_counterparties,
        width=3,
    )

    # Each contract belongs to one counterparty.
    contract_to_counterparty = {
        contract_id: rng.choice(counterparty_ids)
        for contract_id in contract_ids
    }

    selected_contract_ids = rng.choice(
        contract_ids,
        size=number_of_transactions,
    )

    selected_counterparty_ids = np.array(
        [
            contract_to_counterparty[contract_id]
            for contract_id in selected_contract_ids
        ]
    )

    transaction_types = rng.choice(
        config["transaction_types"],
        size=number_of_transactions,
    )

    currencies = rng.choice(
        config["currencies"],
        size=number_of_transactions,
    )

    transaction_dates = generate_dates(
        rng=rng,
        start_date=config["date_range"]["start_date"],
        end_date=config["date_range"]["end_date"],
        count=number_of_transactions,
    )

    accounting_periods = (
        pd.Series(transaction_dates)
        .dt.to_period("M")
        .astype(str)
        .to_numpy()
    )

    processing_timestamps = generate_processing_timestamps(
        rng=rng,
        transaction_dates=transaction_dates,
    )

    original_amounts = generate_amounts(
        rng=rng,
        transaction_types=transaction_types,
    )

    exchange_rates = np.array(
        [
            config["exchange_rates_to_usd"][currency]
            for currency in currencies
        ]
    )

    converted_amounts_usd = np.round(
        original_amounts * exchange_rates,
        2,
    )

    transactions = pd.DataFrame(
        {
            "transaction_id": transaction_ids,
            "contract_id": selected_contract_ids,
            "counterparty_id": selected_counterparty_ids,
            "transaction_type": transaction_types,
            "accounting_period": accounting_periods,
            "transaction_date": transaction_dates,
            "currency": currencies,
            "original_amount": original_amounts,
            "exchange_rate": exchange_rates,
            "converted_amount_usd": converted_amounts_usd,
            "processing_timestamp": processing_timestamps,
        }
    )

    return transactions


def validate_generated_data(
    transactions: pd.DataFrame,
    expected_rows: int,
) -> None:
    """Validate key business and data-quality rules."""
    max_counterparties_per_contract = (
        transactions
        .groupby("contract_id")["counterparty_id"]
        .nunique()
        .max()
    )

    duplicate_transaction_ids = (
        transactions["transaction_id"]
        .duplicated()
        .sum()
    )

    missing_values = transactions.isna().sum().sum()

    invalid_processing_timestamps = (
        transactions["processing_timestamp"]
        < transactions["transaction_date"]
    ).sum()

    if len(transactions) != expected_rows:
        raise ValueError(
            f"Expected {expected_rows} rows, "
            f"but generated {len(transactions)}."
        )

    if duplicate_transaction_ids > 0:
        raise ValueError(
            "Duplicate transaction IDs were generated."
        )

    if missing_values > 0:
        raise ValueError(
            "Missing values were found in the generated dataset."
        )

    if max_counterparties_per_contract != 1:
        raise ValueError(
            "A contract was assigned to multiple counterparties."
        )

    if invalid_processing_timestamps > 0:
        raise ValueError(
            "Processing timestamp occurred before transaction date."
        )


def save_transactions(
    transactions: pd.DataFrame,
    output_path: Path,
) -> None:
    """Save generated transactions to CSV."""
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    transactions.to_csv(
        output_path,
        index=False,
    )


def main() -> None:
    """Generate, validate and save the ground-truth dataset."""
    config = load_config(CONFIG_PATH)

    transactions = generate_transactions(config)

    expected_rows = (
        config["dataset"]["number_of_transactions"]
    )

    validate_generated_data(
        transactions=transactions,
        expected_rows=expected_rows,
    )

    save_transactions(
        transactions=transactions,
        output_path=OUTPUT_PATH,
    )

    print("\nSynthetic data generation completed successfully.")

    print(f"\nRows generated: {len(transactions):,}")

    print(f"Columns generated: {len(transactions.columns)}")

    print(f"Output file: {OUTPUT_PATH}")

    print("\nSample transactions:")
    print(transactions.head(10))

    print("\nTransaction type distribution:")
    print(
        transactions["transaction_type"]
        .value_counts()
    )

    print("\nCurrency distribution:")
    print(
        transactions["currency"]
        .value_counts()
    )


if __name__ == "__main__":
    main()