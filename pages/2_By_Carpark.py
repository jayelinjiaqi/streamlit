import sys
import os

# Adds the root project folder to Python's search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import streamlit as st
from shared_data import get_filtered_data
from utils.dashboard import render_dimension_dashboard


filtered, date_col = get_filtered_data()

render_dimension_dashboard(
    filtered=filtered,
    dimension="car_park_name",
    dimension_label="Car Park",
    page_title="EV Billing Summary By Carpark"
)
