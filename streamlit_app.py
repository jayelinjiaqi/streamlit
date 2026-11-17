
import os
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

st.set_page_config(
    page_title="GoParkin | EV Billing & Analytics",
    page_icon=os.path.join(ASSETS_DIR, "favicon.png"),
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------
# BRANDING
# --------------------------------------------------

logo_path = os.path.join(
    ASSETS_DIR,
    "goparkin_logo.png"
)

if os.path.exists(logo_path):
    st.logo(logo_path, size="large")

# --------------------------------------------------
# GLOBAL STYLING
# --------------------------------------------------

from utils.styles import apply_styles

apply_styles()

# --------------------------------------------------
# NAVIGATION
# --------------------------------------------------

pages = {
    "EV Billing Analytics": [
        st.Page(
            os.path.join(BASE_DIR, "pages", "1_By_Month.py"),
            title="Overview By Month",
            icon=":material/calendar_month:",
            default=True
        ),
        st.Page(
            os.path.join(BASE_DIR, "pages", "2_By_Carpark.py"),
            title="By Carpark",
            icon=":material/local_parking:"
        ),
        st.Page(
            os.path.join(BASE_DIR, "pages", "3_By_Operator.py"),
            title="By Operator",
            icon=":material/business:"
        ),
        st.Page(
            os.path.join(BASE_DIR, "pages", "4_By_Owner.py"),
            title="By Owner",
            icon=":material/domain:"
        )
    ]
}

pg = st.navigation(pages)

pg.run()
