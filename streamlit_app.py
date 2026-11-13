
import streamlit as st
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

st.set_page_config(
    page_title="GoParkin | EV Billing Summary",
    layout="wide",
    initial_sidebar_state="expanded"
)

dashboard_page = st.Page(
    os.path.join(BASE_DIR, "pages", "1_EV_Billing_Summary.py"),
    title="By Month",
    default=True
)

carpark_page = st.Page(
    os.path.join(BASE_DIR, "pages", "2_By_Carpark.py"),
    title="By Carpark"
)

operator_page = st.Page(
    os.path.join(BASE_DIR, "pages", "3_By_Operator.py"),
    title="By Operator"
)

owner_page = st.Page(
    os.path.join(BASE_DIR, "pages", "4_By_Owner.py"),
    title="By Owner"
)

#monthly_details_page = st.Page(
#    os.path.join(BASE_DIR, "pages", "2_Monthly_Payment_Details.py"),
#    title="Monthly Payment Details"
#)

pg = st.navigation([
    dashboard_page,
    carpark_page,
    operator_page,
    owner_page
])

pg.run()
