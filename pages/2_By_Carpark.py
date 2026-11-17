import streamlit as st
import shared_data

st.write("Module location:", shared_data.__file__)

st.write(
    "Function exists:",
    hasattr(shared_data, "get_filtered_data")
)

st.write(
    "Available functions:",
    [x for x in dir(shared_data) if not x.startswith("_")]
)
