import os
import pandas as pd
import streamlit as st
import plotly.express as px
from PIL import Image
from shared_data import get_filtered_data

# ==================================================
# PAGE CONFIGURATION & LOGO
# ==================================================
st.set_page_config(
    page_title="EV Payments Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOGO_PATH = os.path.join(BASE_DIR, "assets", "favicon.png")

if os.path.exists(LOGO_PATH):
    st.logo(LOGO_PATH, size="large")

# Force custom logo size using custom CSS
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

if os.path.exists("assets/goparkin_logo.png"):
    st.logo("assets/goparkin_logo.png", size="large")

# ==================================================
# STYLING
# ==================================================
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

# ==================================================
# FETCH STANDARDIZED DATA & GLOBAL FILTERS
# ==================================================
# This single line calls shared_data.py, renders the sidebar filters,
# and returns the filtered dataframe + date column automatically!
filtered, date_col = get_filtered_data()

st.title("EV Billing Summary")

# ==================================================
# KPI CARDS
# ==================================================
total_payment = filtered["payment_amount"].sum() if not filtered.empty else 0
transaction_count = len(filtered)
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

# ==================================================
# MONTHLY PAYMENT CHART
# ==================================================
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

    event = st.plotly_chart(fig, use_container_width=True,
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

            st.plotly_chart(fig_detail, use_container_width=True)
            st.dataframe(carpark_breakdown, use_container_width=True, hide_index=True)
        else:
            st.warning("No matching transactions found for this month.")

# ==================================================
# ENERGY BY MONTH 
# ==================================================
st.subheader("Energy Delivered By Month")

if date_col is None:
    st.warning("No supported date column was found.")
elif filtered["report_date"].notna().sum() == 0:
    st.warning("No valid transaction dates are available.")
elif filtered.empty:
    st.info("No transactions match the selected filters.")
else:
    monthly_energy = (filtered.dropna(subset=["report_date"])
        .groupby("month", as_index=False)
        .agg(energy_delivered=("ci_power", "sum"), transactions=("ci_power", "size"))
        .sort_values("month")
    )

    fig_energy = px.bar(monthly_energy, x="month", y="energy_delivered", text="energy_delivered",
        hover_data={"transactions": True},
        labels={"month": "Month", "energy_delivered": "Energy Delivered", "transactions": "Transactions"},
        template="plotly_white",
        color_discrete_sequence=["#00A99D"]
    )

    fig_energy.update_traces(texttemplate="%{text:,.0f} kWh",
        textposition="outside",
        cliponaxis=False,
        hovertemplate=("Month: %{x}<br>"
            "Energy Delivered: %{y:,.2f} kWh<br>"
            "<extra></extra>")
    )

    fig_energy.update_layout(height=450, showlegend=False, margin=dict(t=30, b=30, l=20, r=20),
        xaxis_title="Month", yaxis_title="Total Energy Delivered", yaxis_ticksuffix=" kWh", yaxis_tickformat=",.0f")

    st.plotly_chart(fig_energy, use_container_width=True)

# ==================================================
# PIVOT TABLE - ENERGY BY CARPARK NAME & STAKE ID & MONTH
# ==================================================
st.subheader("Energy Delivered By Car Park, Stake ID & Month")

if "ci_stake" not in filtered.columns and "ci_stake_id" in filtered.columns:
    filtered["ci_stake"] = filtered["ci_stake_id"].astype("string").fillna("Unknown")

if "ci_stake" not in filtered.columns:
    st.warning("ci_stake column was not found.")
elif date_col is None:
    st.warning("No supported date column was found.")
elif filtered.empty or filtered["report_date"].notna().sum() == 0:
    st.info("No valid transactions match the selected filters.")
else:
    energy_data = filtered.dropna(subset=["report_date", "ci_stake", "ci_connector_id"]).copy()
    energy_data["car_park_name"] = energy_data["car_park_name"].fillna("Unknown")
    
    # Safely convert connector ID to avoid PyArrow type mismatch crashes
    energy_data["ci_connector_id"] = (
        pd.to_numeric(energy_data["ci_connector_id"], errors="coerce")
        .fillna(0)
        .astype(int)
        .astype(str)
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

    total_row = pd.DataFrame([monthly_stake_energy.sum(axis=0)],
        index=pd.MultiIndex.from_tuples(
            [("Grand Total", "", "")],
            names=["car_park_name", "ci_stake", "ci_connector_id"]
        )
    )

    monthly_stake_energy = pd.concat([monthly_stake_energy, total_row])
    monthly_stake_energy.columns.name = None
    monthly_stake_energy = monthly_stake_energy.reset_index()

    monthly_stake_energy = monthly_stake_energy.rename(columns={
        "car_park_name": "Carpark Name", "ci_stake": "Stake ID", "ci_connector_id": "Connector ID"
    })

    st.dataframe(
        monthly_stake_energy.style.format({col: "{:,.0f} kWh" for col in month_columns + ["Grand Total"]}),
        use_container_width=True, hide_index=True
    )
