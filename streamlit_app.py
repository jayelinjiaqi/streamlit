import os
import pandas as pd
import psycopg
import streamlit as st
import plotly.express as px
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
st.set_page_config(
    page_title="EV Payments Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------
# DASHBOARD STYLING & MODERN UI
# --------------------------------------------------
st.markdown("""
<style>
    /* Main Background and Container Spacing */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        padding-left: 3rem;
        padding-right: 3rem;
    }
    
    /* Global Font & Headers */
    h1, h2, h3 {
        color: #0F172A;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        font-weight: 700;
        letter-spacing: -0.5px;
    }

    /* Modern Metric Cards */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px -1px rgba(0, 0, 0, 0.01);
        transition: all 0.2s ease-in-out;
    }
    [data-testid="stMetric"]:hover {
        border-color: #00A99D;
        box-shadow: 0 10px 15px -3px rgba(0, 169, 157, 0.05);
        transform: translateY(-2px);
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700;
        color: #0F172A;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #F8FAFC;
        border-right: 1px solid #E2E8F0;
    }
    [data-testid="stSidebar"] label {
        color: #1E293B;
        font-weight: 600;
    }

    /* Primary Accent Customization */
    :root {
        --primary-color: #00A99D;
    }
    [data-baseweb="tag"] {
        background-color: #00A99D !important;
    }
    [data-baseweb="select"] div:focus-within {
        border-color: #00A99D !important;
        box-shadow: 0 0 0 1px #00A99D !important;
    }
    [data-testid="stDateInput"] button {
        color: #00A99D !important;
    }

    /* Divider Styling */
    hr {
        margin: 2.5rem 0;
        border-color: #E2E8F0;
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
            cur.execute("""
            SELECT e.*, c.name as car_park_name, cpo.name as car_park_owner, op.name as car_park_operator
            FROM ev_paid_datetime e
            LEFT JOIN car_park c on e.car_park_id = c.id
            LEFT JOIN car_park_owner cpo on c.car_park_owner_id = cpo.id
            LEFT JOIN car_park_operator op on c.car_park_operator_id = op.id
            LIMIT 500""")
            columns = [desc.name for desc in cur.description]
            rows = cur.fetchall()
    return pd.DataFrame(rows, columns=columns)


# --------------------------------------------------
# LOAD AND VALIDATE DATA
# --------------------------------------------------
st.title("⚡ GoParkin | EV Analytics Dashboard")
st.caption("Real-time transaction & energy consumption insights from Neon PostgreSQL")

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

df["payment_amount_100"] = pd.to_numeric(df["payment_amount_100"], errors="coerce")
df["payment_amount"] = df["payment_amount_100"]
df["ci_power"] = pd.to_numeric(df["ci_power"], errors="coerce")

date_candidates = ["paid_dt_p8"]
date_col = next((col for col in date_candidates if col in df.columns), None)

if date_col:
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df["report_date"] = df[date_col]
    df["month"] = df["report_date"].dt.to_period("M").astype(str)
else:
    df["report_date"] = pd.NaT
    df["month"] = None

df["car_park_id"] = df["car_park_id"].astype("string").fillna("Unknown")


# --------------------------------------------------
# SIDEBAR FILTERS
# --------------------------------------------------
st.sidebar.header("🎯 Dashboard Filters")
st.sidebar.markdown("Filter analytics views dynamically.")

carparks = sorted(df["car_park_name"].astype(str).unique().tolist())
selected_carparks = st.sidebar.multiselect(
    "Car Park Name", options=carparks, default=carparks, help="Select one or more car parks."
)

df["car_park_owner"] = df["car_park_owner"].astype("string").fillna("Unknown")
owners = sorted(df["car_park_owner"].unique().tolist())
selected_owners = st.sidebar.multiselect(
    "Car Park Owner", options=owners, default=owners, help="Select one or more car park owners."
)

df["car_park_operator"] = df["car_park_operator"].astype("string").fillna("Unknown")
operators = sorted(df["car_park_operator"].unique().tolist())
selected_operators = st.sidebar.multiselect(
    "Car Park Operator", options=operators, default=operators, help="Select one or more car park operators."
)

if "ci_stake_id" in df.columns:
    df["ci_stake"] = df["ci_stake_id"].astype("string").fillna("Unknown")
    stakes = sorted(df["ci_stake"].unique().tolist())
    selected_stakes = st.sidebar.multiselect(
        "Stake ID", options=stakes, default=stakes, help="Select one or more Stake IDs."
    )
else:
    selected_stakes = None
    st.sidebar.warning("Stake ID column not found.")

if date_col and df["report_date"].notna().any():
    valid_dates = df["report_date"].dropna()
    min_date = valid_dates.min().date()
    max_date = valid_dates.max().date()
    date_range = st.sidebar.date_input(
        "Transaction Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date
    )
else:
    date_range = None

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
    load_ev_data.clear()
    st.rerun()


# --------------------------------------------------
# APPLY FILTERS
# --------------------------------------------------
filtered = df[
    df["car_park_name"].isin(selected_carparks)
    & df["car_park_owner"].isin(selected_owners)
    & df["car_park_operator"].isin(selected_operators)
].copy()

if selected_stakes is not None:
    filtered = filtered[filtered["ci_stake"].isin(selected_stakes)]

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
average_payment = filtered["payment_amount"].mean() if transaction_count else 0

k1, k2, k4 = st.columns(3)
k1.metric("Total Payments", f"${total_payment:,.2f}")
k2.metric("Total Transactions", f"{transaction_count:,}")
k4.metric("Average Payment", f"${average_payment:,.2f}")

st.divider()


# --------------------------------------------------
# MONTHLY PAYMENT CHART
# --------------------------------------------------
st.subheader("📊 Total Payment By Month")

if date_col is None:
    st.warning("No supported date column was found.")
elif filtered["report_date"].notna().sum() == 0:
    st.warning("No valid transaction dates are available.")
elif filtered.empty:
    st.info("No transactions match the selected filters.")
else:
    monthly = (
        filtered.dropna(subset=["report_date"])
        .groupby("month", as_index=False)
        .agg(payment_amount=("payment_amount", "sum"), transactions=("payment_amount", "size"))
        .sort_values("month")
    )

    fig = px.bar(
        monthly, x="month", y="payment_amount", text="payment_amount",
        hover_data={"transactions": True},
        labels={"month": "Month", "payment_amount": "Payment Amount", "transactions": "Transactions"},
        template="plotly_white",
        color_discrete_sequence=["#00A99D"],
    )

    fig.update_traces(
        texttemplate="$%{text:,.2f}", textposition="outside", cliponaxis=False,
        hovertemplate="Month: %{x}<br>Payments: $%{y:,.2f}<br><extra></extra>",
    )
    fig.update_layout(
        height=420, showlegend=False, margin=dict(t=40, b=30, l=20, r=20),
        xaxis_title="Month", yaxis_title="Total Payment", yaxis_tickprefix="$", yaxis_tickformat=",.0f",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------
# MONTHLY PAYMENT BY CAR PARK NAME & MONTH
# --------------------------------------------------
st.subheader("🏢 Total Payment By Carpark & Month")

if not filtered.empty and date_col is not None:
    monthly_carpark = (
        filtered.dropna(subset=["report_date"])
        .groupby(["month", "car_park_name"], as_index=False)
        .agg(payment_amount=("payment_amount", "sum"), transactions=("payment_amount", "size"))
        .sort_values(["month", "car_park_name"])
    )

    fig = px.bar(
        monthly_carpark, x="month", y="payment_amount", color="car_park_name", barmode="group",
        hover_data={"transactions": True},
        labels={"month": "Month", "payment_amount": "Payment Amount", "car_park_name": "Car Park Name", "transactions": "Transactions"},
        template="plotly_white", color_discrete_sequence=px.colors.qualitative.Safe
    )
    fig.update_traces(hovertemplate="Month: %{x}<br>Car Park: %{fullData.name}<br>Payments: $%{y:,.2f}<br><extra></extra>")
    fig.update_layout(
        height=480, margin=dict(t=40, b=30, l=20, r=20),
        xaxis_title="Month", yaxis_title="Total Payment", yaxis_tickprefix="$", yaxis_tickformat=",.2f",
        legend_title="Car Park Name", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------
# MONTHLY PAYMENT BY CARPARK OWNER & MONTH
# --------------------------------------------------
st.subheader("💼 Total Payment By Carpark Owner & Month")

if not filtered.empty and date_col is not None:
    monthly_owner = (
        filtered.dropna(subset=["report_date"])
        .groupby(["month", "car_park_owner"], as_index=False)
        .agg(payment_amount=("payment_amount", "sum"), transactions=("payment_amount", "size"))
        .sort_values(["month", "car_park_owner"])
    )

    fig = px.bar(
        monthly_owner, x="month", y="payment_amount", color="car_park_owner", barmode="group",
        hover_data={"transactions": True},
        labels={"month": "Month", "payment_amount": "Payment Amount", "car_park_owner": "Car Park Owner", "transactions": "Transactions"},
        template="plotly_white", color_discrete_sequence=px.colors.qualitative.Safe
    )
    fig.update_traces(hovertemplate="Month: %{x}<br>Owner: %{fullData.name}<br>Payments: $%{y:,.2f}<br><extra></extra>")
    fig.update_layout(
        height=480, margin=dict(t=40, b=30, l=20, r=20),
        xaxis_title="Month", yaxis_title="Total Payment", yaxis_tickprefix="$", yaxis_tickformat=",.2f",
        legend_title="Car Park Owner", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------
# MONTHLY PAYMENT BY CARPARK OPERATOR & MONTH
# --------------------------------------------------
st.subheader("⚙️ Total Payment By Carpark Operator & Month")

if not filtered.empty and date_col is not None:
    monthly_operator = (
        filtered.dropna(subset=["report_date"])
        .groupby(["month", "car_park_operator"], as_index=False)
        .agg(payment_amount=("payment_amount", "sum"), transactions=("payment_amount", "size"))
        .sort_values(["month", "car_park_operator"])
    )

    fig = px.bar(
        monthly_operator, x="month", y="payment_amount", color="car_park_operator", barmode="group",
        hover_data={"transactions": True},
        labels={"month": "Month", "payment_amount": "Payment Amount", "car_park_operator": "Car Park Operator", "transactions": "Transactions"},
        template="plotly_white", color_discrete_sequence=px.colors.qualitative.Safe
    )
    fig.update_traces(hovertemplate="Month: %{x}<br>Operator: %{fullData.name}<br>Payments: $%{y:,.2f}<br><extra></extra>")
    fig.update_layout(
        height=480, margin=dict(t=40, b=30, l=20, r=20),
        xaxis_title="Month", yaxis_title="Total Payment", yaxis_tickprefix="$", yaxis_tickformat=",.2f",
        legend_title="Carpark Operator", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------
# ENERGY BY MONTH 
# --------------------------------------------------
st.subheader("⚡ Energy Delivered By Month")

if not filtered.empty and date_col is not None:
    monthly_energy = (
        filtered.dropna(subset=["report_date"])
        .groupby("month", as_index=False)
        .agg(energy_delivered=("ci_power", "sum"), transactions=("ci_power", "size"))
        .sort_values("month")
    )

    fig = px.bar(
        monthly_energy, x="month", y="energy_delivered", text="energy_delivered",
        hover_data={"transactions": True},
        labels={"month": "Month", "energy_delivered": "Energy Delivered", "transactions": "Transactions"},
        template="plotly_white", color_discrete_sequence=["#00A99D"],
    )
    fig.update_traces(
        texttemplate="%{text:,.0f} kWh", textposition="outside", cliponaxis=False,
        hovertemplate="Month: %{x}<br>Energy Delivered: %{y:,.2f} kWh<br><extra></extra>",
    )
    fig.update_layout(
        height=420, showlegend=False, margin=dict(t=40, b=30, l=20, r=20),
        xaxis_title="Month", yaxis_title="Total Energy Delivered", yaxis_ticksuffix=" kWh", yaxis_tickformat=",.0f",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------
# PIVOT TABLE - ENERGY BY CARPARK NAME & STAKE ID & MONTH
# --------------------------------------------------
st.divider()
st.subheader("📋 Energy Delivered By Car Park, Stake ID & Month")

if "ci_stake" not in filtered.columns:
    st.warning("ci_stake column was not found.")
elif date_col is None:
    st.warning("No supported date column was found.")
elif filtered.empty or filtered["report_date"].notna().sum() == 0:
    st.info("No valid transactions match the selected filters.")
else:
    energy_data = filtered.dropna(subset=["report_date", "ci_stake", "ci_connector_id"]).copy()
    energy_data["car_park_name"] = energy_data["car_park_name"].fillna("Unknown")
    energy_data["ci_connector_id"] = (
        pd.to_numeric(energy_data["ci_connector_id"], errors="coerce").fillna(0).astype(int)
    )
    energy_data["ci_power"] = pd.to_numeric(energy_data["ci_power"], errors="coerce")
    energy_data = energy_data.dropna(subset=["ci_power"])

    monthly_stake_energy = energy_data.pivot_table(
        index=["car_park_name", "ci_stake", "ci_connector_id"],
        columns="month", values="ci_power", aggfunc="sum", fill_value=0, observed=True
    )

    month_columns = sorted(monthly_stake_energy.columns)
    monthly_stake_energy = monthly_stake_energy[month_columns]
    monthly_stake_energy["Grand Total"] = monthly_stake_energy.sum(axis=1)
    monthly_stake_energy = monthly_stake_energy[monthly_stake_energy["Grand Total"] != 0]
    monthly_stake_energy = monthly_stake_energy.sort_values(by="Grand Total", ascending=False)

    total_row = pd.DataFrame(
        [monthly_stake_energy.sum(axis=0)],
        index=pd.MultiIndex.from_tuples([("Grand Total", "", "")], names=["car_park_name", "ci_stake", "ci_connector_id"])
    )
    monthly_stake_energy = pd.concat([monthly_stake_energy, total_row])
    monthly_stake_energy.columns.name = None
    monthly_stake_energy = monthly_stake_energy.reset_index()

    monthly_stake_energy = monthly_stake_energy.rename(columns={
        "car_park_name": "Carpark Name", "ci_stake": "Stake ID", "ci_connector_id": "Connector ID"
    })

    # Styled Table Look
    styled_table = (
        monthly_stake_energy.style
        .format({col: "{:,.0f} kWh" for col in month_columns + ["Grand Total"]})
        .set_properties(**{
            'background-color': '#FFFFFF',
            'color': '#0F172A',
            'border-color': '#E2E8F0',
            'font-family': 'sans-serif'
        })
    )

    st.dataframe(styled_table, use_container_width=True, hide_index=True, height=450)


# --------------------------------------------------
# TRANSACTION DATA TABLE
# --------------------------------------------------
st.divider()
st.subheader("📑 Transaction Details")
st.caption(f"Showing {len(filtered):,} records after applying filters.")

display_df = filtered.drop(columns=["report_date", "month"], errors="ignore").copy()
display_df = display_df.rename(columns={"payment_amount": "payment_amount_currency"})

st.dataframe(display_df, use_container_width=True, hide_index=True, height=450)

csv_data = display_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="📥 Download Filtered Transactions (CSV)", data=csv_data, file_name="ev_transactions.csv", mime="text/csv"
)

st.caption(f"Source: ev · Date column: {date_col or 'Not detected'}")
