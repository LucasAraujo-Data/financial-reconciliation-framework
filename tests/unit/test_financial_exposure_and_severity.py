import pandas as pd
import pytest

from src.reconciliation.reconciliation_engine import (
    assign_severity,
    calculate_financial_exposure,
)


@pytest.fixture
def severity_config() -> dict:
    """Provide severity thresholds used by the reconciliation engine."""
    return {
        "severity": {
            "low_max_usd": 100,
            "medium_max_usd": 10000,
            "high_max_usd": 100000,
        }
    }


def build_reconciliation_row(
    status: str,
    source_amount: float | None = None,
    accounting_amount: float | None = None,
    absolute_difference: float | None = None,
) -> pd.DataFrame:
    """
    Build a minimal reconciliation DataFrame for unit testing.
    """

    return pd.DataFrame(
        {
            "reconciliation_status": [status],
            "converted_amount_usd_source": [
                source_amount
            ],
            "converted_amount_usd_accounting": [
                accounting_amount
            ],
            "absolute_difference_usd": [
                absolute_difference
            ],
        }
    )


def test_matched_transaction_has_zero_exposure() -> None:
    """
    Matched transactions must not create financial exposure.
    """

    dataframe = build_reconciliation_row(
        status="MATCHED",
        source_amount=50000,
        accounting_amount=50000,
        absolute_difference=0,
    )

    result = calculate_financial_exposure(
        dataframe
    )

    assert (
        result.loc[
            0,
            "financial_exposure_usd",
        ]
        == 0
    )


def test_missing_in_accounting_uses_source_amount() -> None:
    """
    A record missing from Accounting must expose the Source amount.
    """

    dataframe = build_reconciliation_row(
        status="MISSING_IN_ACCOUNTING",
        source_amount=50000,
        accounting_amount=None,
        absolute_difference=None,
    )

    result = calculate_financial_exposure(
        dataframe
    )

    assert (
        result.loc[
            0,
            "financial_exposure_usd",
        ]
        == 50000
    )


def test_missing_in_source_uses_accounting_amount() -> None:
    """
    A record missing from Source must expose the Accounting amount.
    """

    dataframe = build_reconciliation_row(
        status="MISSING_IN_SOURCE",
        source_amount=None,
        accounting_amount=75000,
        absolute_difference=None,
    )

    result = calculate_financial_exposure(
        dataframe
    )

    assert (
        result.loc[
            0,
            "financial_exposure_usd",
        ]
        == 75000
    )


def test_amount_mismatch_uses_absolute_difference() -> None:
    """
    Amount mismatches should expose the difference between systems.
    """

    dataframe = build_reconciliation_row(
        status="AMOUNT_MISMATCH",
        source_amount=10000,
        accounting_amount=12000,
        absolute_difference=2000,
    )

    result = calculate_financial_exposure(
        dataframe
    )

    assert (
        result.loc[
            0,
            "financial_exposure_usd",
        ]
        == 2000
    )


def test_fx_difference_uses_absolute_difference() -> None:
    """
    FX differences should expose the converted-value difference.
    """

    dataframe = build_reconciliation_row(
        status="FX_DIFFERENCE",
        source_amount=10000,
        accounting_amount=10500,
        absolute_difference=500,
    )

    result = calculate_financial_exposure(
        dataframe
    )

    assert (
        result.loc[
            0,
            "financial_exposure_usd",
        ]
        == 500
    )


def test_duplicate_transaction_uses_transaction_value() -> None:
    """
    Duplicate transactions should expose the transaction value.
    """

    dataframe = build_reconciliation_row(
        status="DUPLICATE_TRANSACTION",
        source_amount=25000,
        accounting_amount=25000,
        absolute_difference=0,
    )

    result = calculate_financial_exposure(
        dataframe
    )

    assert (
        result.loc[
            0,
            "financial_exposure_usd",
        ]
        == 25000
    )


def test_mapping_error_uses_transaction_value() -> None:
    """
    Mapping errors should expose the affected transaction value.
    """

    dataframe = build_reconciliation_row(
        status="MAPPING_ERROR",
        source_amount=40000,
        accounting_amount=40000,
        absolute_difference=0,
    )

    result = calculate_financial_exposure(
        dataframe
    )

    assert (
        result.loc[
            0,
            "financial_exposure_usd",
        ]
        == 40000
    )


def test_period_mismatch_uses_transaction_value() -> None:
    """
    Period mismatches should expose the affected transaction value.
    """

    dataframe = build_reconciliation_row(
        status="PERIOD_MISMATCH",
        source_amount=60000,
        accounting_amount=60000,
        absolute_difference=0,
    )

    result = calculate_financial_exposure(
        dataframe
    )

    assert (
        result.loc[
            0,
            "financial_exposure_usd",
        ]
        == 60000
    )


def test_matched_transaction_has_none_severity(
    severity_config: dict,
) -> None:
    """
    Matched transactions must have NONE severity.
    """

    dataframe = pd.DataFrame(
        {
            "reconciliation_status": [
                "MATCHED"
            ],
            "financial_exposure_usd": [
                0
            ],
        }
    )

    result = assign_severity(
        dataframe,
        severity_config,
    )

    assert (
        result.loc[
            0,
            "severity",
        ]
        == "NONE"
    )


@pytest.mark.parametrize(
    (
        "financial_exposure",
        "expected_severity",
    ),
    [
        (0.01, "LOW"),
        (100.00, "LOW"),
        (100.01, "MEDIUM"),
        (10000.00, "MEDIUM"),
        (10000.01, "HIGH"),
        (100000.00, "HIGH"),
        (100000.01, "CRITICAL"),
        (500000.00, "CRITICAL"),
    ],
)
def test_exception_severity_thresholds(
    financial_exposure: float,
    expected_severity: str,
    severity_config: dict,
) -> None:
    """
    Severity must follow configured materiality thresholds.
    """

    dataframe = pd.DataFrame(
        {
            "reconciliation_status": [
                "AMOUNT_MISMATCH"
            ],
            "financial_exposure_usd": [
                financial_exposure
            ],
        }
    )

    result = assign_severity(
        dataframe,
        severity_config,
    )

    assert (
        result.loc[
            0,
            "severity",
        ]
        == expected_severity
    )