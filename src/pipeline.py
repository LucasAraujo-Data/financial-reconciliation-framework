"""
Financial Reconciliation Framework
End-to-End Pipeline

This module orchestrates the complete financial reconciliation workflow:

1. Generate synthetic ground-truth transactions
2. Inject controlled anomalies into source and accounting datasets
3. Execute the reconciliation engine
4. Generate analytical reporting datasets
5. Generate the audit-ready Excel exception report

Run from the project root with:

    python -m src.pipeline
"""

from datetime import datetime
from time import perf_counter

from src.data_generation.generate_transactions import (
    main as generate_transactions,
)
from src.data_generation.inject_anomalies import (
    main as inject_anomalies,
)
from src.reconciliation.reconciliation_engine import (
    main as run_reconciliation,
)
from src.reporting.generate_summary import (
    main as generate_reporting_summary,
)
from src.reporting.generate_excel_report import (
    main as generate_excel_report,
)


PIPELINE_STEPS = [
    (
        "Generate synthetic transactions",
        generate_transactions,
    ),
    (
        "Inject controlled anomalies",
        inject_anomalies,
    ),
    (
        "Run reconciliation engine",
        run_reconciliation,
    ),
    (
        "Generate reporting datasets",
        generate_reporting_summary,
    ),
    (
        "Generate Excel exception report",
        generate_excel_report,
    ),
]


def print_header() -> None:
    """Print pipeline execution header."""

    print("\n" + "=" * 72)
    print("FINANCIAL RECONCILIATION FRAMEWORK")
    print("End-to-End Pipeline")
    print("=" * 72)

    print(
        "\nExecution started:"
        f" {datetime.now():%Y-%m-%d %H:%M:%S}"
    )

    print(
        f"Pipeline steps: {len(PIPELINE_STEPS)}"
    )


def run_step(
    step_number: int,
    step_name: str,
    step_function,
) -> float:
    """
    Execute one pipeline step and return its execution time.

    Any exception raised by a step is intentionally propagated so that
    the pipeline stops immediately rather than producing downstream
    outputs from incomplete or invalid upstream data.
    """

    print("\n" + "-" * 72)

    print(
        f"STEP {step_number}/{len(PIPELINE_STEPS)}"
        f" - {step_name}"
    )

    print("-" * 72)

    start_time = perf_counter()

    try:
        step_function()

    except Exception as error:
        elapsed_time = perf_counter() - start_time

        print(
            f"\n[FAILED] {step_name}"
        )

        print(
            f"Execution time: {elapsed_time:.2f} seconds"
        )

        print(
            f"Error: {type(error).__name__}: {error}"
        )

        raise

    elapsed_time = perf_counter() - start_time

    print(
        f"\n[OK] {step_name}"
    )

    print(
        f"Execution time: {elapsed_time:.2f} seconds"
    )

    return elapsed_time


def main() -> None:
    """Execute the complete financial reconciliation pipeline."""

    pipeline_start = perf_counter()

    print_header()

    execution_times = []

    try:
        for step_number, (
            step_name,
            step_function,
        ) in enumerate(
            PIPELINE_STEPS,
            start=1,
        ):
            elapsed_time = run_step(
                step_number=step_number,
                step_name=step_name,
                step_function=step_function,
            )

            execution_times.append(
                (
                    step_name,
                    elapsed_time,
                )
            )

    except Exception:
        total_elapsed = (
            perf_counter()
            - pipeline_start
        )

        print("\n" + "=" * 72)
        print("PIPELINE FAILED")
        print("=" * 72)

        print(
            "\nThe pipeline stopped because one of the "
            "processing steps failed."
        )

        print(
            "Downstream steps were not executed."
        )

        print(
            f"Total execution time before failure: "
            f"{total_elapsed:.2f} seconds"
        )

        raise

    total_elapsed = (
        perf_counter()
        - pipeline_start
    )

    print("\n" + "=" * 72)
    print("PIPELINE EXECUTION SUMMARY")
    print("=" * 72)

    for step_number, (
        step_name,
        elapsed_time,
    ) in enumerate(
        execution_times,
        start=1,
    ):
        print(
            f"{step_number}. "
            f"{step_name:<38} "
            f"{elapsed_time:>8.2f}s"
        )

    print("-" * 72)

    print(
        f"Total execution time:"
        f" {total_elapsed:.2f} seconds"
    )

    print(
        f"Execution completed:"
        f" {datetime.now():%Y-%m-%d %H:%M:%S}"
    )

    print("\nGenerated artifacts:")

    artifacts = [
        "data/processed/ground_truth_transactions.csv",
        "data/raw/source_transactions.csv",
        "data/raw/accounting_transactions.csv",
        "data/processed/expected_anomalies.csv",
        "outputs/reconciliation_results.csv",
        "outputs/reconciliation_summary.csv",
        "outputs/exception_summary_by_status.csv",
        "outputs/exception_summary_by_severity.csv",
        "outputs/exception_report.xlsx",
    ]

    for artifact in artifacts:
        print(
            f"  - {artifact}"
        )

    print("\n" + "=" * 72)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 72)


if __name__ == "__main__":
    main()