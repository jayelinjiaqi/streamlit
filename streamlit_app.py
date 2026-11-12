import streamlit as st
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------
st.set_page_config(
    page_title="EV Payments Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------
# PAGE 1 - EV BILLING SUMMARY
# --------------------------------------------------
dashboard_page = st.Page(
    os.path.join(BASE_DIR, "pages", "1_EV_Billing_Summary.py"),
    title="EV Billing Summary",
    default=True
)

# --------------------------------------------------
# PAGE 2 - BY CARPARK
# --------------------------------------------------
carpark_page = st.Page(
    os.path.join(BASE_DIR, "pages", "3_By_Carpark.py"),
    title="EV Billing Summary by Carpark"
)

# --------------------------------------------------
# PAGE 3 - MONTHLY PAYMENT DETAILS
# --------------------------------------------------
monthly_details_page = st.Page(
    os.path.join(BASE_DIR, "pages", "2_Monthly_Payment_Details.py"),
    title="Monthly Payment Details"
)

# --------------------------------------------------
# LEFT SIDEBAR NAVIGATION
# --------------------------------------------------
pg = st.navigation([
    dashboard_page,
    carpark_page,
    monthly_details_page
])

# --------------------------------------------------
# RUN SELECTED PAGE
# --------------------------------------------------
pg.run()
