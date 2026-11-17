
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

PAYMENT_DIVISOR = float(get_secret("PAYMENT_DIVISOR", 1))

DATE_COLUMN_CANDIDATES = ["paid_dt_p8"]


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
            "DATABASE_URL is missing from Streamlit Secrets."
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
        connect_timeout=15,
        application_name="goparkin_dashboard"
    ) as conn:

        df = pd.read_sql_query(query, conn)

    return df


# ==================================================
# PREPARE EV DATA
# ==================================================

@st.cache_data(ttl=CACHE_TTL)
def prepare_ev_data():

    df = load_ev_data().copy()

    required_columns = [
        "car_park_id",
        "payment_amount_100"
    ]

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required database columns: {', '.join(missing)}"
        )

    if df.empty:
        return df, None

    # ----------------------------------------------
    # PAYMENT
    # ----------------------------------------------

    df["payment_amount_100"] = pd.to_numeric(
        df["payment_amount_100"],
        errors="coerce"
    )

    df["payment_amount"] = (
        df["payment_amount_100"] / PAYMENT_DIVISOR
    )

    # ----------------------------------------------
    # ENERGY
    # ----------------------------------------------

    if "ci_power" in df.columns:
        df["ci_power"] = pd.to_numeric(
            df["ci_power"],
            errors="coerce"
        )
    else:
        df["ci_power"] = 0.0

    # ----------------------------------------------
    # DATE
    # ----------------------------------------------

    date_col = next(
        (
            col for col in DATE_COLUMN_CANDIDATES
            if col in df.columns
        ),
        None
    )

    if date_col:

        df[date_col] = pd.to_datetime(
            df[date_col],
            errors="coerce"
        )

        df["report_date"] = df[date_col]

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

    # ----------------------------------------------
    # DIMENSION COLUMNS
    # ----------------------------------------------

    dimension_columns = [
        "car_park_id",
        "car_park_name",
        "car_park_owner",
        "car_park_operator"
    ]

    for col in dimension_columns:

        if col not in df.columns:
            df[col] = "Unknown"

        df[col] = (
            df[col]
            .astype("string")
            .fillna("Unknown")
        )

    # ----------------------------------------------
    # STAKE ID
    # ----------------------------------------------

    if "ci_stake_id" in df.columns:

        df["ci_stake"] = (
            df["ci_stake_id"]
            .astype("string")
            .fillna("Unknown")
        )

    return df, date_col


# ==================================================
# SHARED SIDEBAR FILTERS
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
            "The EV transaction table contains no records."
        )

        st.stop()

    st.sidebar.header("Dashboard Filters")

    # ----------------------------------------------
    # CAR PARK FILTER
    # ----------------------------------------------

    carparks = sorted(
        df["car_park_name"].unique().tolist()
    )

    selected_carparks = st.sidebar.multiselect(
        "Car Park Name",
        options=carparks,
        default=carparks,
        key="filter_carparks"
    )

    # ----------------------------------------------
    # OWNER FILTER
    # ----------------------------------------------

    owners = sorted(
        df["car_park_owner"].unique().tolist()
    )

    selected_owners = st.sidebar.multiselect(
        "Car Park Owner",
        options=owners,
        default=owners,
        key="filter_owners"
    )

    # ----------------------------------------------
    # OPERATOR FILTER
    # ----------------------------------------------

    operators = sorted(
        df["car_park_operator"].unique().tolist()
    )

    selected_operators = st.sidebar.multiselect(
        "Car Park Operator",
        options=operators,
        default=operators,
        key="filter_operators"
    )

    # ----------------------------------------------
    # STAKE ID FILTER
    # ----------------------------------------------

    if "ci_stake" in df.columns:

        stakes = sorted(
            df["ci_stake"].unique().tolist()
        )

        selected_stakes = st.sidebar.multiselect(
            "Stake ID",
            options=stakes,
            default=stakes,
            key="filter_stakes"
        )

    else:

        selected_stakes = None

    # ----------------------------------------------
    # DATE FILTER
    # ----------------------------------------------

    date_range = None

    if (
        date_col is not None
        and df["report_date"].notna().any()
    ):

        valid_dates = df["report_date"].dropna()

        min_date = valid_dates.min().date()
        max_date = valid_dates.max().date()

        date_range = st.sidebar.date_input(
            "Transaction Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="filter_date_range"
        )

    # ----------------------------------------------
    # REFRESH DATA
    # ----------------------------------------------

    if st.sidebar.button(
        "Refresh Data",
        use_container_width=True
    ):

        load_ev_data.clear()
        prepare_ev_data.clear()

        st.rerun()

    # ----------------------------------------------
    # APPLY FILTERS
    # ----------------------------------------------

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

        if start_date and end_date:

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
