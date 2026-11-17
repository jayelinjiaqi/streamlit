
import streamlit as st

from shared_data import get_filtered_data
from utils.dashboard import render_dimension_dashboard


# ==================================================
# LOAD FILTERED DATA
# ==================================================

filtered, date_col = get_filtered_data()


# ==================================================
# RENDER OPERATOR DASHBOARD
# ==================================================

render_dimension_dashboard(
    filtered=filtered,
    dimension="car_park_operator",
    dimension_label="Car Park Operator",
    page_title="EV Billing Analytics By Operator"
)
