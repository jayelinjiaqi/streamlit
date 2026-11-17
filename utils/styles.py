
import streamlit as st


def apply_styles():

    st.markdown(
        """
        <style>

        :root {
            --primary: #00A99D;
            --navy: #123047;
            --background: #F8FAFC;
            --border: #E5E7EB;
        }

        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2.5rem;
            max-width: 1600px;
        }

        h1, h2, h3 {
            color: var(--navy);
        }

        [data-testid="stMetric"] {
            background: white;
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 18px;
        }

        [data-testid="stMetricLabel"] {
            color: #64748B;
            font-weight: 500;
        }

        [data-testid="stMetricValue"] {
            color: var(--navy);
            font-weight: 700;
        }

        [data-baseweb="tag"] {
            background-color: var(--primary) !important;
        }

        [data-baseweb="select"] div:focus-within {
            border-color: var(--primary) !important;
            box-shadow: 0 0 0 1px var(--primary) !important;
        }

        [data-testid="stSidebar"] {
            border-right: 1px solid var(--border);
        }

        [data-testid="stSidebar"] h2 {
            color: var(--navy);
        }

        [data-testid="stDownloadButton"] button {
            border-radius: 8px;
        }

        div.stButton > button {
            border-radius: 8px;
        }

        hr {
            border-color: var(--border);
        }

        </style>
        """,
        unsafe_allow_html=True
    )
