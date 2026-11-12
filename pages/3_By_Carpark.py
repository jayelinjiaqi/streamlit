from shared_data import get_filtered_data
import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------------------------------
# PAGE: BY CARPARK
# --------------------------------------------------
st.title("EV Billing Summary By Carpark")

# Get shared data from app.py
filtered, date_col = get_filtered_data()



# --------------------------------------------------
# PAYMENT BY CAR PARK NAME
# --------------------------------------------------
st.subheader("Total Payment By Carpark")
if date_col is None:
    st.warning("No supported date column was found.")
elif filtered.empty or filtered["report_date"].notna().sum() == 0:
    st.info("No valid transactions match the selected filters.")
else:
    carpark_payment = (
        filtered.dropna(subset=["report_date"])
        .groupby("car_park_name", as_index=False)
        .agg(payment_amount=("payment_amount", "sum"),
            transactions=("payment_amount", "size")
        )
        .sort_values("payment_amount", ascending=False)
    )

    fig_payment = px.bar(
        carpark_payment,
        x="payment_amount",
        y="car_park_name",
        orientation="h",
        text="payment_amount",
        hover_data={"transactions": True},
        labels={
            "car_park_name": "Car Park Name",
            "payment_amount": "Payment Amount",
            "transactions": "Transactions"
        },
        template="plotly_white",
        color_discrete_sequence=["#00A99D"]
    )

    fig_payment.update_traces(
        texttemplate="$%{text:,.2f}",
        textposition="outside",
        cliponaxis=False,
        hovertemplate=(
            "Car Park: %{y}<br>"
            "Payment: $%{x:,.2f}<br>"
            "Transactions: %{customdata[0]}<br>"
            "<extra></extra>"
        )
    )

    fig_payment.update_layout(
        height=600,
        margin=dict(t=30, b=30, l=20, r=100),
        xaxis_title="Total Payment",
        yaxis_title="Car Park Name",
        xaxis_tickprefix="$",
        xaxis_tickformat=",.2f",
        yaxis=dict(categoryorder="total ascending"),
        showlegend=False
    )

    event = st.plotly_chart(
        fig_payment,
        use_container_width=True,
        key="carpark_payment_chart",
        on_select="rerun",
        selection_mode="points"
    )

    # Get selected car park
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

    selected_carpark = st.session_state.get("selected_carpark")

    # Monthly payment breakdown
    if selected_carpark is not None:

        st.divider()

        st.subheader(
            f"Monthly Payment Breakdown - {selected_carpark}"
        )

        carpark_monthly = (
            filtered[
                filtered["car_park_name"] == selected_carpark
            ]
            .dropna(subset=["report_date"])
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
                text="payment_amount",
                hover_data={"transactions": True},
                template="plotly_white",
                color_discrete_sequence=["#00A99D"]
            )

            fig_monthly.update_traces(
                texttemplate="$%{text:,.2f}",
                textposition="outside",
                cliponaxis=False
            )

            fig_monthly.update_layout(
                height=450,
                showlegend=False,
                xaxis_title="Month",
                yaxis_title="Total Payment",
                yaxis_tickprefix="$",
                yaxis_tickformat=",.2f"
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


# --------------------------------------------------
# ENERGY BY CAR PARK
# --------------------------------------------------

st.divider()
st.subheader("Energy Delivered By Carpark")

if date_col is None:
    st.warning("No supported date column was found.")

elif filtered.empty or filtered["report_date"].notna().sum() == 0:
    st.info("No valid transactions match the selected filters.")

else:

    carpark_energy = (
        filtered.dropna(subset=["report_date"])
        .groupby("car_park_name", as_index=False)
        .agg(
            energy_delivered=("ci_power", "sum"),
            transactions=("ci_power", "count")
        )
        .sort_values("energy_delivered", ascending=False)
    )

    fig_energy = px.bar(
        carpark_energy,
        x="energy_delivered",
        y="car_park_name",
        orientation="h",
        text="energy_delivered",
        hover_data={"transactions": True},
        labels={
            "car_park_name": "Car Park Name",
            "energy_delivered": "Energy Delivered",
            "transactions": "Transactions"
        },
        template="plotly_white",
        color_discrete_sequence=["#00A99D"]
    )

    fig_energy.update_traces(
        texttemplate="%{text:,.0f} kWh",
        textposition="outside",
        cliponaxis=False,
        hovertemplate=(
            "Car Park: %{y}<br>"
            "Energy: %{x:,.2f} kWh<br>"
            "Transactions: %{customdata[0]}<br>"
            "<extra></extra>"
        )
    )

    fig_energy.update_layout(
        height=600,
        margin=dict(t=30, b=30, l=20, r=110),
        xaxis_title="Total Energy Delivered (kWh)",
        yaxis_title="Car Park Name",
        xaxis_ticksuffix=" kWh",
        xaxis_tickformat=",.0f",
        yaxis=dict(categoryorder="total ascending"),
        showlegend=False
    )

    event_energy = st.plotly_chart(
        fig_energy,
        use_container_width=True,
        key="carpark_energy_chart",
        on_select="rerun",
        selection_mode="points"
    )

    # Get selected car park
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

    # Monthly energy breakdown
    if selected_energy_carpark is not None:

        st.divider()

        st.subheader(
            f"Monthly Energy Breakdown - {selected_energy_carpark}"
        )

        carpark_monthly_energy = (
            filtered[
                filtered["car_park_name"] == selected_energy_carpark
            ]
            .dropna(subset=["report_date"])
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
                text="energy_delivered",
                hover_data={"transactions": True},
                template="plotly_white",
                color_discrete_sequence=["#00A99D"]
            )

            fig_energy_monthly.update_traces(
                texttemplate="%{text:,.0f} kWh",
                textposition="outside",
                cliponaxis=False
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
