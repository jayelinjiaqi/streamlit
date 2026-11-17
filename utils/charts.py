
import plotly.express as px

CHART_COLOR = "#00A99D"
NAVY = "#123047"


def get_chart_height(rows):

    return max(
        420,
        min(rows * 36 + 100, 1600)
    )


def create_ranking_chart(
    df,
    category,
    value,
    transaction_count,
    title,
    unit="currency",
    chart_key=None
):

    if df.empty:
        return None

    fig = px.bar(
        df,
        x=value,
        y=category,
        orientation="h",
        custom_data=[transaction_count],
        template="plotly_white",
        color_discrete_sequence=[CHART_COLOR]
    )

    if unit == "currency":

        hover_value = (
            "Payment: $%{x:,.2f}"
        )

        fig.update_xaxes(
            tickprefix="$",
            tickformat=",.0f"
        )

    else:

        hover_value = (
            "Energy: %{x:,.2f} kWh"
        )

        fig.update_xaxes(
            ticksuffix=" kWh",
            tickformat=",.0f"
        )

    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            + hover_value
            + "<br>"
            "Transactions: %{customdata[0]:,}"
            "<extra></extra>"
        ),
        marker_line_width=0
    )

    fig.update_layout(
        height=get_chart_height(len(df)),
        margin=dict(
            t=25,
            b=45,
            l=20,
            r=60
        ),
        xaxis_title=title,
        yaxis_title="",
        yaxis=dict(
            categoryorder="total ascending",
            automargin=True
        ),
        showlegend=False,
        bargap=0.3,
        font=dict(
            family="Arial",
            size=12,
            color=NAVY
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        clickmode="event+select",
        dragmode=False
    )

    return fig


def create_monthly_chart(
    df,
    value,
    title,
    unit="currency"
):

    if df.empty:
        return None

    fig = px.bar(
        df,
        x="month",
        y=value,
        text=value,
        template="plotly_white",
        color_discrete_sequence=[CHART_COLOR]
    )

    if unit == "currency":

        text_template = "$%{text:,.2f}"

        hover_value = (
            "Payment: $%{y:,.2f}"
        )

        fig.update_yaxes(
            tickprefix="$",
            tickformat=",.0f"
        )

    else:

        text_template = "%{text:,.2f} kWh"

        hover_value = (
            "Energy: %{y:,.2f} kWh"
        )

        fig.update_yaxes(
            ticksuffix=" kWh",
            tickformat=",.0f"
        )

    fig.update_traces(
        texttemplate=text_template,
        textposition="outside",
        cliponaxis=False,
        hovertemplate=(
            "Month: %{x}<br>"
            + hover_value
            + "<extra></extra>"
        )
    )

    fig.update_layout(
        height=440,
        title=title,
        margin=dict(
            t=45,
            b=35,
            l=20,
            r=20
        ),
        xaxis_title="Month",
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white"
    )

    return fig
