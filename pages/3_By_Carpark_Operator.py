
from shared_data import get_filtered_data
import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.title("EV Billing Summary By Car Park Operator")

CHART_COLOR = "#00A99D"

filtered, date_col = get_filtered_data()


# --------------------------------------------------
# VALIDATE DATA
# --------------------------------------------------

if filtered.empty:
    st.warning("No transactions match the selected filters.")
    st.stop()

if date_col is None:
    st.warning("No supported date column was found.")
    st.stop()

if filtered["report_date"].notna().sum() == 0:
    st.warning("No valid transaction dates are available.")
    st.stop()

if "car_park_operator" not in filtered.columns:
    st.error("car_park_operator column was not found.")
    st.stop()


# --------------------------------------------------
# CLEAN DATA
# --------------------------------------------------

filtered = filtered.copy()

filtered["car_park_operator"] = (
    filtered["car_park_operator"]
    .fillna("Unknown")
    .astype(str)
)

filtered["payment_amount"] = pd.to_numeric(
    filtered["payment_amount"], errors="coerce"
)

filtered["ci_power"] = pd.to_numeric(
    filtered["ci_power"], errors="coerce"
)


# --------------------------------------------------
# SHARED OPERATOR FILTERS
# --------------------------------------------------

st.subheader("Operator Filters")

col1, col2 = st.columns([1, 2])

with col1:

    limit_choice = st.selectbox(
        "Number of operators",
        ["Top 10", "Top 20", "Top 30", "Top 50", "All"],
        index=1,
        key="shared_operator_limit"
    )

with col2:

    all_operators = sorted(
        filtered["car_park_operator"].unique().tolist()
    )

    selected_operator_search = st.selectbox(
        "Search car park operator",
        options=["All Operators"] + all_operators,
        index=0,
        key="shared_operator_search",
        placeholder="Type operator name..."
    )


# --------------------------------------------------
# NUMBER OF OPERATORS
# --------------------------------------------------

limit_options = {
    "Top 10": 10,
    "Top 20": 20,
    "Top 30": 30,
    "Top 50": 50,
    "All": len(all_operators)
}

limit = limit_options[limit_choice]


# --------------------------------------------------
# CHART HEIGHT
# --------------------------------------------------

def get_chart_height(number_of_rows):
    return max(450, min(number_of_rows * 35 + 100, 1600))


# --------------------------------------------------
# PREPARE CHART DATA
# --------------------------------------------------

valid_data = filtered.dropna(subset=["report_date"]).copy()


# ==================================================
# 1. TOTAL PAYMENT BY OPERATOR
# ==================================================

st.divider()
st.subheader("Total Payment By Car Park Operator")

operator_payment = (
    valid_data
    .groupby("car_park_operator", as_index=False)
    .agg(
        payment_amount=("payment_amount", "sum"),
        transactions=("payment_amount", "count")
    )
    .sort_values("payment_amount", ascending=False)
)


# --------------------------------------------------
# APPLY SHARED SEARCH AND TOP N FILTER
# --------------------------------------------------

if selected_operator_search != "All Operators":

    payment_display = operator_payment[
        operator_payment["car_park_operator"]
        == selected_operator_search
    ].copy()

else:

    payment_display = operator_payment.head(limit).copy()


st.caption(
    f"Displaying {len(payment_display):,} of "
    f"{len(operator_payment):,} operators."
)


# --------------------------------------------------
# PAYMENT CHART
# --------------------------------------------------

if payment_display.empty:

    st.info("No matching operators found.")

else:

    fig_payment = px.bar(
        payment_display,
        x="payment_amount",
        y="car_park_operator",
        orientation="h",
        custom_data=["transactions"],
        labels={
            "car_park_operator": "Car Park Operator",
            "payment_amount": "Payment Amount"
        },
        template="plotly_white",
        color_discrete_sequence=[CHART_COLOR]
    )

    fig_payment.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Payment: $%{x:,.2f}<br>"
            "Transactions: %{customdata[0]:,}"
            "<extra></extra>"
        )
    )

    fig_payment.update_layout(
        height=get_chart_height(len(payment_display)),
        margin=dict(t=30, b=40, l=20, r=50),
        xaxis_title="Total Payment ($)",
        yaxis_title="Car Park Operator",
        xaxis_tickprefix="$",
        xaxis_tickformat=",.0f",
        yaxis=dict(
            categoryorder="total ascending",
            automargin=True
        ),
        showlegend=False,
        bargap=0.25,
        font=dict(size=12)
    )

    event_payment = st.plotly_chart(
        fig_payment,
        use_container_width=True,
        key="operator_payment_chart",
        on_select="rerun",
        selection_mode="points"
    )

    # --------------------------------------------------
    # SELECT OPERATOR FROM PAYMENT CHART
    # --------------------------------------------------

    selected_points = event_payment.selection.points

    if selected_points:

        clicked_operator = selected_points[0]["y"]

        current_operator = st.session_state.get(
            "selected_payment_operator"
        )

        if current_operator == clicked_operator:
            st.session_state["selected_payment_operator"] = None
        else:
            st.session_state["selected_payment_operator"] = (
                clicked_operator
            )


# --------------------------------------------------
# PAYMENT MONTHLY BREAKDOWN
# --------------------------------------------------

selected_payment_operator = st.session_state.get(
    "selected_payment_operator"
)

# Search selection takes priority over chart selection
if selected_operator_search != "All Operators":
    payment_monthly_operator = selected_operator_search
else:
    payment_monthly_operator = selected_payment_operator


if payment_monthly_operator is not None:

    st.divider()

    st.subheader(
        f"Monthly Payment Breakdown - {payment_monthly_operator}"
    )

    operator_monthly = (
        valid_data[
            valid_data["car_park_operator"]
            == payment_monthly_operator
        ]
        .groupby("month", as_index=False)
        .agg(
            payment_amount=("payment_amount", "sum"),
            transactions=("payment_amount", "count")
        )
        .sort_values("month")
    )

    if not operator_monthly.empty:

        fig_monthly = px.bar(
            operator_monthly,
            x="month",
            y="payment_amount",
            custom_data=["transactions"],
            template="plotly_white",
            color_discrete_sequence=[CHART_COLOR]
        )

        fig_monthly.update_traces(
            hovertemplate=(
                "Month: %{x}<br>"
                "Payment: $%{y:,.2f}<br>"
                "Transactions: %{customdata[0]:,}"
                "<extra></extra>"
            )
        )

        fig_monthly.update_layout(
            height=450,
            showlegend=False,
            xaxis_title="Month",
            yaxis_title="Total Payment ($)",
            yaxis_tickprefix="$",
            yaxis_tickformat=",.0f"
        )

        st.plotly_chart(
            fig_monthly,
            use_container_width=True
        )

        st.dataframe(
            operator_monthly,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No monthly payment records found.")


# ==================================================
# 2. ENERGY DELIVERED BY OPERATOR
# ==================================================

st.divider()
st.subheader("Energy Delivered By Car Park Operator")

operator_energy = (
    valid_data
    .groupby("car_park_operator", as_index=False)
    .agg(
        energy_delivered=("ci_power", "sum"),
        transactions=("ci_power", "count")
    )
    .sort_values("energy_delivered", ascending=False)
)


# --------------------------------------------------
# APPLY SAME SEARCH AND TOP N FILTER
# --------------------------------------------------

if selected_operator_search != "All Operators":

    energy_display = operator_energy[
        operator_energy["car_park_operator"]
        == selected_operator_search
    ].copy()

else:

    energy_display = operator_energy.head(limit).copy()


st.caption(
    f"Displaying {len(energy_display):,} of "
    f"{len(operator_energy):,} operators."
)


# --------------------------------------------------
# ENERGY CHART
# --------------------------------------------------

if energy_display.empty:

    st.info("No matching operators found.")

else:

    fig_energy = px.bar(
        energy_display,
        x="energy_delivered",
        y="car_park_operator",
        orientation="h",
        custom_data=["transactions"],
        labels={
            "car_park_operator": "Car Park Operator",
            "energy_delivered": "Energy Delivered"
        },
        template="plotly_white",
        color_discrete_sequence=[CHART_COLOR]
    )

    fig_energy.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Energy: %{x:,.2f} kWh<br>"
            "Transactions: %{customdata[0]:,}"
            "<extra></extra>"
        )
    )

    fig_energy.update_layout(
        height=get_chart_height(len(energy_display)),
        margin=dict(t=30, b=40, l=20, r=60),
        xaxis_title="Total Energy Delivered (kWh)",
        yaxis_title="Car Park Operator",
        xaxis_ticksuffix=" kWh",
        xaxis_tickformat=",.0f",
        yaxis=dict(
            categoryorder="total ascending",
            automargin=True
        ),
        showlegend=False,
        bargap=0.25,
        font=dict(size=12)
    )

    event_energy = st.plotly_chart(
        fig_energy,
        use_container_width=True,
        key="operator_energy_chart",
        on_select="rerun",
        selection_mode="points"
    )


    # --------------------------------------------------
    # SELECT OPERATOR FROM ENERGY CHART
    # --------------------------------------------------

    selected_points = event_energy.selection.points

    if selected_points:

        clicked_operator = selected_points[0]["y"]

        current_operator = st.session_state.get(
            "selected_energy_operator"
        )

        if current_operator == clicked_operator:
            st.session_state["selected_energy_operator"] = None
        else:
            st.session_state["selected_energy_operator"] = (
                clicked_operator
            )


# --------------------------------------------------
# ENERGY MONTHLY BREAKDOWN
# --------------------------------------------------

selected_energy_operator = st.session_state.get(
    "selected_energy_operator"
)

# Search selection takes priority over chart selection
if selected_operator_search != "All Operators":
    energy_monthly_operator = selected_operator_search
else:
    energy_monthly_operator = selected_energy_operator


if energy_monthly_operator is not None:

    st.divider()

    st.subheader(
        f"Monthly Energy Breakdown - {energy_monthly_operator}"
    )

    operator_monthly_energy = (
        valid_data[
            valid_data["car_park_operator"]
            == energy_monthly_operator
        ]
        .groupby("month", as_index=False)
        .agg(
            energy_delivered=("ci_power", "sum"),
            transactions=("ci_power", "count")
        )
        .sort_values("month")
    )

    if not operator_monthly_energy.empty:

        fig_energy_monthly = px.bar(
            operator_monthly_energy,
            x="month",
            y="energy_delivered",
            custom_data=["transactions"],
            template="plotly_white",
            color_discrete_sequence=[CHART_COLOR]
        )

        fig_energy_monthly.update_traces(
            hovertemplate=(
                "Month: %{x}<br>"
                "Energy: %{y:,.2f} kWh<br>"
                "Transactions: %{customdata[0]:,}"
                "<extra></extra>"
            )
        )

        fig_energy_monthly.update_layout(
            height=450,
            showlegend=False,
            xaxis_title="Month",
            yaxis_title="Energy Delivered (kWh)",
            yaxis_ticksuffix=" kWh",
            yaxis_tickformat=",.0f"
        )

        st.plotly_chart(
            fig_energy_monthly,
            use_container_width=True
        )

        st.dataframe(
            operator_monthly_energy,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No monthly energy records found.")

