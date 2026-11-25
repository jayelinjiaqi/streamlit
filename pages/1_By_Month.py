import os
import pandas as pd
import psycopg
import streamlit as st
import plotly.express as px
from dotenv import load_dotenv
import os
from PIL import Image

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOGO_PATH = os.path.join(BASE_DIR, "assets", "favicon.png")

if os.path.exists(LOGO_PATH):
    st.logo(LOGO_PATH, size="large")

logo = Image.open(LOGO_PATH)

st.html(
    """
    <style>
    img[data-testid="stLogo"] {
        height: 9.5rem;
        max-height: none;   
    }
    </style>
    """
)

st.logo("assets/goparkin_logo.png", size="large")

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
    [data-testid="stSidebar"] label {
        color: #123047;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300, show_spinner="Loading EV transactions...")
def load_ev_data():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is missing from .env")
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT e.*, c.name as car_park_name, cpo.name as car_park_owner, op.name as car_park_operator
            FROM public.ev_paid_datetime e
            LEFT JOIN public.car_park c on e.car_park_id = c.id
            LEFT JOIN public.car_park_owner cpo on c.car_park_owner_id = cpo.id
            LEFT JOIN public.car_park_operator op on c.car_park_operator_id = op.id
            LIMIT 9000
            """)
            columns = [desc.name for desc in cur.description]
            rows = cur.fetchall()
    return pd.DataFrame(rows, columns=columns)

st.title("EV Billing Summary")

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

if "ci_connector_id" in df.columns:
    df["ci_connector_id"] = (
        df["ci_connector_id"]
        .astype(str)
        .str.strip()
        .replace({"": None, "nan": None, "None": None})
    )
    df["ci_connector_id"] = pd.to_numeric(
        df["ci_connector_id"],
        errors="coerce"
    ).astype("Int64")

date_candidates = ["paid_dt_p8"]
date_col = next((col for col in date_candidates if col in df.columns), None)
if date_col:
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df["report_date"] = df[date_col]
    df["month"] = df["report_date"].dt.to_period("M").astype(str)
else:
    df["report_date"] = pd.NaT
    df["month"] = None

df["car_park_id"] = (df["car_park_id"].astype("string").fillna("Unknown"))

st.sidebar.header("Dashboard Filters")

carparks = sorted(df["car_park_name"].astype(str).unique().tolist())
selected_carparks = st.sidebar.multiselect(
    "Car Park Name",
    options=carparks, default=carparks, help="Select one or more car parks.",)

df["car_park_owner"] = df["car_park_owner"].astype("string").fillna("Unknown")
owners = sorted(df["car_park_owner"].unique().tolist())
selected_owners = st.sidebar.multiselect(
    "Car Park Owner",
    options=owners, default=owners, help="Select one or more car park owners.",)

df["car_park_operator"] = df["car_park_operator"].astype("string").fillna("Unknown")
operators = sorted(df["car_park_operator"].unique().tolist())
selected_operators = st.sidebar.multiselect(
    "Car Park Operator",
    options=operators, default=operators, help="Select one or more car park operators.",)

if "ci_stake_id" in df.columns:
    df["ci_stake"] = df["ci_stake_id"].astype("string").fillna("Unknown")
    stakes = sorted(df["ci_stake"].unique().tolist())
    selected_stakes = st.sidebar.multiselect("Stake ID", options=stakes, default=stakes, help="Select one or more Stake IDs.")
else:
    selected_stakes = None
    st.sidebar.warning("Stake ID column ci_stake not found.")

if date_col and df["report_date"].notna().any():
    valid_dates = df["report_date"].dropna()
    min_date = valid_dates.min().date()
    max_date = valid_dates.max().date()

    date_range = st.sidebar.date_input("Transaction date range",
        value=(min_date, max_date), min_value=min_date, max_value=max_date,)
else:
    date_range = None

if st.sidebar.button("Refresh data", width="stretch"):
    load_ev_data.clear()
    st.rerun()

filtered = df[df["car_park_name"].isin(selected_carparks)
    & df["car_park_owner"].isin(selected_owners)
    & df["car_park_operator"].isin(selected_operators)].copy()

if selected_stakes is not None:
    filtered = filtered[filtered["ci_stake"].isin(selected_stakes)]

if date_range and len(date_range) == 2:
    start_date, end_date = date_range
    filtered = filtered[filtered["report_date"].notna()
        & (filtered["report_date"].dt.date >= start_date)
        & (filtered["report_date"].dt.date <= end_date)]

total_payment = filtered["payment_amount"].sum()
transaction_count = len(filtered)
carpark_count = filtered["car_park_id"].nunique()

average_payment = (filtered["payment_amount"].mean() if transaction_count else 0)

k1, k2, k4 = st.columns(3)

with k1:
    st.html(f"""
    <div
        onclick="window.parent.location.href =
        window.parent.location.origin +
        window.parent.location.pathname +
        '?page=payment_details'"
        style="
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 18px;
            min-height: 110px;
            cursor: pointer;
            transition: all 0.2s ease;
        "
        onmouseover="this.style.borderColor='#00A99D';
                     this.style.boxShadow='0 4px 12px rgba(0,169,157,0.15)'"
        onmouseout="this.style.borderColor='#e5e7eb';
                    this.style.boxShadow='none'"
    >
        <div style="color:#555;font-size:14px;">
            Total Payments
        </div>
        <div style="
            color:#123047;
            font-size:30px;
            font-weight:600;
            margin-top:8px;
        ">
            ${total_payment:,.2f}
        </div>
        <div style="
            color:#00A99D;
            font-size:12px;
            margin-top:8px;
        ">
            View payment details →
        </div>
    </div>
    """)

k2.metric("Transactions", f"{transaction_count:,}")
k4.metric("Average Payment", f"${average_payment:,.2f}")

st.divider()

st.subheader("Total Payment By Month")

if date_col is None:
    st.warning("No supported date column was found.")
elif filtered["report_date"].notna().sum() == 0:
    st.warning("No valid transaction dates are available.")
elif filtered.empty:
    st.info("No transactions match the selected filters.")
else:
    monthly = (filtered.dropna(subset=["report_date"])
        .groupby("month", as_index=False)
        .agg(payment_amount=("payment_amount", "sum"), transactions=("payment_amount", "size"))
        .sort_values("month")
    )
    fig = px.bar(monthly, x="month", y="payment_amount", text="payment_amount",
        custom_data=["transactions"],
        labels={"month": "Month", "payment_amount": "Payment Amount"},
        template="plotly_white",
        color_discrete_sequence=["#00A99D"]
    )

    fig.update_traces(
        texttemplate="$%{text:,.2f}",
        textposition="outside",
        cliponaxis=False,
        hovertemplate=(
            "Month: %{x}<br>"
            "Payments: $%{y:,.2f}<br>"
            "Transactions: %{customdata[0]}<br>"
            "<extra></extra>"
        )
    )

    fig.update_layout(height=450, showlegend=False, margin=dict(t=30, b=30, l=20, r=20),
        xaxis_title="Month",
        yaxis_title="Total Payment",
        yaxis_tickprefix="$",
        yaxis_tickformat=",.2f", clickmode="event+select"
    )

    event = st.plotly_chart(fig, width="stretch",
        on_select="rerun", selection_mode="points", key="monthly_payment_chart"
    )

    selected_points = event.selection.points
    
    if selected_points:
        selected_month = pd.to_datetime(selected_points[0]["x"]).strftime("%Y-%m")
        st.session_state["selected_payment_month"] = selected_month
    else:
        selected_month = st.session_state.get("selected_payment_month")
    
    if selected_month is not None:
        selected_data = filtered[filtered["month"].astype(str).str.strip() == str(selected_month).strip()].copy()
        st.divider()
        st.subheader(f"Payment Breakdown By Car Park - {selected_month}")

        if not selected_data.empty:
            carpark_breakdown = (selected_data
                .groupby("car_park_name", as_index=False)
                .agg(payment_amount=("payment_amount", "sum"), transactions=("payment_amount", "size"))
                .sort_values("payment_amount", ascending=False)
            )

            fig_detail = px.bar(carpark_breakdown, x="car_park_name", y="payment_amount",
                text="payment_amount", template="plotly_white", color_discrete_sequence=["#00A99D"])

            fig_detail.update_traces(texttemplate="$%{text:,.2f}",
                textposition="outside",
                cliponaxis=False,
                hovertemplate=(
                    "Car Park: %{x}<br>"
                    "Payment: $%{y:,.2f}<br>"
                    "<extra></extra>"
                )
            )

            fig_detail.update_layout(height=450, showlegend=False, margin=dict(t=30, b=30, l=20, r=20),
                xaxis_title="Car Park Name", yaxis_title="Total Payment", yaxis_tickprefix="$", yaxis_tickformat=",.2f")

            st.plotly_chart(fig_detail, width="stretch")
            st.dataframe(carpark_breakdown, width="stretch", hide_index=True)

        else:
            st.warning("No matching transactions found for this month.")

st.subheader("Energy Delivered By Month")

if date_col is None:
    st.warning("No supported date column was found.")
elif filtered["report_date"].notna().sum() == 0:
    st.warning("No valid transaction dates are available.")
elif filtered.empty:
    st.info("No transactions match the selected filters.")
else:
    monthly = (filtered.dropna(subset=["report_date"])
        .groupby("month", as_index=False)
        .agg(energy_delivered=("ci_power", "sum"), transactions=("ci_power", "size"),).sort_values("month"))

    fig = px.bar(monthly, x="month", y="energy_delivered", text="energy_delivered",
        hover_data={"transactions": True},
        labels={"month": "Month", "energy_delivered": "Energy Delivered", "transactions": "Transactions",},
        template="plotly_white",
        color_discrete_sequence=["#00A99D"],)

    fig.update_traces(texttemplate="%{text:,.0f} kWh",
        textposition="outside",
        cliponaxis=False,
        hovertemplate=("Month: %{x}<br>"
            "Energy Delivered: %{y:,.2f} kWh<br>"
            "<extra></extra>"),)

    fig.update_layout(height=450, showlegend=False, margin=dict(t=30, b=30, l=20, r=20),
        xaxis_title="Month", yaxis_title="Total Energy Delivered", yaxis_ticksuffix=" kWh", yaxis_tickformat=",.0f",)

    st.plotly_chart(fig, width="stretch")

st.subheader("Energy Delivered By Car Park, Stake ID & Month")

required_columns = [
    "car_park_name",
    "ci_stake",
    "ci_connector_id",
    "ci_power",
    "report_date"
]

missing_columns = [
    col for col in required_columns
    if col not in filtered.columns
]

if missing_columns:
    st.warning(f"Missing columns: {', '.join(missing_columns)}")
else:
    energy_data = filtered.dropna(subset=["report_date"]).copy()

    energy_data["car_park_name"] = (
        energy_data["car_park_name"]
        .fillna("Unknown")
        .astype("string")
    )

    energy_data["ci_stake"] = (
        energy_data["ci_stake"]
        .fillna("Unknown")
        .astype("string")
    )

    energy_data["ci_connector_id"] = pd.to_numeric(
        energy_data["ci_connector_id"],
        errors="coerce"
    ).astype("Int64")

    energy_data["ci_power"] = pd.to_numeric(
        energy_data["ci_power"],
        errors="coerce"
    )

    energy_data = energy_data.dropna(
        subset=["ci_connector_id", "ci_power"]
    )

    if energy_data.empty:
        st.info("No valid energy records are available.")
    else:
        monthly_stake_energy = energy_data.pivot_table(
            index=[
                "car_park_name",
                "ci_stake",
                "ci_connector_id"
            ],
            columns="month",
            values="ci_power",
            aggfunc="sum",
            fill_value=0,
            observed=True
        )

        month_columns = sorted(
            monthly_stake_energy.columns.tolist()
        )

        monthly_stake_energy = monthly_stake_energy[month_columns]

        monthly_stake_energy["Grand Total"] = (
            monthly_stake_energy[month_columns].sum(axis=1)
        )

        monthly_stake_energy = (
            monthly_stake_energy[
                monthly_stake_energy["Grand Total"] != 0
            ]
            .sort_values(
                "Grand Total",
                ascending=False
            )
        )

        if not monthly_stake_energy.empty:
            total_values = (
                monthly_stake_energy[
                    month_columns + ["Grand Total"]
                ].sum()
            )

            total_row = pd.DataFrame(
                [total_values],
                index=pd.MultiIndex.from_tuples(
                    [("Grand Total", " ", pd.NA)],
                    names=[
                        "car_park_name",
                        "ci_stake",
                        "ci_connector_id"
                    ]
                )
            )

            monthly_stake_energy = pd.concat(
                [
                    monthly_stake_energy,
                    total_row
                ]
            )

            monthly_stake_energy.columns.name = None
            monthly_stake_energy = monthly_stake_energy.reset_index()

            monthly_stake_energy = monthly_stake_energy.rename(
                columns={
                    "car_park_name": "Carpark Name",
                    "ci_stake": "Stake ID",
                    "ci_connector_id": "Connector ID"
                }
            )

            monthly_stake_energy["Carpark Name"] = (
                monthly_stake_energy["Carpark Name"]
                .astype("string")
            )

            monthly_stake_energy["Stake ID"] = (
                monthly_stake_energy["Stake ID"]
                .astype("string")
            )

            monthly_stake_energy["Connector ID"] = (
                pd.to_numeric(
                    monthly_stake_energy["Connector ID"],
                    errors="coerce"
                ).astype("Int64")
            )

            for col in month_columns + ["Grand Total"]:
                monthly_stake_energy[col] = pd.to_numeric(
                    monthly_stake_energy[col],
                    errors="coerce"
                ).fillna(0).astype("float64")

            st.dataframe(
                monthly_stake_energy.style.format(
                    {
                        col: "{:,.2f} kWh"
                        for col in month_columns + ["Grand Total"]
                    }
                ),
                width="stretch",
                hide_index=True
            )
        else:
            st.info("No energy records were found for the selected filters.")
