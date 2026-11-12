
import os
import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------------------------------
# LOGO
# --------------------------------------------------
BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

LOGO_PATH = os.path.join(
    BASE_DIR, "assets", "goparkin_logo.png"
)

if os.path.exists(LOGO_PATH):
    st.logo(LOGO_PATH, size="large")

# --------------------------------------------------
# GET SELECTED MONTH
# --------------------------------------------------
selected_month = st.session_state.get(
    "selected_payment_month"
)

detail_data = st.session_state.get(
    "payment_detail_data"
)

if selected_month is None or detail_data is None:

    st.warning("Please select a month from the dashboard.")

    if st.button("← Back to Dashboard"):
        st.switch_page(
            "pages/1_EV_Billing_Summary.py"
        )

    st.stop()

# --------------------------------------------------
# FILTER SELECTED MONTH
# --------------------------------------------------
monthly_data = detail_data.copy()

monthly_data["month"] = (
    monthly_data["month"].astype(str)
)

monthly_data = monthly_data[
    monthly_data["month"] == str(selected_month)
].copy()

st.title("EV | Monthly Payment Details")

st.subheader(
    f"Payment Breakdown - {selected_month}"
)

if monthly_data.empty:
    st.warning("No payment records found.")

    if st.button("← Back to Dashboard"):
        st.switch_page(
            "pages/1_EV_Billing_Summary.py"
        )

    st.stop()
