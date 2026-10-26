#import os
#import pandas as pd
#import psycopg
#import streamlit as st
#import plotly.express as px
#from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

st.set_page_config(
    page_title="EV Payments Dashboard",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------
# PROFESSIONAL DASHBOARD STYLING
# --------------------------------------------------

st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        padding: 18px;
        border-radius: 12px;
    }
    h1, h2, h3 {
        color: #123047;
    }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

@st.cache_data(ttl=300, show_spinner="Loading EV transactions...")
def load_ev_data():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is missing from .env")

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM ev")
            columns = [desc.name for desc in cur.description]
            rows = cur.fetchall()

    return pd.DataFrame(rows, columns=columns)


# --------------------------------------------------
# LOAD AND VALIDATE DATA
# --------------------------------------------------

st.title("EV Payments Dashboard")
st.caption("Transaction analytics | Neon PostgreSQL")

try:
    df = load_ev_data()
except Exception as exc:
    st.error(f"Unable to load data: {exc}")
    st.stop()

required = ["car_park_id", "payment_amount_100"]

missing = [col for col in required if col not in df.columns]

if missing:
    st.error(f"Missing required columns: {', '.join(missing)}")
    st.stop()

if df.empty:
    st.warning("The ev table contains no records.")
    st.stop()

df["payment_amount_100"] = pd.to_numeric(
    df["payment_amount_100"], errors="coerce")

df["payment_amount"] = df["payment_amount_100"]

# Prefer exit_dt_p8; fall back to other common date columns.
date_candidates = [
    "exit_dt_p8",
    "exit_date_time",
    "paid_dt_p8",
    "paid_datetime",
    "entry_dt_p8",
]

date_col = next(
    (col for col in date_candidates if col in df.columns),
    None,
)

if date_col:
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df["report_date"] = df[date_col]
    df["month"] = df["report_date"].dt.to_period("M").astype(str)
else:
    df["report_date"] = pd.NaT
    df["month"] = None

df["car_park_id"] = (
    df["car_park_id"].astype("string").fillna("Unknown")
)


# --------------------------------------------------
# SIDEBAR FILTERS
# --------------------------------------------------

st.sidebar.header("Dashboard Filters")

carparks = sorted(df["car_park_id"].unique().tolist())

selected_carparks = st.sidebar.multiselect(
    "Car Park ID",
    options=carparks,
    default=carparks,
    help="Select one or more car parks.",
)

if date_col and df["report_date"].notna().any():
    valid_dates = df["report_date"].dropna()

    min_date = valid_dates.min().date()
    max_date = valid_dates.max().date()

    date_range = st.sidebar.date_input(
        "Transaction date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
else:
    date_range = None

if st.sidebar.button("Refresh data"):
    load_ev_data.clear()
    st.rerun()


# --------------------------------------------------
# APPLY FILTERS
# --------------------------------------------------

filtered = df[df["car_park_id"].isin(selected_carparks)].copy()

if date_range and len(date_range) == 2:
    start_date, end_date = date_range

    filtered = filtered[
        filtered["report_date"].notna()
        & (filtered["report_date"].dt.date >= start_date)
        & (filtered["report_date"].dt.date <= end_date)
    ]


# --------------------------------------------------
# KPI CARDS
# --------------------------------------------------

total_payment = filtered["payment_amount"].sum()
transaction_count = len(filtered)
carpark_count = filtered["car_park_id"].nunique()

average_payment = (
    filtered["payment_amount"].mean()
    if transaction_count
    else 0
)

k1, k2, k3, k4 = st.columns(4)

k1.metric("Total Payments", f"${total_payment:,.2f}")
k2.metric("Transactions", f"{transaction_count:,}")
k3.metric("Car Parks", f"{carpark_count:,}")
k4.metric("Average Payment", f"${average_payment:,.2f}")

st.divider()


# --------------------------------------------------
# MONTHLY PAYMENT CHART
# --------------------------------------------------

st.subheader("Monthly Payment Trend")

if date_col is None:
    st.warning(
        "No supported date column was found. "
        "Add your actual transaction date column to date_candidates."
    )
elif filtered["report_date"].notna().sum() == 0:
    st.warning("No valid transaction dates are available.")
elif filtered.empty:
    st.info("No transactions match the selected filters.")
else:
    monthly = (
        filtered.dropna(subset=["report_date"])
        .groupby("month", as_index=False)
        .agg(
            payment_amount=("payment_amount", "sum"),
            transactions=("payment_amount", "size"),
        )
        .sort_values("month")
    )

    fig = px.bar(
        monthly,
        x="month",
        y="payment_amount",
        text="payment_amount",
        hover_data={"transactions": True},
        labels={
            "month": "Month",
            "payment_amount": "Payment Amount",
            "transactions": "Transactions",
        },
        template="plotly_white",
        color_discrete_sequence=["#00A99D"],
    )

    fig.update_traces(
        texttemplate="$%{text:,.2f}",
        textposition="outside",
        cliponaxis=False,
        hovertemplate=(
            "Month: %{x}<br>"
            "Payments: $%{y:,.2f}<br>"
            "<extra></extra>"
        ),
    )

    fig.update_layout(
        height=450,
        showlegend=False,
        margin=dict(t=30, b=30, l=20, r=20),
        xaxis_title="Month",
        yaxis_title="Total Payment",
        yaxis_tickprefix="$",
        yaxis_tickformat=",.2f",
    )

    st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------
# TRANSACTION DATA TABLE
# --------------------------------------------------

st.divider()
st.subheader("Transaction Details")

st.caption(
    f"Showing {len(filtered):,} records after applying filters."
)

# Display all original ev columns plus a readable payment amount.
display_df = filtered.drop(
    columns=["report_date", "month"],
    errors="ignore",
).copy()

display_df = display_df.rename(
    columns={"payment_amount": "payment_amount_currency"}
)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    height=450,
)

# CSV export
csv_data = display_df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download filtered transactions (CSV)",
    data=csv_data,
    file_name="ev_transactions.csv",
    mime="text/csv",
)

st.caption(
    f"Source: Neon PostgreSQL · Table: ev · "
    f"Date column: {date_col or 'Not detected'}"
)
