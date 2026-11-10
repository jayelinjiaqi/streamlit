import streamlit as st

# Global page configuration (keep this in the router)
st.set_page_config(
    page_title="EV Payments Dashboard",
    page_icon="assets/favicon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Define your pages using st.Page
dashboard_page = st.Page("pages/1_EV_Billing_Summary.py", title="EV Billing Summary", default=True)
monthly_details_page = st.Page("pages/2_Monthly_Payment_Details.py", title="Monthly Payment Details")

# Run navigation
pg = st.navigation([dashboard_page, monthly_details_page])
pg.run()
