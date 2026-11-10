
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Monthly Payment Details",layout="wide")

# --------------------------------------------------
# GET SELECTED MONTH
# --------------------------------------------------
selected_month = st.session_state.get("selected_payment_month")

detail_data = st.session_state.get("payment_detail_data")

if selected_month is None or detail_data is None:
    st.warning("Please select a month from the dashboard.")
    if st.button("Back to Dashboard"):
        st.switch_page("streamlit_app.py")
    st.stop()

# --------------------------------------------------
# FILTER SELECTED MONTH
# --------------------------------------------------
monthly_data = detail_data[detail_data["month"] == selected_month].copy()

st.title("EV | Monthly Payment Details")
st.subheader(f"Payment Breakdown - {selected_month}")

if monthly_data.empty:
    st.warning("No payment records found.")
    st.stop()

# --------------------------------------------------
# KPI SUMMARY
# --------------------------------------------------
total_payment = monthly_data["payment_amount"].sum()
transaction_count = len(monthly_data)
carpark_count = monthly_data["car_park_id"].nunique()

k1, k2, k3 = st.columns(3)

k1.metric("Total Payments",f"${total_payment:,.2f}")
k2.metric("Transactions",f"{transaction_count:,}")
k3.metric("Car Parks",f"{carpark_count:,}")

st.divider()

# --------------------------------------------------
# PAYMENT BREAKDOWN BY CAR PARK
# --------------------------------------------------
st.subheader("Total Payment By Car Park")

carpark_payment = (
    monthly_data
    .groupby("car_park_name", as_index=False)
    .agg(payment_amount=("payment_amount", "sum"),transactions=("payment_amount", "size"))
    .sort_values("payment_amount", ascending=False)
)

fig = px.bar(carpark_payment,
    x="car_park_name",
    y="payment_amount",
    text="payment_amount",
    hover_data={"transactions": True},
    labels={"car_park_name": "Car Park","payment_amount": "Total Payment","transactions": "Transactions"},
    template="plotly_white",
    color_discrete_sequence=["#00A99D"]
)

fig.update_traces(texttemplate="$%{text:,.2f}",textposition="outside",cliponaxis=False)

fig.update_layout(height=500,showlegend=False,xaxis_title="Car Park",yaxis_title="Total Payment",
    yaxis_tickprefix="$",yaxis_tickformat=",.2f")

st.plotly_chart(fig, use_container_width=True)

st.divider()

# --------------------------------------------------
# PAYMENT DETAIL TABLE
# --------------------------------------------------
st.subheader("Car Park Payment Summary")

display_data = carpark_payment.rename(columns={"car_park_name": "Car Park Name",
    "payment_amount": "Total Payment","transactions": "Transactions"})

st.dataframe(display_data.style.format({"Total Payment": "${:,.2f}"
    }),use_container_width=True,hide_index=True)

# --------------------------------------------------
# NAVIGATION
# --------------------------------------------------
if st.button("← Back to Dashboard"):
    st.switch_page("streamlit_app.py")
