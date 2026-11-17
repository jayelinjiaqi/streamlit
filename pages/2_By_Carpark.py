import streamlit as st
import shared_data

st.write("Loaded shared_data from:")
st.code(shared_data.__file__)

st.write("Has get_filtered_data:")
st.write(hasattr(shared_data, "get_filtered_data"))

st.write("Available filter functions:")
st.write([
    name for name in dir(shared_data)
    if "filter" in name.lower()
])

if not hasattr(shared_data, "get_filtered_data"):
    st.error("get_filtered_data() is missing from the loaded module.")
    st.stop()

from utils.dashboard import render_dimension_dashboard

filtered, date_col = shared_data.get_filtered_data()

render_dimension_dashboard(
    filtered=filtered,
    dimension="car_park_name",
    dimension_label="Car Park",
    page_title="EV Billing Summary By Carpark"
)
