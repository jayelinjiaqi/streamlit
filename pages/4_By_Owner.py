
from shared_data import get_filtered_data
import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.title("EV Billing Summary By Car Park Owner")

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

if "car_park_owner" not in filtered.columns:
    st.error("car_park_owner column was not found.")
    st.stop()


# --------------------------------------------------
# CLEAN DATA
# --------------------------------------------------

filtered = filtered.copy()

filtered["car_park_owner"] = (
    filtered["car_park_owner"]
    .fillna("Unknown")
    .astype(str)
)

filtered["payment_amount"] = pd.to_numeric(
    filtered["payment_amount"],
    errors="coerce"
)

filtered["ci_power"] = pd.to_numeric(
    filtered["ci_power"],
    errors="coerce"
)


# --------------------------------------------------
# SHARED OWNER FILTERS
# --------------------------------------------------

st.subheader("Owner Filters")

col1, col2 = st.columns([1, 2])

with col1:

    limit_choice = st.selectbox(
        "Number of owners",
        ["Top 10", "Top 20", "Top 30", "Top 50", "All"],
        index=1,
        key="shared_owner_limit"
    )

with col2:

    all_owners = sorted(
        filtered["car_park_owner"].unique().tolist()
    )

    selected_owner_search = st.selectbox(
        "Search car park owner",
        options=["All Owners"] + all_owners,
        index=0,
        key="shared_owner_search",
        placeholder="Type owner name..."
    )


# --------------------------------------------------
# TOP N FILTER
# --------------------------------------------------

limit_options = {
    "Top 10": 10,
    "Top 20": 20,
    "Top 30": 30,
    "Top 50": 50,
    "All": len(all_owners)
}

limit = limit_options[limit_choice]


# --------------------------------------------------
# DYNAMIC CHART HEIGHT
# --------------------------------------------------

def get_chart_height(number_of_rows):
    return max(450, min(number_of_rows * 35 + 100, 1600))


# --------------------------------------------------
# PREPARE DATA
# --------------------------------------------------

valid_data = filtered.dropna(
    subset=["report_date"]
).copy()


# ==================================================
# 1. PAYMENT BY OWNER
# ==================================================

st.divider()
st.subheader("Total Payment By Car Park Owner")

owner_payment = (
    valid_data
    .groupby("car_park_owner", as_index=False)
    .agg(
        payment_amount=("payment_amount", "sum"),
        transactions=("payment_amount", "count")
    )
    .sort_values("payment_amount", ascending=False)
)


# --------------------------------------------------
# APPLY SEARCH AND TOP N
# --------------------------------------------------

if selected_owner_search != "All Owners":

    payment_display = owner_payment[
        owner_payment["car_park_owner"]
        == selected_owner_search
    ].copy()

else:

    payment_display = owner_payment.head(limit).copy()


st.caption(
    f"Displaying {len(payment_display):,} of "
    f"{len(owner_payment):,} owners."
)


# --------------------------------------------------
# PAYMENT CHART
# --------------------------------------------------

if payment_display.empty:

    st.info("No matching owners found.")

else:

    fig_payment = px.bar(
        payment_display,
        x="payment_amount",
        y="car_park_owner",
        orientation="h",
        custom_data=["transactions"],
        labels={
            "car_park_owner": "Car Park Owner",
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
        yaxis_title="Car Park Owner",
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
        key="owner_payment_chart",
        on_select="rerun",
        selection_mode="points"
    )

    # --------------------------------------------------
    # SELECT OWNER
    # --------------------------------------------------

    selected_points = event_payment.selection.points

    if selected_points:

        clicked_owner = selected_points[0]["y"]

        current_owner = st.session_state.get(
            "selected_payment_owner"
        )

        if current_owner == clicked_owner:
            st.session_state["selected_payment_owner"] = None
        else:
            st.session_state["selected_payment_owner"] = clicked_owner


# --------------------------------------------------
# MONTHLY PAYMENT BREAKDOWN
# --------------------------------------------------

selected_payment_owner = st.session_state.get(
    "selected_payment_owner"
)

if selected_owner_search != "All Owners":
    payment_monthly_owner = selected_owner_search
else:
    payment_monthly_owner = selected_payment_owner


if payment_monthly_owner is not None:

    st.divider()

    st.subheader(
        f"Monthly Payment Breakdown - {payment_monthly_owner}"
    )

    owner_monthly = (
        valid_data[
            valid_data["car_park_owner"]
            == payment_monthly_owner
        ]
        .groupby("month", as_index=False)
        .agg(
            payment_amount=("payment_amount", "sum"),
            transactions=("payment_amount", "count")
        )
        .sort_values("month")
    )

    if not owner_monthly.empty:

        fig_monthly = px.bar(
            owner_monthly,
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
            owner_monthly,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No monthly payment records found.")


# ==================================================
# 2. ENERGY BY OWNER
# ==================================================

st.divider()
st.subheader("Energy Delivered By Car Park Owner")

owner_energy = (
    valid_data
    .groupby("car_park_owner", as_index=False)
    .agg(
        energy_delivered=("ci_power", "sum"),
        transactions=("ci_power", "count")
    )
    .sort_values("energy_delivered", ascending=False)
)


# --------------------------------------------------
# APPLY SAME SEARCH AND TOP N
# --------------------------------------------------

if selected_owner_search != "All Owners":

    energy_display = owner_energy[
        owner_energy["car_park_owner"]
        == selected_owner_search
    ].copy()

else:

    energy_display = owner_energy.head(limit).copy()


st.caption(
    f"Displaying {len(energy_display):,} of "
    f"{len(owner_energy):,} owners."
)


# --------------------------------------------------
# ENERGY CHART
# --------------------------------------------------

if energy_display.empty:

    st.info("No matching owners found.")

else:

    fig_energy = px.bar(
        energy_display,
        x="energy_delivered",
        y="car_park_owner",
        orientation="h",
        custom_data=["transactions"],
        labels={
            "car_park_owner": "Car Park Owner",
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
        yaxis_title="Car Park Owner",
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
        key="owner_energy_chart",
        on_select="rerun",
        selection_mode="points"
    )

    # --------------------------------------------------
    # SELECT OWNER
    # --------------------------------------------------

    selected_points = event_energy.selection.points

    if selected_points:

        clicked_owner = selected_points[0]["y"]

        current_owner = st.session_state.get(
            "selected_energy_owner"
        )

        if current_owner == clicked_owner:
            st.session_state["selected_energy_owner"] = None
        else:
            st.session_state["selected_energy_owner"] = clicked_owner


# --------------------------------------------------
# MONTHLY ENERGY BREAKDOWN
# --------------------------------------------------

selected_energy_owner = st.session_state.get(
    "selected_energy_owner"
)

if selected_owner_search != "All Owners":
    energy_monthly_owner = selected_owner_search
else:
    energy_monthly_owner = selected_energy_owner


if energy_monthly_owner is not None:

    st.divider()

    st.subheader(
        f"Monthly Energy Breakdown - {energy_monthly_owner}"
    )

    owner_monthly_energy = (
        valid_data[
            valid_data["car_park_owner"]
            == energy_monthly_owner
        ]
        .groupby("month", as_index=False)
        .agg(
            energy_delivered=("ci_power", "sum"),
            transactions=("ci_power", "count")
        )
        .sort_values("month")
    )

    if not owner_monthly_energy.empty:

        fig_energy_monthly = px.bar(
            owner_monthly_energy,
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
            owner_monthly_energy,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No monthly energy records found.")
