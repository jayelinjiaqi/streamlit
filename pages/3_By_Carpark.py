
from shared_data import get_filtered_data
import streamlit as st
import pandas as pd
import plotly.express as px

# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.title("EV Billing Summary By Carpark")

CHART_COLOR = "#00A99D"

filtered, date_col = get_filtered_data()

# ==================================================
# CHECK DATA
# ==================================================

if filtered.empty:
    st.warning("No transactions match the selected filters.")
    st.stop()

if date_col is None:
    st.warning("No supported date column was found.")
    st.stop()

if filtered["report_date"].notna().sum() == 0:
    st.warning("No valid transaction dates are available.")
    st.stop()

# Make car park names consistent
filtered = filtered.copy()

filtered["car_park_name"] = (
    filtered["car_park_name"]
    .fillna("Unknown")
    .astype(str)
)

# ==================================================
# PREPARE CAR PARK DATA
# ==================================================

valid_data = filtered.dropna(subset=["report_date"])

carpark_payment = (
    valid_data
    .groupby("car_park_name", as_index=False)
    .agg(
        payment_amount=("payment_amount", "sum"),
        transactions=("payment_amount", "size")
    )
    .sort_values("payment_amount", ascending=False)
)

carpark_energy = (
    valid_data
    .groupby("car_park_name", as_index=False)
    .agg(
        energy_delivered=("ci_power", "sum"),
        transactions=("ci_power", "count")
    )
    .sort_values("energy_delivered", ascending=False)
)

# ==================================================
# SHARED CAR PARK FILTERS
# ==================================================

st.subheader("Car Park Filters")

col1, col2 = st.columns([1, 2])

all_carparks = sorted(
    filtered["car_park_name"].unique().tolist()
)

with col1:

    limit_choice = st.selectbox(
        "Number of car parks",
        ["Top 10", "Top 20", "Top 30", "Top 50", "All"],
        index=1,
        key="shared_carpark_limit"
    )

with col2:

    selected_carpark_search = st.selectbox(
        "Search car park",
        options=["All Car Parks"] + all_carparks,
        index=0,
        key="shared_carpark_search",
        placeholder="Type to search car park..."
    )

# ==================================================
# APPLY SHARED FILTERS
# ==================================================

limit_options = {
    "Top 10": 10,
    "Top 20": 20,
    "Top 30": 30,
    "Top 50": 50,
    "All": len(all_carparks)
}

if selected_carpark_search != "All Car Parks":

    # Show only the searched car park
    payment_display = carpark_payment[
        carpark_payment["car_park_name"]
        == selected_carpark_search
    ].copy()

    energy_display = carpark_energy[
        carpark_energy["car_park_name"]
        == selected_carpark_search
    ].copy()

else:

    # Apply Top N to both charts
    limit = limit_options[limit_choice]

    payment_display = carpark_payment.head(limit).copy()

    energy_display = carpark_energy.head(limit).copy()

# Display filter information
if selected_carpark_search != "All Car Parks":

    st.caption(
        f"Showing selected car park: {selected_carpark_search}"
    )

else:

    st.caption(
        f"Showing up to {limit_options[limit_choice]} car parks "
        f"out of {len(all_carparks)}."
    )

# ==================================================
# DYNAMIC CHART HEIGHT
# ==================================================

def get_chart_height(number_of_rows):

    return max(
        450,
        min(number_of_rows * 35 + 100, 1600)
    )

# ==================================================
# 1. PAYMENT BY CAR PARK
# ==================================================

st.divider()

st.subheader("Total Payment By Carpark")

if payment_display.empty:

    st.info("No matching car parks found.")

else:

    fig_payment = px.bar(
        payment_display,
        x="payment_amount",
        y="car_park_name",
        orientation="h",
        custom_data=["transactions"],
        labels={
            "car_park_name": "Car Park Name",
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
        yaxis_title="Car Park Name",
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

    event = st.plotly_chart(
        fig_payment,
        use_container_width=True,
        key="carpark_payment_chart",
        on_select="rerun",
        selection_mode="points"
    )

    # ----------------------------------------------
    # SELECT CAR PARK
    # ----------------------------------------------

    selected_points = event.selection.points

    if selected_points:

        clicked_carpark = selected_points[0]["y"]

        current_carpark = st.session_state.get(
            "selected_carpark"
        )

        if current_carpark == clicked_carpark:

            st.session_state["selected_carpark"] = None

        else:

            st.session_state["selected_carpark"] = clicked_carpark

    selected_carpark = st.session_state.get(
        "selected_carpark"
    )

    # ----------------------------------------------
    # MONTHLY PAYMENT BREAKDOWN
    # ----------------------------------------------

    if selected_carpark is not None:

        st.divider()

        st.subheader(
            f"Monthly Payment Breakdown - {selected_carpark}"
        )

        carpark_monthly = (
            valid_data[
                valid_data["car_park_name"] == selected_carpark
            ]
            .groupby("month", as_index=False)
            .agg(
                payment_amount=("payment_amount", "sum"),
                transactions=("payment_amount", "size")
            )
            .sort_values("month")
        )

        if not carpark_monthly.empty:

            fig_monthly = px.bar(
                carpark_monthly,
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
                carpark_monthly,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info("No monthly payment records found.")

# ==================================================
# 2. ENERGY BY CAR PARK
# ==================================================

st.divider()

st.subheader("Energy Delivered By Carpark")

if energy_display.empty:

    st.info("No matching car parks found.")

else:

    fig_energy = px.bar(
        energy_display,
        x="energy_delivered",
        y="car_park_name",
        orientation="h",
        custom_data=["transactions"],
        labels={
            "car_park_name": "Car Park Name",
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
        margin=dict(t=30, b=40, l=20, r=50),
        xaxis_title="Total Energy Delivered (kWh)",
        yaxis_title="Car Park Name",
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
        key="carpark_energy_chart",
        on_select="rerun",
        selection_mode="points"
    )

    # ----------------------------------------------
    # SELECT CAR PARK
    # ----------------------------------------------

    selected_points = event_energy.selection.points

    if selected_points:

        clicked_carpark = selected_points[0]["y"]

        current_carpark = st.session_state.get(
            "selected_energy_carpark"
        )

        if current_carpark == clicked_carpark:

            st.session_state["selected_energy_carpark"] = None

        else:

            st.session_state["selected_energy_carpark"] = clicked_carpark

    selected_energy_carpark = st.session_state.get(
        "selected_energy_carpark"
    )

    # ----------------------------------------------
    # MONTHLY ENERGY BREAKDOWN
    # ----------------------------------------------

    if selected_energy_carpark is not None:

        st.divider()

        st.subheader(
            f"Monthly Energy Breakdown - {selected_energy_carpark}"
        )

        carpark_monthly_energy = (
            valid_data[
                valid_data["car_park_name"]
                == selected_energy_carpark
            ]
            .groupby("month", as_index=False)
            .agg(
                energy_delivered=("ci_power", "sum"),
                transactions=("ci_power", "count")
            )
            .sort_values("month")
        )

        if not carpark_monthly_energy.empty:

            fig_energy_monthly = px.bar(
                carpark_monthly_energy,
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
                carpark_monthly_energy,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info("No monthly energy records found.")
