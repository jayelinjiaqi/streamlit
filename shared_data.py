
import os
import pandas as pd
import psycopg
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# --------------------------------------------------
# DATABASE
# --------------------------------------------------
@st.cache_data(ttl=300, show_spinner="Loading EV transactions...")
def load_ev_data():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is missing from .env")
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT e.*,c.name AS car_park_name,cpo.name AS car_park_owner,op.name AS car_park_operator
                FROM ev_paid_datetime e
                LEFT JOIN car_park c ON e.car_park_id = c.id
                LEFT JOIN car_park_owner cpo ON c.car_park_owner_id = c.id
                LEFT JOIN car_park_operator op ON c.car_park_operator_id = op.id
            """)
            columns = [desc.name for desc in cur.description]
            rows = cur.fetchall()
    return pd.DataFrame(rows, columns=columns)


# --------------------------------------------------
# LOAD AND PREPARE DATA
# --------------------------------------------------
@st.cache_data(ttl=300)
def prepare_ev_data():
    df = load_ev_data()
    required = ["car_park_id", "payment_amount_100"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    if df.empty:
        return df, None
    df["payment_amount_100"] = pd.to_numeric(df["payment_amount_100"], errors="coerce")
    df["payment_amount"] = df["payment_amount_100"]
    df["ci_power"] = pd.to_numeric(df["ci_power"], errors="coerce")

    date_candidates = ["paid_dt_p8"]

    date_col = next(
        (col for col in date_candidates if col in df.columns),
        None
    )

    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df["report_date"] = df[date_col]
        df["month"] = (df["report_date"].dt.to_period("M").astype(str))
    else:
        df["report_date"] = pd.NaT
        df["month"] = None

    df["car_park_id"] = (df["car_park_id"].astype("string").fillna("Unknown"))
    df["car_park_name"] = (df["car_park_name"].astype("string").fillna("Unknown"))
    df["car_park_owner"] = (df["car_park_owner"].astype("string").fillna("Unknown"))
    df["car_park_operator"] = (df["car_park_operator"].astype("string").fillna("Unknown"))
    return df, date_col


# --------------------------------------------------
# SHARED SIDEBAR FILTERS
# --------------------------------------------------
def get_filtered_data():
    try:
        df, date_col = prepare_ev_data()
    except Exception as exc:
        st.error(f"Unable to load data: {exc}")
        st.stop()
    if df.empty:
        st.warning("The ev table contains no records.")
        st.stop()
    st.sidebar.header("Dashboard Filters")

    # Car Park Name
    carparks = sorted(df["car_park_name"].unique().tolist())

    selected_carparks = st.sidebar.multiselect(
        "Car Park Name",
        options=carparks,
        default=carparks,
        key="filter_carparks"
    )

    # Car Park Owner
    owners = sorted(df["car_park_owner"].unique().tolist())

    selected_owners = st.sidebar.multiselect(
        "Car Park Owner",
        options=owners,
        default=owners,
        key="filter_owners"
    )

    # Car Park Operator
    operators = sorted(
        df["car_park_operator"].unique().tolist()
    )

    selected_operators = st.sidebar.multiselect(
        "Car Park Operator",
        options=operators,
        default=operators,
        key="filter_operators"
    )

    # Stake ID
    if "ci_stake_id" in df.columns:

        df["ci_stake"] = (
            df["ci_stake_id"].astype("string").fillna("Unknown")
        )

        stakes = sorted(df["ci_stake"].unique().tolist())

        selected_stakes = st.sidebar.multiselect(
            "Stake ID",
            options=stakes,
            default=stakes,
            key="filter_stakes"
        )

    else:
        selected_stakes = None

    # Date range
    if date_col and df["report_date"].notna().any():

        valid_dates = df["report_date"].dropna()

        min_date = valid_dates.min().date()
        max_date = valid_dates.max().date()

        date_range = st.sidebar.date_input(
            "Transaction date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="filter_date_range"
        )

    else:
        date_range = None

    # Refresh
    if st.sidebar.button("Refresh data"):

        load_ev_data.clear()
        prepare_ev_data.clear()

        st.rerun()

    # Apply filters
    filtered = df[
        df["car_park_name"].isin(selected_carparks)
        & df["car_park_owner"].isin(selected_owners)
        & df["car_park_operator"].isin(selected_operators)
    ].copy()

    if selected_stakes is not None:

        filtered = filtered[
            filtered["ci_stake"].isin(selected_stakes)
        ]

    if date_range and len(date_range) == 2:

        start_date, end_date = date_range

        filtered = filtered[
            filtered["report_date"].notna()
            & (filtered["report_date"].dt.date >= start_date)
            & (filtered["report_date"].dt.date <= end_date)
        ]

    return filtered, date_col
