
from io import BytesIO

import pandas as pd


# ==================================================
# CSV EXPORT
# ==================================================

def create_csv(df):

    return df.to_csv(
        index=False,
        encoding="utf-8-sig"
    ).encode("utf-8-sig")


# ==================================================
# EXCEL EXPORT
# ==================================================

def create_excel(
    transactions,
    summary=None,
    monthly=None
):

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        # ------------------------------------------
        # TRANSACTIONS
        # ------------------------------------------

        transactions.to_excel(
            writer,
            sheet_name="Transactions",
            index=False
        )

        # ------------------------------------------
        # SUMMARY
        # ------------------------------------------

        if summary is not None:

            summary.to_excel(
                writer,
                sheet_name="Dashboard Summary",
                index=False
            )

        # ------------------------------------------
        # MONTHLY
        # ------------------------------------------

        if monthly is not None:

            monthly.to_excel(
                writer,
                sheet_name="Monthly Summary",
                index=False
            )

        # ------------------------------------------
        # FORMAT WORKSHEETS
        # ------------------------------------------

        for worksheet in writer.book.worksheets:

            worksheet.freeze_panes = "A2"

            worksheet.auto_filter.ref = (
                worksheet.dimensions
            )

            for column in worksheet.columns:

                max_length = 0

                column_letter = (
                    column[0].column_letter
                )

                for cell in column:

                    value = cell.value

                    if value is not None:

                        max_length = max(
                            max_length,
                            len(str(value))
                        )

                worksheet.column_dimensions[
                    column_letter
                ].width = min(
                    max_length + 3,
                    35
                )

    output.seek(0)

    return output.getvalue()


# ==================================================
# REPORT DOWNLOAD CONTROLS
# ==================================================

def render_export_buttons(
    df,
    filename="goparkin_report",
    summary=None,
    monthly=None
):

    csv_data = create_csv(df)

    excel_data = create_excel(
        transactions=df,
        summary=summary,
        monthly=monthly
    )

    col1, col2 = __import__(
        "streamlit"
    ).columns(2)

    with col1:

        __import__("streamlit").download_button(
            "Download CSV",
            data=csv_data,
            file_name=f"{filename}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col2:

        __import__("streamlit").download_button(
            "Download Excel",
            data=excel_data,
            file_name=f"{filename}.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            use_container_width=True
        )
