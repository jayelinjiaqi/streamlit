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

# --------------------------------------------------
# PAGE NAVIGATION
# --------------------------------------------------
#dashboard_page = st.Page("pages/1_EV_Billing_Summary.py", title="EV Billing Summary", default=True)
#monthly_details_page = st.Page("pages/2_Monthly_Payment_Details.py", title="Monthly Payment Details") # check if it's pages/2_...

#pg = st.navigation([dashboard_page, monthly_details_page])
#pg.run()

# --------------------------------------------------
# TOP LEFT BROWSER LOGO
# --------------------------------------------------
# Build safe paths relative to the project root directory
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOGO_PATH = os.path.join(BASE_DIR, "assets", "favicon.png")

# Render logo safely
if os.path.exists(LOGO_PATH):
    st.logo(LOGO_PATH, size="large")

logo = Image.open(LOGO_PATH)

#st.set_page_config(
#    page_title="EV Payments Dashboard",
#    page_icon=logo,
#    layout="wide",
#    initial_sidebar_state="expanded")


# 1. Force custom size using custom CSS
st.html(
    """
    <style>
    img[data-testid="stLogo"] {
        height: 9.5rem;
        max-height: none;   /* Override Streamlit built-in limits */
    }
    </style>
    """
)

# 2. Render logo
st.logo("assets/goparkin_logo.png",size="large")

# --------------------------------------------------
# STYLING
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

        /* Match filter selection color to chart */
    :root {
        --primary-color: #00A99D;
    }

    /* Selected items in multiselect */
    [data-baseweb="tag"] {
        background-color: #00A99D !important;
    }

    /* Selected filter controls */
    [data-baseweb="select"] div:focus-within {
        border-color: #00A99D !important;
        box-shadow: 0 0 0 1px #00A99D !important;
    }

    /* Date picker selected date */
    [data-testid="stDateInput"] button {
        color: #00A99D !important;
    }

    /* Sidebar filter labels */
    [data-testid="stSidebar"] label {
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
st.title("EV | Billing Summary")
# st.caption("Transaction analytics | Neon PostgreSQL")

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

# date_candidates = ["exit_dt_p8","exit_date_time","paid_dt_p8","paid_datetime","entry_dt_p8",] # Prefer exit_dt_p8; fall back to other common date columns.
date_candidates = ["paid_dt_p8"]
date_col = next((col for col in date_candidates if col in df.columns),None,)
if date_col:
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df["report_date"] = df[date_col]
    df["month"] = df["report_date"].dt.to_period("M").astype(str)
else:
    df["report_date"] = pd.NaT
    df["month"] = None

df["car_park_id"] = (df["car_park_id"].astype("string").fillna("Unknown"))



# --------------------------------------------------
# SIDEBAR FILTERS
# --------------------------------------------------
st.sidebar.header("Dashboard Filters")

# 1. Car Park Name Filter
carparks = sorted(df["car_park_name"].astype(str).unique().tolist())
selected_carparks = st.sidebar.multiselect(
    "Car Park Name",
    options=carparks,default=carparks,help="Select one or more car parks.",)

# 2. Car Park Owner Filter
df["car_park_owner"] = df["car_park_owner"].astype("string").fillna("Unknown")
owners = sorted(df["car_park_owner"].unique().tolist())
selected_owners = st.sidebar.multiselect(
    "Car Park Owner",
    options=owners,default=owners,help="Select one or more car park owners.",)

# 3. Car Park Operator Filter
df["car_park_operator"] = df["car_park_operator"].astype("string").fillna("Unknown")
operators = sorted(df["car_park_operator"].unique().tolist())
selected_operators = st.sidebar.multiselect(
    "Car Park Operator",
    options=operators,default=operators,help="Select one or more car park operators.",)

# 4. Stake ID Filter
if "ci_stake_id" in df.columns:
    df["ci_stake"] = df["ci_stake_id"].astype("string").fillna("Unknown")
    stakes = sorted(df["ci_stake"].unique().tolist())

    selected_stakes = st.sidebar.multiselect("Stake ID",options=stakes,default=stakes,help="Select one or more Stake IDs.")
else:
    selected_stakes = None
    st.sidebar.warning("Stake ID column ci_stake not found.")


if date_col and df["report_date"].notna().any():
    valid_dates = df["report_date"].dropna()
    min_date = valid_dates.min().date()
    max_date = valid_dates.max().date()

    date_range = st.sidebar.date_input("Transaction date range",
        value=(min_date, max_date),min_value=min_date,max_value=max_date,)
else:
    date_range = None

if st.sidebar.button("Refresh data"):
    load_ev_data.clear()
    st.rerun()


# --------------------------------------------------
# APPLY FILTERS
# --------------------------------------------------
filtered = df[
    df["car_park_name"].isin(selected_carparks)
    & df["car_park_owner"].isin(selected_owners)
    & df["car_park_operator"].isin(selected_operators)].copy()

# Apply Stake ID filter
if selected_stakes is not None:
    filtered = filtered[filtered["ci_stake"].isin(selected_stakes)]

# Apply date filter
if date_range and len(date_range) == 2:
    start_date, end_date = date_range

    filtered = filtered[
        filtered["report_date"].notna()
        & (filtered["report_date"].dt.date >= start_date)
        & (filtered["report_date"].dt.date <= end_date)]

# --------------------------------------------------
# KPI CARDS
# --------------------------------------------------
total_payment = filtered["payment_amount"].sum()
transaction_count = len(filtered)
carpark_count = filtered["car_park_id"].nunique()

average_payment = (filtered["payment_amount"].mean()
    if transaction_count
    else 0)

#k1, k2, k3, k4 = st.columns(4)
k1, k2, k4 = st.columns(3)

#k1.metric("Total Payments", f"${total_payment:,.2f}")
#k2.metric("Transactions", f"{transaction_count:,}") #k3.metric("Car Parks", f"{carpark_count:,}")
#k4.metric("Average Payment", f"${average_payment:,.2f}")
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






# --------------------------------------------------
# MONTHLY PAYMENT CHART
# --------------------------------------------------
st.subheader("Total Payment By Month")

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
        .agg(
            payment_amount=("payment_amount", "sum"),
            transactions=("payment_amount", "size")
        )
        .sort_values("month")
    )

    fig = px.bar(
        monthly,
        x="month",
        y="payment_amount",
        text="payment_amount",
        custom_data=["transactions"],
        labels={
            "month": "Month",
            "payment_amount": "Payment Amount"
        },
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

    fig.update_layout(
        height=450,
        showlegend=False,
        margin=dict(t=30, b=30, l=20, r=20),
        xaxis_title="Month",
        yaxis_title="Total Payment",
        yaxis_tickprefix="$",
        yaxis_tickformat=",.2f",
        clickmode="event+select"
    )

    event = st.plotly_chart(
        fig,
        use_container_width=True,
        on_select="rerun",
        selection_mode="points",
        key="monthly_payment_chart"
    )

    # ----------------------------------------------
    # GET SELECTED MONTH
    # ----------------------------------------------
    selected_points = event.selection.points
    
    if selected_points:
        #selected_month = str(selected_points[0]["x"])
        selected_month = pd.to_datetime(selected_points[0]["x"]).strftime("%Y-%m")
        st.session_state["selected_payment_month"] = selected_month
    else:
        selected_month = st.session_state.get("selected_payment_month")
    
    # ----------------------------------------------
    # DEBUG SECTION
    # ----------------------------------------------
    #st.write("DEBUG - Selected month:", repr(selected_month))
    #st.write("DEBUG - Available months:",filtered["month"].unique().tolist())
    #st.write("DEBUG - Sample transaction records:",filtered[["month", "payment_amount", "car_park_name"]].head(10))

    # ----------------------------------------------
    # DISPLAY MONTHLY CAR PARK BREAKDOWN
    # ----------------------------------------------
    if selected_month is not None:

        selected_data = filtered[filtered["month"].astype(str).str.strip() == str(selected_month).strip()].copy()

        st.divider()

        st.subheader(f"Payment Breakdown By Car Park - {selected_month}")

        if not selected_data.empty:

            carpark_breakdown = (
                selected_data
                .groupby("car_park_name", as_index=False)
                .agg(payment_amount=("payment_amount", "sum"),transactions=("payment_amount", "size"))
                .sort_values("payment_amount",ascending=False)
            )

            fig_detail = px.bar(carpark_breakdown,x="car_park_name",y="payment_amount",
                text="payment_amount",template="plotly_white",color_discrete_sequence=["#00A99D"])

            fig_detail.update_traces(
                texttemplate="$%{text:,.2f}",
                textposition="outside",
                cliponaxis=False,
                hovertemplate=(
                    "Car Park: %{x}<br>"
                    "Payment: $%{y:,.2f}<br>"
                    "<extra></extra>"
                )
            )

            fig_detail.update_layout(
                height=450,
                showlegend=False,
                margin=dict(t=30, b=30, l=20, r=20),
                xaxis_title="Car Park Name",
                yaxis_title="Total Payment",
                yaxis_tickprefix="$",
                yaxis_tickformat=",.2f"
            )

            st.plotly_chart(fig_detail,use_container_width=True)
            st.dataframe(carpark_breakdown,use_container_width=True,hide_index=True)

        else:
            st.warning("No matching transactions found for this month.")



# --------------------------------------------------
# MONTHLY PAYMENT BY CAR PARK NAME & MONTH
# --------------------------------------------------
st.subheader("Total Payment By Carpark & Month")

if date_col is None:
    st.warning("No supported date column was found.")
elif filtered["report_date"].notna().sum() == 0:
    st.warning("No valid transaction dates are available.")
elif filtered.empty:
    st.info("No transactions match the selected filters.")

else:
    monthly_carpark = (filtered.dropna(subset=["report_date"])
        .groupby(["month", "car_park_name"], as_index=False)
        .agg(payment_amount=("payment_amount", "sum"),transactions=("payment_amount", "size"))
        .sort_values(["month", "car_park_name"])
    )

    fig = px.bar(monthly_carpark,x="month",y="payment_amount",
        color="car_park_name",barmode="group",
        hover_data={"transactions": True},
        labels={"month": "Month","payment_amount": "Payment Amount","car_park_name": "Car Park Name","transactions": "Transactions"},
        template="plotly_white",
        color_discrete_sequence=px.colors.qualitative.Safe
    )

    fig.update_traces(hovertemplate=("Month: %{x}<br>"
            "Car Park: %{fullData.name}<br>"
            "Payments: $%{y:,.2f}<br>"
            "<extra></extra>"))

    fig.update_layout(height=500,margin=dict(t=30, b=30, l=20, r=20),
        xaxis_title="Month",yaxis_title="Total Payment",
        yaxis_tickprefix="$",yaxis_tickformat=",.2f",
        legend_title="Car Park Name",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="left",x=0))

    st.plotly_chart(fig, use_container_width=True)



# --------------------------------------------------
# MONTHLY PAYMENT BY CARPARK OWNER & MONTH
# --------------------------------------------------
st.subheader("Total Payment By Carpark Owner & Month")

if date_col is None:
    st.warning("No supported date column was found.")
elif filtered["report_date"].notna().sum() == 0:
    st.warning("No valid transaction dates are available.")
elif filtered.empty:
    st.info("No transactions match the selected filters.")

else:
    monthly_owner = (
        filtered.dropna(subset=["report_date"])
        .groupby(["month", "car_park_owner"], as_index=False)
        .agg(payment_amount=("payment_amount", "sum"),transactions=("payment_amount", "size"))
        .sort_values(["month", "car_park_owner"])
    )

    fig = px.bar(monthly_owner,x="month",y="payment_amount",
        color="car_park_owner",barmode="group",
        hover_data={"transactions": True},
        labels={"month": "Month","payment_amount": "Payment Amount","car_park_owner": "Car Park Owner","transactions": "Transactions"},
        template="plotly_white",
        color_discrete_sequence=px.colors.qualitative.Safe
    )

    fig.update_traces(
        hovertemplate=("Month: %{x}<br>"
            "Owner: %{fullData.name}<br>"
            "Payments: $%{y:,.2f}<br>"
            "<extra></extra>"
        ))

    fig.update_layout(height=500,margin=dict(t=30, b=30, l=20, r=20),
        xaxis_title="Month",yaxis_title="Total Payment",
        yaxis_tickprefix="$",yaxis_tickformat=",.2f",
        legend_title="Car Park Owner",legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="left",x=0))

    st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------
# MONTHLY PAYMENT BY CARPARK OPERATOR & MONTH
# --------------------------------------------------
st.subheader("Total Payment By Carpark Operator & Month")

if date_col is None:
    st.warning("No supported date column was found.")
elif filtered["report_date"].notna().sum() == 0:
    st.warning("No valid transaction dates are available.")
elif filtered.empty:
    st.info("No transactions match the selected filters.")

else:
    monthly_operator = (
        filtered.dropna(subset=["report_date"])
        .groupby(["month", "car_park_operator"], as_index=False)
        .agg(payment_amount=("payment_amount", "sum"),transactions=("payment_amount", "size"))
        .sort_values(["month", "car_park_operator"])
    )

    fig = px.bar(monthly_operator,x="month",y="payment_amount",
        color="car_park_operator",barmode="group",
        hover_data={"transactions": True},
        labels={"month": "Month","payment_amount": "Payment Amount","car_park_operator": "Car Park Operator",
            "transactions": "Transactions"},
        template="plotly_white",
        color_discrete_sequence=px.colors.qualitative.Safe
    )

    fig.update_traces(hovertemplate=("Month: %{x}<br>"
            "Operator: %{fullData.name}<br>"
            "Payments: $%{y:,.2f}<br>"
            "<extra></extra>"
        ))

    fig.update_layout(height=500,margin=dict(t=30, b=30, l=20, r=20),
        xaxis_title="Month",yaxis_title="Total Payment",yaxis_tickprefix="$",yaxis_tickformat=",.2f",
        legend_title="Carpark Operator",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="left",x=0))

    st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------
# ENERGY BY MONTH 
# --------------------------------------------------
st.subheader("Energy Delivered By Month")

if date_col is None:
    st.warning("No supported date column was found. "
        "Add your actual transaction date column to date_candidates.")
elif filtered["report_date"].notna().sum() == 0:
    st.warning("No valid transaction dates are available.")
elif filtered.empty:
    st.info("No transactions match the selected filters.")
else:
    monthly = (filtered.dropna(subset=["report_date"])
        .groupby("month", as_index=False)
        .agg(energy_delivered=("ci_power", "sum"),
            transactions=("ci_power", "size"),).sort_values("month"))
        #size counts all rows, including empty rows.
        #count counts only non-null ci_power values.

    fig = px.bar(monthly,x="month",y="energy_delivered",text="energy_delivered",
        hover_data={"transactions": True},
        labels={"month": "Month","energy_delivered": "Energy Delivered","transactions": "Transactions",},
        template="plotly_white",
        color_discrete_sequence=["#00A99D"],)

    fig.update_traces(texttemplate="%{text:,.0f} kWh",
        textposition="outside",
        cliponaxis=False,
        hovertemplate=("Month: %{x}<br>"
            "Energy Delivered: %{y:,.2f} kWh<br>"
            "<extra></extra>"),)

    fig.update_layout(height=450,showlegend=False,margin=dict(t=30, b=30, l=20, r=20),
        xaxis_title="Month",yaxis_title="Total Energy Delivered",yaxis_ticksuffix=" kWh",yaxis_tickformat=",.0f",)

    st.plotly_chart(fig, use_container_width=True)



# --------------------------------------------------
# ENERGY BY CARPARK & MONTH
# --------------------------------------------------
st.subheader("Energy Delivered By Carpark & Month")

if date_col is None:
    st.warning("No supported date column was found.")
elif filtered["report_date"].notna().sum() == 0:
    st.warning("No valid transaction dates are available.")
elif filtered.empty:
    st.info("No transactions match the selected filters.")
else:
    monthly_carpark_energy = (filtered.dropna(subset=["report_date"])
        .groupby(["month", "car_park_name"], as_index=False)
        .agg(energy_delivered=("ci_power", "sum"),transactions=("ci_power", "count"))
        .sort_values(["month", "car_park_name"])
    )

    fig = px.bar(monthly_carpark_energy,x="month",y="energy_delivered",
        color="car_park_name",barmode="group",
        hover_data={"transactions": True},
        labels={"month": "Month","energy_delivered": "Energy Delivered","car_park_name": "Car Park Name","transactions": "Transactions"},
        template="plotly_white",
        color_discrete_sequence=px.colors.qualitative.Safe
    )

    fig.update_traces(hovertemplate=("Month: %{x}<br>"
            "Car Park: %{fullData.name}<br>"
            "Energy Delivered: %{y:,.0f} kWh<br>"
            "Transactions: %{customdata[0]}<br>"
            "<extra></extra>"
        ),
        customdata=monthly_carpark_energy[["transactions"]].values
    )

    fig.update_layout(height=500,margin=dict(t=30, b=30, l=20, r=20),
        xaxis_title="Month",yaxis_title="Total Energy Delivered",
        yaxis_ticksuffix=" kWh",yaxis_tickformat=",.0f",legend_title="Car Park Name",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="left",x=0))

    st.plotly_chart(fig, use_container_width=True)



# --------------------------------------------------
# ENERGY BY CARPARK OWNER & MONTH
# --------------------------------------------------
st.subheader("Energy Delivered By Carpark Owner & Month")

if date_col is None:
    st.warning("No supported date column was found.")
elif filtered["report_date"].notna().sum() == 0:
    st.warning("No valid transaction dates are available.")
elif filtered.empty:
    st.info("No transactions match the selected filters.")
else:
    monthly_owner_energy = (filtered.dropna(subset=["report_date"])
        .groupby(["month", "car_park_owner"], as_index=False)
        .agg(energy_delivered=("ci_power", "sum"),transactions=("ci_power", "count"))
        .sort_values(["month", "car_park_owner"])
    )

    fig = px.bar(monthly_owner_energy,x="month",y="energy_delivered",
        color="car_park_owner",barmode="group",
        labels={"month": "Month","energy_delivered": "Energy Delivered",
            "car_park_owner": "Car Park Owner","transactions": "Transactions"},
        template="plotly_white",
        color_discrete_sequence=px.colors.qualitative.Safe
    )

    fig.update_traces(hovertemplate=("Month: %{x}<br>"
            "Owner: %{fullData.name}<br>"
            "Energy Delivered: %{y:,.0f} kWh<br>"
            "Transactions: %{customdata[0]}<br>"
            "<extra></extra>"
        ),
        customdata=monthly_owner_energy[["transactions"]].values,
        texttemplate="%{y:,.0f} kWh"
    )

    fig.update_layout(height=500,margin=dict(t=30, b=30, l=20, r=20),
        xaxis_title="Month",yaxis_title="Total Energy Delivered",
        yaxis_ticksuffix=" kWh",yaxis_tickformat=",.0f",legend_title="Carpark Owner",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="left",x=0
        ))

    st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------
# PIVOT TABLE - ENERGY BY CARPARK NAME & STAKE ID & MONTH
# --------------------------------------------------
st.subheader("Energy Delivered By Car Park, Stake ID & Month")

if "ci_stake" not in filtered.columns:
    st.warning("ci_stake column was not found.")
elif date_col is None:
    st.warning("No supported date column was found.")
elif filtered.empty or filtered["report_date"].notna().sum() == 0:
    st.info("No valid transactions match the selected filters.")
else:
    energy_data = filtered.dropna(subset=["report_date","ci_stake","ci_connector_id"]).copy()

    energy_data["car_park_name"] = (energy_data["car_park_name"].fillna("Unknown"))

    energy_data["ci_connector_id"] = (pd.to_numeric(energy_data["ci_connector_id"], errors="coerce").fillna(0).astype(int))

    energy_data["ci_power"] = pd.to_numeric(energy_data["ci_power"], errors="coerce")
    energy_data = energy_data.dropna(subset=["ci_power"])

    # Create pivot table
    monthly_stake_energy = energy_data.pivot_table(index=["car_park_name", "ci_stake", "ci_connector_id"],
        columns="month",values="ci_power",aggfunc="sum",fill_value=0,observed=True)

    # Sort month columns chronologically
    month_columns = sorted(monthly_stake_energy.columns)
    monthly_stake_energy = monthly_stake_energy[month_columns]

    # Add Grand Total column
    monthly_stake_energy["Grand Total"] = (monthly_stake_energy.sum(axis=1))

    # Remove zero-energy rows
    monthly_stake_energy = monthly_stake_energy[monthly_stake_energy["Grand Total"] != 0]

    # Sort by Grand Total descending
    monthly_stake_energy = monthly_stake_energy.sort_values(by="Grand Total",ascending=False)

    # Calculate overall Grand Total
    total_row = pd.DataFrame([monthly_stake_energy.sum(axis=0)],
        index=pd.MultiIndex.from_tuples(
            [("Grand Total", "", "")],  #3 empty string to match 3 index levels
            names=["car_park_name", "ci_stake", "ci_connector_id"]))

    # Append one Grand Total row
    monthly_stake_energy = pd.concat([monthly_stake_energy, total_row])

    # Remove column heading
    monthly_stake_energy.columns.name = None

    # Reset index to display clean columns
    monthly_stake_energy = monthly_stake_energy.reset_index()

    # RENAME COLUMNS
    monthly_stake_energy = monthly_stake_energy.rename(columns={
        "car_park_name": "Carpark Name","ci_stake": "Stake ID","ci_connector_id": "Connector ID"})

    # Display table
    st.dataframe(monthly_stake_energy.style.format({col: "{:,.0f} kWh" for col in month_columns + ["Grand Total"]}),
        use_container_width=True,hide_index=True)

# --------------------------------------------------
# TRANSACTION DATA TABLE
# --------------------------------------------------
#st.divider()
#st.subheader("Transaction Details")
#st.caption(f"Showing {len(filtered):,} records after applying filters.")

# Display all original ev columns plus a readable payment amount.
#display_df = filtered.drop(columns=["report_date", "month"],errors="ignore",).copy()
#display_df = display_df.rename(columns={"payment_amount": "payment_amount_currency"})
#st.dataframe(display_df,use_container_width=True,hide_index=True,height=450,)

# CSV export
#csv_data = display_df.to_csv(index=False).encode("utf-8")
#st.download_button(label="Download filtered transactions (CSV)",data=csv_data,file_name="ev_transactions.csv",mime="text/csv",)

#st.caption(f"Source: ev · "
#    f"Date column: {date_col or 'Not detected'}")
