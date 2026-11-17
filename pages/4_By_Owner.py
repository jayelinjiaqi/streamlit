
import streamlit as st

from shared_data import get_filtered_data
from utils.dashboard import render_dimension_dashboard


# ==================================================
# LOAD FILTERED DATA
# ==================================================

filtered, date_col = get_filtered_data()


# ==================================================
# RENDER OWNER DASHBOARD
# ==================================================

render_dimension_dashboard(
    filtered=filtered,
    dimension="car_park_owner",
    dimension_label="Car Park Owner",
    page_title="EV Billing Analytics By Owner"
)
