
import os
import pandas as pd
import psycopg
import streamlit as st


# ==================================================
# CLOUD CONFIGURATION
# ==================================================

def get_secret(name, default=None):

    try:
        return st.secrets.get(name, default)
    except Exception:
        return os.getenv(name, default)


DATABASE_URL = get_secret("DATABASE_URL")

CACHE_TTL = int(get_secret("CACHE_TTL", 300))

CURRENCY_SYMBOL = get_secret("CURRENCY_SYMBOL", "$")

PAYMENT_DIVISOR = float(
    get_secret("PAYMENT_DIVISOR", 1)
)


# ==================================================
# DATABASE CONNECTION
# ==================================================

@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner="Loading EV transactions..."
)
def load_ev_data():

    if not DATABASE_URL:
        raise ValueError(
            "DATABASE_URL is missing from Streamlit Secrets."
        )

    with psycopg.connect(
        DATABASE_URL,
        connect_timeout=15,
        application_name="goparkin_dashboard"
    ) as conn:

        query = """
            SELECT
                e.*,
                c.name AS car_park_name,
                cpo.name AS car_park_owner,
                op.name AS car_park_operator

            FROM public.ev_paid_datetime e

            LEFT JOIN public.car_park c
                ON e.car_park_id = c.id

            LEFT JOIN public.car_park_owner cpo
                ON c.car_park_owner_id = cpo.id

            LEFT JOIN public.car_park_operator op
                ON c.car_park_operator_id = op.id
        """

        df = pd.read_sql_query(
            query,
            conn
        )

    return df
