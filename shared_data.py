
import os

import pandas as pd
import psycopg
import streamlit as st

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))

CURRENCY_SYMBOL = os.getenv("CURRENCY_SYMBOL", "$")

PAYMENT_DIVISOR = float(
    os.getenv("PAYMENT_DIVISOR", "1")
)

REQUIRED_COLUMNS = [
    "car_park_id",
    "payment_amount_100",
]

DIMENSION_COLUMNS = [
    "car_park_name",
    "car_park_owner",
    "car_park_operator",
]


# ==================================================
# DATABASE LOADER
# ==================================================

@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner="Loading EV transactions..."
)
def load_ev_data():

    if not DATABASE_URL:
        raise ValueError(
            "DATABASE_URL is missing."
        )

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

    with psycopg.connect(
        DATABASE_URL,
        connect_timeout=10
    ) as conn:

        with conn.cursor() as cur:

            cur.execute(query)

            columns = [
                item.name
                for item in cur.description
            ]

            rows = cur.fetchall()

    return pd.DataFrame(
        rows,
        columns=columns
    )


# ==================================================
# PREPARE DATA
# ==================================================

@st.cache_data(ttl=CACHE_TTL)
def prepare_ev_data():

    df = load_ev_data().copy()

    if df.empty:
        return df, None

    missing = [
        col for col in REQUIRED_COLUMNS
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing database columns: {missing}"
        )

    # --------------------------------------------------
    # PAYMENT
    # --------------------------------------------------

    df["payment_amount_100"] = pd.to_numeric(
        df["payment_amount_100"],
        errors="coerce"
    )

    df["payment_amount"] = (
        df["payment_amount_100"] / PAYMENT_DIVISOR
    )

    # --------------------------------------------------
    # ENERGY
    # --------------------------------------------------

    if "ci_power" in df.columns:

        df["ci_power"] = pd.to_numeric(
            df["ci_power"],
            errors="coerce"
        )

    else:

        df["ci_power"] = float("nan")

    # --------------------------------------------------
    # DATE
    # --------------------------------------------------

    date_candidates = [
        "paid_dt_p8"
    ]

    date_col = next(
        (
            col for col in date_candidates
            if col in df.columns
        ),
        None
    )

    if date_col:

        df["report_date"] = pd.to_datetime(
            df[date_col],
            errors="coerce"
        )

        # Ensure consistent date handling.
        if isinstance(
            df["report_date"].dtype,
            pd.DatetimeTZDtype
        ):
            df["report_date"] = (
                df["report_date"].dt.tz_localize(None)
            )

        df["month"] = (
            df["report_date"]
            .dt.to_period("M")
            .astype("string")
        )

    else:

        df["report_date"] = pd.NaT

        df["month"] = pd.Series(
            pd.NA,
            index=df.index,
            dtype="string"
        )

    # --------------------------------------------------
    # DIMENSIONS
    # --------------------------------------------------

    for col in DIMENSION_COLUMNS:

        if col not in df.columns:
            df[col] = "Unknown"

        df[col] = (
            df[col]
            .astype("string")
            .fillna("Unknown")
        )

    df["car_park_id"] = (
        df["car_park_id"]
        .astype("string")
        .fillna("Unknown")
    )

    # --------------------------------------------------
    # STAKE ID
    # --------------------------------------------------

    if "ci_stake_id" in df.columns:

        df["ci_stake"] = (
            df["ci_stake_id"]
            .astype("string")
            .fillna("Unknown")
        )

    return df, date_col


# ==================================================
# CACHE REFRESH
# ==================================================

def refresh_data():

    load_ev_data.clear()
    prepare_ev_data.clear()

    st.cache_data.clear()

    st.session_state.pop(
        "selected_payment_month",
        None
    )

    st.session_state.pop(
        "selected_carpark",
        None
    )

    st.session_state.pop(
        "selected_payment_operator",
        None
    )

    st.session_state.pop(
        "selected_payment_owner",
        None
    )

    st.rerun()


# ==================================================
# FILTER CONTROL
# ==================================================

def sidebar_multiselect(
    label,
    options,
    key
):

    options = sorted(
        str(value) for value in options
    )

    previous = st.session_state.get(key)

    if previous is None:

        default = options

    else:

        default = [
            value
            for value in previous
            if value in options
        ]

    return st.sidebar.multiselect(
        label,
        options=options,
        default=default,
        key=key
    )


# ==================================================
# GLOBAL FILTERS
# ==================================================

def get_filtered_data():

    try:

        df, date_col = prepare_ev_data()

    except Exception as exc:

        st.error(
            f"Unable to load EV data: {exc}"
        )

        st.stop()

    if df.empty:

        st.warning(
            "No EV transactions were found."
        )

        st.stop()

    st.sidebar.header("Dashboard Filters")

    # --------------------------------------------------
    # CAR PARK
    # --------------------------------------------------

    selected_carparks = sidebar_multiselect(
        "Car Park",
        df["car_park_name"].unique(),
        "filter_carparks"
    )

    # --------------------------------------------------
    # OWNER
    # --------------------------------------------------

    selected_owners = sidebar_multiselect(
        "Car Park Owner",
        df["car_park_owner"].unique(),
        "filter_owners"
    )

    # --------------------------------------------------
    # OPERATOR
    # --------------------------------------------------

    selected_operators = sidebar_multiselect(
        "Car Park Operator",
        df["car_park_operator"].unique(),
        "filter_operators"
    )

    # --------------------------------------------------
    # STAKE
    # --------------------------------------------------

    selected_stakes = None

    if "ci_stake" in df.columns:

        selected_stakes = sidebar_multiselect(
            "Stake ID",
            df["ci_stake"].unique(),
            "filter_stakes"
        )

    # --------------------------------------------------
    # DATE RANGE
    # --------------------------------------------------

    date_range = None

    if (
        date_col is not None
        and df["report_date"].notna().any()
    ):

        valid_dates = df["report_date"].dropna()

        min_date = valid_dates.min().date()
        max_date = valid_dates.max().date()

        default_range = (
            min_date,
            max_date
        )

        current_range = st.session_state.get(
            "filter_date_range"
        )

        if (
            not isinstance(current_range, (tuple, list))
            or len(current_range) != 2
            or current_range[0] < min_date
            or current_range[1] > max_date
        ):

            current_range = default_range

        date_range = st.sidebar.date_input(
            "Transaction Date Range",
            value=current_range,
            min_value=min_date,
            max_value=max_date,
            key="filter_date_range"
        )

    # --------------------------------------------------
    # REFRESH
    # --------------------------------------------------

    if st.sidebar.button(
        "Refresh Data",
        use_container_width=True
    ):

        refresh_data()

    # --------------------------------------------------
    # APPLY FILTERS
    # --------------------------------------------------

    filtered = df[
        df["car_park_name"].isin(selected_carparks)
        & df["car_park_owner"].isin(selected_owners)
        & df["car_park_operator"].isin(selected_operators)
    ].copy()

    if selected_stakes is not None:

        filtered = filtered[
            filtered["ci_stake"].isin(selected_stakes)
        ]

    if (
        isinstance(date_range, (tuple, list))
        and len(date_range) == 2
    ):

        start_date, end_date = date_range

        filtered = filtered[
            filtered["report_date"].notna()
            & (
                filtered["report_date"].dt.date
                >= start_date
            )
            & (
                filtered["report_date"].dt.date
                <= end_date
            )
        ]

    return filtered, date_col
