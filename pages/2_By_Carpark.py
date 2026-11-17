
import streamlit as st

from shared_data import get_filtered_data
from utils.dashboard import render_dimension_dashboard


# Load filtered EV billing data
filtered, date_col = get_filtered_data()


# Render By Carpark dashboard
render_dimension_dashboard(
    filtered=filtered,
    dimension="car_park_name",
    dimension_label="Carpark",
    page_title="EV Billing Analytics By Carpark"
)

