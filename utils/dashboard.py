
import pandas as pd
import streamlit as st

from utils.charts import (
    create_ranking_chart,
    create_monthly_chart
)

from utils.reporting import (
    render_export_buttons
)

from shared_data import CURRENCY_SYMBOL


# ==================================================
# CONFIGURATION
# ==================================================

LIMIT_OPTIONS = {
    "Top 10": 10,
    "Top 20": 20,
    "Top 30": 30,
    "Top 50": 50,
    "All": None
}


# ==================================================
# DATA CLEANING
# ==================================================


def clean_display_dataframe(df):
    """
    Clean DataFrame columns before displaying through Streamlit.
    Prevents common PyArrow serialization errors.
    """

    df = df.copy()

    for col in df.columns:

        normalized_col = (
            str(col).strip().lower().replace("_", " ")
        )

        # ------------------------------------------
        # CONNECTOR ID
        # ------------------------------------------

        if normalized_col in [
            "connector id",
            "ci connector id"
        ]:

            df[col] = (
                df[col]
                .astype("string")
                .str.strip()
                .replace("", pd.NA)
            )

        # ------------------------------------------
        # DATETIME
        # ------------------------------------------

        elif pd.api.types.is_datetime64_any_dtype(df[col]):

            df[col] = pd.to_datetime(
                df[col],
                errors="coerce"
            )

        # ------------------------------------------
        # OBJECT COLUMNS
        # ------------------------------------------

        elif df[col].dtype == "object":

            non_null = df[col].dropna()

            if not non_null.empty:

                types = non_null.map(type).nunique()

                if types > 1:
                    df[col] = df[col].astype("string")

    return df



# ==================================================
# AGGREGATION
# ==================================================

def prepare_summary(
    df,
    dimension,
    value_column
):

    if df.empty:
        return pd.DataFrame(
            columns=[
                dimension,
                "total_amount",
                "transactions",
                "valid_values"
            ]
        )

    if dimension not in df.columns:
        return pd.DataFrame()

    if value_column not in df.columns:
        return pd.DataFrame()

    valid = df.dropna(
        subset=["report_date"]
    ).copy()

    valid[value_column] = pd.to_numeric(
        valid[value_column],
        errors="coerce"
    )

    result = (
        valid
        .groupby(dimension, as_index=False)
        .agg(
            total_amount=(value_column, "sum"),
            transactions=(value_column, "size"),
            valid_values=(value_column, "count")
        )
        .sort_values(
            "total_amount",
            ascending=False
        )
    )

    return result


# ==================================================
# SELECTED ENTITY
# ==================================================

def update_selection(
    event,
    state_key
):

    if event is None:
        return

    selected_points = event.selection.points

    if not selected_points:
        return

    clicked = selected_points[0].get("y")

    if clicked is None:
        return

    current = st.session_state.get(state_key)

    if current == clicked:

        st.session_state[state_key] = None

    else:

        st.session_state[state_key] = clicked


# ==================================================
# TRANSACTION DETAILS
# ==================================================

def render_transactions(
    df,
    dimension,
    selected_entity,
    selected_month=None
):

    details = df.copy()

    # ----------------------------------------------
    # ENTITY FILTER
    # ----------------------------------------------

    if selected_entity is not None:

        details = details[
            details[dimension].astype(str)
            == str(selected_entity)
        ]

    # ----------------------------------------------
    # MONTH FILTER
    # ----------------------------------------------

    if selected_month is not None:

        details = details[
            details["month"].astype(str)
            == str(selected_month)
        ]

    # ----------------------------------------------
    # SORT
    # ----------------------------------------------

    if "report_date" in details.columns:

        details = details.sort_values(
            "report_date",
            ascending=False
        )

    st.divider()

    st.subheader("Transaction Details")

    st.caption(
        f"Showing {len(details):,} transactions."
    )

    if details.empty:

        st.info(
            "No transactions match the selected criteria."
        )

        return

    # ----------------------------------------------
    # TRANSACTION TABLE
    # ----------------------------------------------

    display = details.copy()

    display = display.drop(
        columns=[
            "report_date",
            "month"
        ],
        errors="ignore"
    )

    # Clean mixed data types before Arrow conversion

    display = clean_display_dataframe(display)

    st.dataframe(
        display,
        width="stretch",
        hide_index=True,
        height=450
    )

    # ----------------------------------------------
    # EXPORT
    # ----------------------------------------------

    st.markdown("#### Export Transactions")

    render_export_buttons(
        df=display,
        filename="goparkin_transactions"
    )


# ==================================================
# DIMENSION DASHBOARD
# ==================================================

def render_dimension_dashboard(
    filtered,
    dimension,
    dimension_label,
    page_title
):

    # ----------------------------------------------
    # PAGE HEADER
    # ----------------------------------------------

    st.title(page_title)

    st.caption(
        "EV billing and energy performance analytics"
    )

    # ----------------------------------------------
    # EMPTY DATA CHECK
    # ----------------------------------------------

    if filtered.empty:

        st.warning(
            "No transactions match the selected filters."
        )

        return

    # ----------------------------------------------
    # REQUIRED COLUMNS
    # ----------------------------------------------

    required_columns = [
        "report_date",
        "payment_amount",
        "ci_power",
        "month",
        dimension
    ]

    missing = [
        col for col in required_columns
        if col not in filtered.columns
    ]

    if missing:

        st.error(
            "Missing required columns: "
            + ", ".join(missing)
        )

        return

    if filtered["report_date"].notna().sum() == 0:

        st.warning(
            "No valid transaction dates are available."
        )

        return

    filtered = filtered.copy()

    # ----------------------------------------------
    # CLEAN DATA
    # ----------------------------------------------

    filtered[dimension] = (
        filtered[dimension]
        .astype("string")
        .fillna("Unknown")
    )

    filtered["payment_amount"] = pd.to_numeric(
        filtered["payment_amount"],
        errors="coerce"
    )

    filtered["ci_power"] = pd.to_numeric(
        filtered["ci_power"],
        errors="coerce"
    )

    # ----------------------------------------------
    # FILTERS
    # ----------------------------------------------

    st.subheader(
        f"{dimension_label} Filters"
    )

    col1, col2 = st.columns([1, 2])

    all_entities = sorted(
        filtered[dimension].unique().tolist()
    )

    with col1:

        limit_choice = st.selectbox(
            f"Number of {dimension_label.lower()}s",
            list(LIMIT_OPTIONS.keys()),
            index=1,
            key=f"{dimension}_limit"
        )

    with col2:

        selected_search = st.selectbox(
            f"Search {dimension_label}",
            ["All"] + all_entities,
            key=f"{dimension}_search"
        )

    limit = LIMIT_OPTIONS[limit_choice]

    # ----------------------------------------------
    # PREPARE DATA
    # ----------------------------------------------

    valid_data = filtered.dropna(
        subset=["report_date"]
    ).copy()

    payment_summary = prepare_summary(
        valid_data,
        dimension,
        "payment_amount"
    )

    energy_summary = prepare_summary(
        valid_data,
        dimension,
        "ci_power"
    )

    # ----------------------------------------------
    # APPLY DISPLAY FILTER
    # ----------------------------------------------

    def apply_display_filter(summary):

        if summary.empty:
            return summary

        if selected_search != "All":

            return summary[
                summary[dimension] == selected_search
            ].copy()

        if limit is not None:

            return summary.head(limit).copy()

        return summary.copy()

    payment_display = apply_display_filter(
        payment_summary
    )

    energy_display = apply_display_filter(
        energy_summary
    )

    st.caption(
        f"Displaying {len(payment_display):,} of "
        f"{len(payment_summary):,} {dimension_label.lower()}s."
    )

    # ==================================================
    # PAYMENT CHART
    # ==================================================

    st.divider()

    st.subheader(
        f"Total Payment By {dimension_label}"
    )

    if payment_display.empty:

        st.info("No payment records found.")

    else:

        fig_payment = create_ranking_chart(
            payment_display,
            category=dimension,
            value="total_amount",
            transaction_count="transactions",
            title="Total Payment ($)",
            unit="currency"
        )

        event_payment = st.plotly_chart(
            fig_payment,
            width="stretch",
            key=f"{dimension}_payment_chart",
            on_select="rerun",
            selection_mode="points"
        )

        update_selection(
            event_payment,
            f"selected_payment_{dimension}"
        )

    # ==================================================
    # PAYMENT MONTHLY BREAKDOWN
    # ==================================================

    selected_payment = st.session_state.get(
        f"selected_payment_{dimension}"
    )

    payment_entity = (
        selected_search
        if selected_search != "All"
        else selected_payment
    )

    if payment_entity is not None:

        monthly_payment = (
            valid_data[
                valid_data[dimension] == payment_entity
            ]
            .groupby("month", as_index=False)
            .agg(
                payment_amount=("payment_amount", "sum"),
                transactions=("payment_amount", "size")
            )
            .sort_values("month")
        )

        st.subheader(
            f"Monthly Payments - {payment_entity}"
        )

        fig = create_monthly_chart(
            monthly_payment,
            "payment_amount",
            "Monthly Payment",
            "currency"
        )

        if fig is not None:

            st.plotly_chart(
                fig,
                width="stretch"
            )

            st.dataframe(
                monthly_payment,
                width="stretch",
                hide_index=True
            )

        render_transactions(
            filtered,
            dimension,
            payment_entity
        )

    # ==================================================
    # ENERGY CHART
    # ==================================================

    st.divider()

    st.subheader(
        f"Energy Delivered By {dimension_label}"
    )

    if energy_display.empty:

        st.info("No energy records found.")

    else:

        fig_energy = create_ranking_chart(
            energy_display,
            category=dimension,
            value="total_amount",
            transaction_count="transactions",
            title="Total Energy (kWh)",
            unit="energy"
        )

        event_energy = st.plotly_chart(
            fig_energy,
            width="stretch",
            key=f"{dimension}_energy_chart",
            on_select="rerun",
            selection_mode="points"
        )

        update_selection(
            event_energy,
            f"selected_energy_{dimension}"
        )

    # ==================================================
    # ENERGY MONTHLY BREAKDOWN
    # ==================================================

    selected_energy = st.session_state.get(
        f"selected_energy_{dimension}"
    )

    energy_entity = (
        selected_search
        if selected_search != "All"
        else selected_energy
    )

    if energy_entity is not None:

        monthly_energy = (
            valid_data[
                valid_data[dimension] == energy_entity
            ]
            .groupby("month", as_index=False)
            .agg(
                energy_delivered=("ci_power", "sum"),
                transactions=("ci_power", "count")
            )
            .sort_values("month")
        )

        st.subheader(
            f"Monthly Energy - {energy_entity}"
        )

        fig = create_monthly_chart(
            monthly_energy,
            "energy_delivered",
            "Monthly Energy Delivered",
            "energy"
        )

        if fig is not None:

            st.plotly_chart(
                fig,
                width="stretch"
            )

            st.dataframe(
                monthly_energy,
                width="stretch",
                hide_index=True
            )

        render_transactions(
            filtered,
            dimension,
            energy_entity
        )

    # ==================================================
    # SUMMARY EXPORT
    # ==================================================

    st.divider()

    st.subheader(
        f"{dimension_label} Summary Export"
    )

    combined = payment_summary.merge(
        energy_summary[
            [dimension, "total_amount"]
        ].rename(
            columns={
                "total_amount": "energy_delivered"
            }
        ),
        on=dimension,
        how="outer"
    )

    combined = combined.rename(
        columns={
            "total_amount": "total_payment"
        }
    )

    combined = combined.fillna({
        "total_payment": 0,
        "energy_delivered": 0
    })

    export_data = filtered.drop(
        columns=[
            "report_date",
            "month"
        ],
        errors="ignore"
    )

    export_data = clean_display_dataframe(
        export_data
    )

    render_export_buttons(
        df=export_data,
        filename=f"goparkin_{dimension}_report",
        summary=combined
    )
