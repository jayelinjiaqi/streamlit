
import os
import streamlit as st

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

ASSETS_DIR = os.path.join(
    BASE_DIR,
    "assets"
)

st.set_page_config(
    page_title="GoParkin | EV Billing Summary",
    page_icon=os.path.join(
        ASSETS_DIR,
        "favicon.png"
    ),
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================================================
# BRANDING
# ==================================================

LOGO_PATH = os.path.join(
    ASSETS_DIR,
    "goparkin_logo.png"
)

if os.path.exists(LOGO_PATH):

    st.logo(
        LOGO_PATH,
        size="large"
    )

# ==================================================
# NAVIGATION
# ==================================================

pages = {

    "EV Billing Summary": [

        st.Page(
            os.path.join(
                BASE_DIR,
                "pages",
                "1_By_Month.py"
            ),
            title="By Month",
            default=True
        ),

        st.Page(
            os.path.join(
                BASE_DIR,
                "pages",
                "2_By_Carpark.py"
            ),
            title="By Carpark"
        ),

        st.Page(
            os.path.join(
                BASE_DIR,
                "pages",
                "3_By_Operator.py"
            ),
            title="By Operator"
        ),

        st.Page(
            os.path.join(
                BASE_DIR,
                "pages",
                "4_By_Owner.py"
            ),
            title="By Owner"
        )

    ]

}

pg = st.navigation(pages)

pg.run()
