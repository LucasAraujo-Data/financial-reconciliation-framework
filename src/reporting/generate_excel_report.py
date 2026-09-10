from pathlib import Path

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RECONCILIATION_RESULTS_PATH = (
    PROJECT_ROOT / "outputs" / "reconciliation_results.csv"
)

OVERALL_SUMMARY_PATH = (
    PROJECT_ROOT / "outputs" / "reconciliation_summary.csv"
)

STATUS_SUMMARY_PATH = (
    PROJECT_ROOT / "outputs" / "exception_summary_by_status.csv"
)

SEVERITY_SUMMARY_PATH = (
    PROJECT_ROOT / "outputs" / "exception_summary_by_severity.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT / "outputs" / "exception_report.xlsx"
)


# ---------------------------------------------------------------------
# Visual theme
# ---------------------------------------------------------------------

DARK_BLUE = "1F4E78"
MEDIUM_BLUE = "5B9BD5"
LIGHT_BLUE = "D9EAF7"

WHITE = "FFFFFF"
BLACK = "000000"
GRAY_TEXT = "666666"

GREEN = "C6EFCE"
GREEN_TEXT = "006100"

YELLOW = "FFF2CC"
YELLOW_TEXT = "9C6500"

ORANGE = "F4B183"
ORANGE_TEXT = "9C5700"

RED = "FFC7CE"
RED_TEXT = "9C0006"

LIGHT_GRAY = "F2F2F2"

THIN_BORDER = Border(
    left=Side(style="thin", color="D9E1F2"),
    right=Side(style="thin", color="D9E1F2"),
    top=Side(style="thin", color="D9E1F2"),
    bottom=Side(style="thin", color="D9E1F2"),
)


# ---------------------------------------------------------------------
# Presentation mappings
# ---------------------------------------------------------------------

STATUS_LABELS = {
    "AMOUNT_MISMATCH": "Amount Mismatch",
    "MISSING_IN_ACCOUNTING": "Missing in Accounting",
    "MISSING_IN_SOURCE": "Missing in Source",
    "DUPLICATE_TRANSACTION": "Duplicate Transaction",
    "FX_DIFFERENCE": "FX Difference",
    "PERIOD_MISMATCH": "Period Mismatch",
    "MAPPING_ERROR": "Mapping Error",
    "REPROCESSED_TRANSACTION": "Reprocessed Transaction",
    "MATCHED": "Matched",
}

COLUMN_LABELS = {
    "reconciliation_status": "Exception Type",
    "exception_count": "Exception Count",
    "total_exposure_usd": "Total Exposure (USD)",
    "average_exposure_usd": "Average Exposure (USD)",
    "maximum_exposure_usd": "Maximum Exposure (USD)",
    "exception_percentage": "% of Exceptions",
    "severity": "Severity",
}


def load_data() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """Load datasets required by the Excel reporting layer."""

    reconciliation_results = pd.read_csv(
        RECONCILIATION_RESULTS_PATH
    )

    overall_summary = pd.read_csv(
        OVERALL_SUMMARY_PATH
    )

    status_summary = pd.read_csv(
        STATUS_SUMMARY_PATH
    )

    severity_summary = pd.read_csv(
        SEVERITY_SUMMARY_PATH
    )

    return (
        reconciliation_results,
        overall_summary,
        status_summary,
        severity_summary,
    )


def validate_inputs(
    reconciliation_results: pd.DataFrame,
    overall_summary: pd.DataFrame,
    status_summary: pd.DataFrame,
    severity_summary: pd.DataFrame,
) -> None:
    """Validate source datasets before report generation."""

    datasets = {
        "reconciliation_results": reconciliation_results,
        "overall_summary": overall_summary,
        "status_summary": status_summary,
        "severity_summary": severity_summary,
    }

    for name, dataframe in datasets.items():
        if dataframe.empty:
            raise ValueError(
                f"{name} is empty."
            )

    required_columns = {
        "transaction_id",
        "reconciliation_status",
        "severity",
        "financial_exposure_usd",
    }

    missing_columns = (
        required_columns
        - set(reconciliation_results.columns)
    )

    if missing_columns:
        raise ValueError(
            "Reconciliation results are missing "
            f"required columns: {sorted(missing_columns)}"
        )


def prepare_status_summary(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Convert technical status summary into presentation format."""

    presentation = dataframe.copy()

    presentation[
        "reconciliation_status"
    ] = (
        presentation[
            "reconciliation_status"
        ]
        .map(STATUS_LABELS)
        .fillna(
            presentation[
                "reconciliation_status"
            ]
        )
    )

    presentation = presentation.rename(
        columns=COLUMN_LABELS
    )

    return presentation


def prepare_severity_summary(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Convert severity summary into presentation format."""

    return dataframe.rename(
        columns=COLUMN_LABELS
    )


def prepare_exception_detail(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Prepare transaction-level exception queue."""

    exceptions = dataframe[
        dataframe[
            "reconciliation_status"
        ] != "MATCHED"
    ].copy()

    severity_order = {
        "CRITICAL": 1,
        "HIGH": 2,
        "MEDIUM": 3,
        "LOW": 4,
    }

    exceptions["_severity_order"] = (
        exceptions["severity"]
        .map(severity_order)
        .fillna(99)
    )

    exceptions = (
        exceptions
        .sort_values(
            [
                "_severity_order",
                "financial_exposure_usd",
                "transaction_id",
            ],
            ascending=[
                True,
                False,
                True,
            ],
        )
        .drop(columns=["_severity_order"])
        .reset_index(drop=True)
    )

    exceptions[
        "reconciliation_status"
    ] = (
        exceptions[
            "reconciliation_status"
        ]
        .map(STATUS_LABELS)
        .fillna(
            exceptions[
                "reconciliation_status"
            ]
        )
    )

    detail_labels = {
        "transaction_id":
            "Transaction ID",

        "reconciliation_status":
            "Exception Type",

        "severity":
            "Severity",

        "contract_id_source":
            "Source Contract ID",

        "contract_id_accounting":
            "Accounting Contract ID",

        "counterparty_id_source":
            "Source Counterparty ID",

        "counterparty_id_accounting":
            "Accounting Counterparty ID",

        "transaction_type_source":
            "Source Transaction Type",

        "transaction_type_accounting":
            "Accounting Transaction Type",

        "accounting_period_source":
            "Source Accounting Period",

        "accounting_period_accounting":
            "Accounting System Period",

        "currency_source":
            "Source Currency",

        "currency_accounting":
            "Accounting Currency",

        "original_amount_source":
            "Source Original Amount",

        "original_amount_accounting":
            "Accounting Original Amount",

        "exchange_rate_source":
            "Source FX Rate",

        "exchange_rate_accounting":
            "Accounting FX Rate",

        "converted_amount_usd_source":
            "Source Amount (USD)",

        "converted_amount_usd_accounting":
            "Accounting Amount (USD)",

        "amount_difference_usd":
            "Amount Difference (USD)",

        "absolute_difference_usd":
            "Absolute Difference (USD)",

        "financial_exposure_usd":
            "Financial Exposure (USD)",

        "relative_difference":
            "Relative Difference",

        "processing_timestamp_source":
            "Source Processing Timestamp",

        "processing_timestamp_accounting":
            "Accounting Processing Timestamp",

        "processing_delay_hours":
            "Processing Delay (Hours)",
    }

    return exceptions.rename(
        columns=detail_labels
    )


def create_title(
    worksheet,
    title: str,
    subtitle: str,
    end_column: int,
) -> None:
    """Create worksheet title and subtitle."""

    worksheet.merge_cells(
        start_row=1,
        start_column=1,
        end_row=1,
        end_column=end_column,
    )

    title_cell = worksheet.cell(
        row=1,
        column=1,
        value=title,
    )

    title_cell.font = Font(
        size=18,
        bold=True,
        color=WHITE,
    )

    title_cell.fill = PatternFill(
        fill_type="solid",
        fgColor=DARK_BLUE,
    )

    title_cell.alignment = Alignment(
        vertical="center"
    )

    worksheet.row_dimensions[1].height = 30

    worksheet.merge_cells(
        start_row=2,
        start_column=1,
        end_row=2,
        end_column=end_column,
    )

    subtitle_cell = worksheet.cell(
        row=2,
        column=1,
        value=subtitle,
    )

    subtitle_cell.font = Font(
        size=10,
        italic=True,
        color=GRAY_TEXT,
    )

    worksheet.row_dimensions[2].height = 20


def create_section_header(
    worksheet,
    row: int,
    start_column: int,
    end_column: int,
    title: str,
) -> None:
    """Create section heading."""

    worksheet.merge_cells(
        start_row=row,
        start_column=start_column,
        end_row=row,
        end_column=end_column,
    )

    cell = worksheet.cell(
        row=row,
        column=start_column,
        value=title,
    )

    cell.font = Font(
        bold=True,
        color=WHITE,
    )

    cell.fill = PatternFill(
        fill_type="solid",
        fgColor=MEDIUM_BLUE,
    )


def create_kpi_card(
    worksheet,
    label_cell: str,
    value_cell: str,
    label: str,
    value,
    number_format: str,
) -> None:
    """Create one executive KPI card."""

    label_target = worksheet[
        label_cell
    ]

    value_target = worksheet[
        value_cell
    ]

    label_target.value = label

    label_target.font = Font(
        bold=True,
        color=WHITE,
    )

    label_target.fill = PatternFill(
        fill_type="solid",
        fgColor=DARK_BLUE,
    )

    label_target.alignment = Alignment(
        horizontal="left",
        vertical="center",
    )

    label_target.border = THIN_BORDER

    value_target.value = value

    value_target.font = Font(
        bold=True,
        size=13,
        color=BLACK,
    )

    value_target.fill = PatternFill(
        fill_type="solid",
        fgColor=LIGHT_BLUE,
    )

    value_target.alignment = Alignment(
        horizontal="right",
        vertical="center",
    )

    value_target.border = THIN_BORDER

    value_target.number_format = (
        number_format
    )


def write_dataframe(
    worksheet,
    dataframe: pd.DataFrame,
    start_row: int,
    start_column: int = 1,
) -> tuple[int, int]:
    """Write DataFrame to worksheet."""

    for column_number, column_name in enumerate(
        dataframe.columns,
        start=start_column,
    ):
        cell = worksheet.cell(
            row=start_row,
            column=column_number,
            value=column_name,
        )

        cell.font = Font(
            bold=True,
            color=WHITE,
        )

        cell.fill = PatternFill(
            fill_type="solid",
            fgColor=DARK_BLUE,
        )

        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True,
        )

        cell.border = THIN_BORDER

    for row_number, values in enumerate(
        dataframe.itertuples(
            index=False,
            name=None,
        ),
        start=start_row + 1,
    ):
        for column_number, value in enumerate(
            values,
            start=start_column,
        ):
            if pd.isna(value):
                value = None

            cell = worksheet.cell(
                row=row_number,
                column=column_number,
                value=value,
            )

            cell.border = THIN_BORDER

            cell.alignment = Alignment(
                vertical="center",
            )

    end_row = (
        start_row + len(dataframe)
    )

    end_column = (
        start_column
        + len(dataframe.columns)
        - 1
    )

    return end_row, end_column


def add_table(
    worksheet,
    start_row: int,
    start_column: int,
    end_row: int,
    end_column: int,
    name: str,
) -> None:
    """Create formatted Excel table."""

    reference = (
        f"{get_column_letter(start_column)}"
        f"{start_row}:"
        f"{get_column_letter(end_column)}"
        f"{end_row}"
    )

    table = Table(
        displayName=name,
        ref=reference,
    )

    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )

    worksheet.add_table(table)


def format_summary_columns(
    worksheet,
    header_row: int,
) -> None:
    """Apply reporting number formats."""

    headers = {
        worksheet.cell(
            row=header_row,
            column=column,
        ).value: column
        for column in range(
            1,
            worksheet.max_column + 1,
        )
    }

    currency_headers = {
        "Total Exposure (USD)",
        "Average Exposure (USD)",
        "Maximum Exposure (USD)",
    }

    for header, column in headers.items():

        if header in currency_headers:
            for row in range(
                header_row + 1,
                worksheet.max_row + 1,
            ):
                worksheet.cell(
                    row=row,
                    column=column,
                ).number_format = (
                    '$#,##0.00;[Red]-$#,##0.00'
                )

        if header == "% of Exceptions":
            for row in range(
                header_row + 1,
                worksheet.max_row + 1,
            ):
                worksheet.cell(
                    row=row,
                    column=column,
                ).number_format = "0.00%"


def format_detail_columns(
    worksheet,
    header_row: int,
) -> None:
    """Apply number formats to transaction detail."""

    headers = {
        worksheet.cell(
            row=header_row,
            column=column,
        ).value: column
        for column in range(
            1,
            worksheet.max_column + 1,
        )
    }

    currency_columns = {
        "Source Amount (USD)",
        "Accounting Amount (USD)",
        "Amount Difference (USD)",
        "Absolute Difference (USD)",
        "Financial Exposure (USD)",
    }

    original_amount_columns = {
        "Source Original Amount",
        "Accounting Original Amount",
    }

    for header, column in headers.items():

        if (
            header in currency_columns
            or header in original_amount_columns
        ):
            for row in range(
                header_row + 1,
                worksheet.max_row + 1,
            ):
                worksheet.cell(
                    row=row,
                    column=column,
                ).number_format = (
                    '$#,##0.00;[Red]-$#,##0.00'
                )

        elif header == "Relative Difference":
            for row in range(
                header_row + 1,
                worksheet.max_row + 1,
            ):
                worksheet.cell(
                    row=row,
                    column=column,
                ).number_format = "0.00%"


def apply_severity_formatting(
    worksheet,
    header_row: int,
    end_row: int,
) -> None:
    """Apply visual severity highlighting."""

    headers = {
        worksheet.cell(
            row=header_row,
            column=column,
        ).value: column
        for column in range(
            1,
            worksheet.max_column + 1,
        )
    }

    severity_column = headers.get(
        "Severity"
    )

    if severity_column is None:
        return

    severity_letter = get_column_letter(
        severity_column
    )

    data_range = (
        f"{severity_letter}"
        f"{header_row + 1}:"
        f"{severity_letter}"
        f"{end_row}"
    )

    severity_styles = {
        "CRITICAL": (
            RED,
            RED_TEXT,
        ),
        "HIGH": (
            ORANGE,
            ORANGE_TEXT,
        ),
        "MEDIUM": (
            YELLOW,
            YELLOW_TEXT,
        ),
        "LOW": (
            GREEN,
            GREEN_TEXT,
        ),
    }

    for severity, (
        fill_color,
        font_color,
    ) in severity_styles.items():

        worksheet.conditional_formatting.add(
            data_range,
            FormulaRule(
                formula=[
                    f'{severity_letter}'
                    f'{header_row + 1}='
                    f'"{severity}"'
                ],
                fill=PatternFill(
                    fill_type="solid",
                    fgColor=fill_color,
                ),
                font=Font(
                    bold=True,
                    color=font_color,
                ),
            ),
        )


def set_column_widths(
    worksheet,
    widths: dict[str, float],
) -> None:
    """Set explicit column widths."""

    for column, width in widths.items():
        worksheet.column_dimensions[
            column
        ].width = width


def auto_fit_columns(
    worksheet,
    maximum_width: int = 30,
) -> None:
    """Auto-fit unmerged worksheet columns."""

    for column_index in range(
        1,
        worksheet.max_column + 1,
    ):

        column_letter = get_column_letter(
            column_index
        )

        max_length = 0

        for row_index in range(
            1,
            worksheet.max_row + 1,
        ):

            cell = worksheet.cell(
                row=row_index,
                column=column_index,
            )

            if cell.value is None:
                continue

            max_length = max(
                max_length,
                len(str(cell.value)),
            )

        worksheet.column_dimensions[
            column_letter
        ].width = min(
            max(max_length + 2, 12),
            maximum_width,
        )


def create_executive_summary_sheet(
    workbook: Workbook,
    overall_summary: pd.DataFrame,
    status_summary: pd.DataFrame,
    severity_summary: pd.DataFrame,
) -> None:
    """Create management-oriented Executive Summary."""

    worksheet = workbook.active

    worksheet.title = (
        "Executive Summary"
    )

    worksheet.sheet_view.showGridLines = False

    create_title(
        worksheet,
        "Financial Reconciliation Executive Summary",
        (
            "Automated reconciliation control, "
            "financial exposure and exception prioritization"
        ),
        8,
    )

    summary = overall_summary.iloc[0]

    create_section_header(
        worksheet,
        4,
        1,
        8,
        "Reconciliation KPIs",
    )

    kpis = [
        (
            "A6",
            "B6",
            "Transactions",
            int(
                summary[
                    "total_transactions"
                ]
            ),
            '#,##0',
        ),
        (
            "D6",
            "E6",
            "Match Rate",
            float(
                summary[
                    "match_rate"
                ]
            ),
            '0.00%',
        ),
        (
            "G6",
            "H6",
            "Exceptions",
            int(
                summary[
                    "exception_transactions"
                ]
            ),
            '#,##0',
        ),
        (
            "A8",
            "B8",
            "Exception Exposure",
            float(
                summary[
                    "total_exception_exposure_usd"
                ]
            ),
            '$0.00,,"M"',
        ),
        (
            "D8",
            "E8",
            "Material Exposure",
            float(
                summary[
                    "material_exposure_usd"
                ]
            ),
            '$0.00,,"M"',
        ),
        (
            "G8",
            "H8",
            "Critical Exceptions",
            int(
                summary[
                    "critical_exceptions"
                ]
            ),
            '#,##0',
        ),
    ]

    for (
        label_cell,
        value_cell,
        label,
        value,
        number_format,
    ) in kpis:

        create_kpi_card(
            worksheet,
            label_cell,
            value_cell,
            label,
            value,
            number_format,
        )

    create_section_header(
        worksheet,
        11,
        1,
        6,
        "Exception Analysis",
    )

    status_end_row, status_end_column = (
        write_dataframe(
            worksheet,
            status_summary,
            start_row=12,
        )
    )

    add_table(
        worksheet,
        start_row=12,
        start_column=1,
        end_row=status_end_row,
        end_column=status_end_column,
        name="ExecutiveExceptionAnalysis",
    )

    format_summary_columns(
        worksheet,
        header_row=12,
    )

    severity_start_row = (
        status_end_row + 3
    )

    create_section_header(
        worksheet,
        severity_start_row,
        1,
        4,
        "Severity Overview",
    )

    severity_header_row = (
        severity_start_row + 1
    )

    severity_end_row, severity_end_column = (
        write_dataframe(
            worksheet,
            severity_summary,
            start_row=severity_header_row,
        )
    )

    add_table(
        worksheet,
        start_row=severity_header_row,
        start_column=1,
        end_row=severity_end_row,
        end_column=severity_end_column,
        name="ExecutiveSeverityOverview",
    )

    format_summary_columns(
        worksheet,
        header_row=severity_header_row,
    )

    apply_severity_formatting(
        worksheet,
        header_row=severity_header_row,
        end_row=severity_end_row,
    )

    set_column_widths(
        worksheet,
        {
            "A": 27,
            "B": 18,
            "C": 22,
            "D": 24,
            "E": 24,
            "F": 18,
            "G": 22,
            "H": 15,
        },
    )

    worksheet.freeze_panes = "A4"


def create_status_sheet(
    workbook: Workbook,
    status_summary: pd.DataFrame,
) -> None:
    """Create exception category analysis."""

    worksheet = workbook.create_sheet(
        "Exceptions by Status"
    )

    worksheet.sheet_view.showGridLines = False

    create_title(
        worksheet,
        "Exceptions by Status",
        (
            "Exception volume and financial "
            "exposure by reconciliation category"
        ),
        len(status_summary.columns),
    )

    end_row, end_column = (
        write_dataframe(
            worksheet,
            status_summary,
            start_row=4,
        )
    )

    add_table(
        worksheet,
        4,
        1,
        end_row,
        end_column,
        "StatusSummary",
    )

    format_summary_columns(
        worksheet,
        4,
    )

    auto_fit_columns(
        worksheet,
        maximum_width=28,
    )

    worksheet.freeze_panes = "A5"


def create_severity_sheet(
    workbook: Workbook,
    severity_summary: pd.DataFrame,
) -> None:
    """Create materiality analysis."""

    worksheet = workbook.create_sheet(
        "Exceptions by Severity"
    )

    worksheet.sheet_view.showGridLines = False

    create_title(
        worksheet,
        "Exceptions by Severity",
        (
            "Materiality-based prioritization "
            "of reconciliation exceptions"
        ),
        len(severity_summary.columns),
    )

    end_row, end_column = (
        write_dataframe(
            worksheet,
            severity_summary,
            start_row=4,
        )
    )

    add_table(
        worksheet,
        4,
        1,
        end_row,
        end_column,
        "SeveritySummary",
    )

    format_summary_columns(
        worksheet,
        4,
    )

    apply_severity_formatting(
        worksheet,
        4,
        end_row,
    )

    auto_fit_columns(
        worksheet,
        maximum_width=28,
    )

    worksheet.freeze_panes = "A5"


def create_exception_detail_sheet(
    workbook: Workbook,
    exception_detail: pd.DataFrame,
) -> None:
    """Create investigation-ready exception queue."""

    worksheet = workbook.create_sheet(
        "Exception Detail"
    )

    worksheet.sheet_view.showGridLines = False

    create_title(
        worksheet,
        "Reconciliation Exception Detail",
        (
            "Transaction-level investigation queue "
            "prioritized by severity and financial exposure"
        ),
        len(exception_detail.columns),
    )

    end_row, end_column = (
        write_dataframe(
            worksheet,
            exception_detail,
            start_row=4,
        )
    )

    add_table(
        worksheet,
        4,
        1,
        end_row,
        end_column,
        "ExceptionDetail",
    )

    format_detail_columns(
        worksheet,
        4,
    )

    apply_severity_formatting(
        worksheet,
        4,
        end_row,
    )

    auto_fit_columns(
        worksheet,
        maximum_width=25,
    )

    worksheet.freeze_panes = "A5"


def validate_workbook_before_save(
    workbook: Workbook,
    expected_exception_count: int,
) -> None:
    """Validate report structure and detail count."""

    expected_sheets = [
        "Executive Summary",
        "Exceptions by Status",
        "Exceptions by Severity",
        "Exception Detail",
    ]

    if workbook.sheetnames != expected_sheets:
        raise ValueError(
            "Unexpected workbook structure."
        )

    detail_sheet = workbook[
        "Exception Detail"
    ]

    actual_exception_count = (
        detail_sheet.max_row - 4
    )

    if (
        actual_exception_count
        != expected_exception_count
    ):
        raise ValueError(
            "Exception Detail row count mismatch. "
            f"Expected {expected_exception_count}, "
            f"found {actual_exception_count}."
        )


def validate_saved_workbook(
    output_path: Path,
    expected_exception_count: int,
) -> None:
    """
    Reopen the saved workbook and validate the generated artifact.

    This confirms that the XLSX file can be read after serialization.
    """

    workbook = load_workbook(
        output_path,
        read_only=True,
        data_only=False,
    )

    expected_sheets = [
        "Executive Summary",
        "Exceptions by Status",
        "Exceptions by Severity",
        "Exception Detail",
    ]

    if workbook.sheetnames != expected_sheets:
        workbook.close()

        raise ValueError(
            "Saved workbook does not contain "
            "the expected worksheets."
        )

    detail_sheet = workbook[
        "Exception Detail"
    ]

    actual_exception_count = (
        detail_sheet.max_row - 4
    )

    workbook.close()

    if (
        actual_exception_count
        != expected_exception_count
    ):
        raise ValueError(
            "Saved Exception Detail row count mismatch."
        )


def main() -> None:
    """Generate professional Excel reconciliation report."""

    (
        reconciliation_results,
        overall_summary,
        status_summary,
        severity_summary,
    ) = load_data()

    validate_inputs(
        reconciliation_results,
        overall_summary,
        status_summary,
        severity_summary,
    )

    status_presentation = (
        prepare_status_summary(
            status_summary
        )
    )

    severity_presentation = (
        prepare_severity_summary(
            severity_summary
        )
    )

    exception_detail = (
        prepare_exception_detail(
            reconciliation_results
        )
    )

    workbook = Workbook()

    create_executive_summary_sheet(
        workbook,
        overall_summary,
        status_presentation,
        severity_presentation,
    )

    create_status_sheet(
        workbook,
        status_presentation,
    )

    create_severity_sheet(
        workbook,
        severity_presentation,
    )

    create_exception_detail_sheet(
        workbook,
        exception_detail,
    )

    expected_exception_count = len(
        exception_detail
    )

    validate_workbook_before_save(
        workbook,
        expected_exception_count,
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    workbook.save(
        OUTPUT_PATH
    )

    validate_saved_workbook(
        OUTPUT_PATH,
        expected_exception_count,
    )

    print(
        "\nExcel exception report generated successfully."
    )

    print(
        f"\nExceptions exported: "
        f"{expected_exception_count:,}"
    )

    print(
        "Worksheets created:"
    )

    for sheet_name in workbook.sheetnames:
        print(
            f"  - {sheet_name}"
        )

    print(
        f"\nOutput file: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()