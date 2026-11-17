
import plotly.express as px


CHART_COLOR = "#00A99D"


def get_chart_height(number_of_rows):

    return max(
        450,
        min(number_of_rows * 35 + 100, 1600)
    )


def create_horizontal_chart(
    df,
    category_column,
    value_column,
    transaction_column,
    title,
    value_label,
    unit="currency",
):

    if df.empty:
        return None

    fig = px.bar(
        df,
        x=value_column,
        y=category_column,
        orientation="h",
        custom_data=[transaction_column],
        template="plotly_white",
        color_discrete_sequence=[CHART_COLOR],
        labels={
            category_column: title,
            value_column: value_label
        }
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
        )
    )

    fig.update_layout(
        height=get_chart_height(len(df)),
        margin=dict(
            t=30,
            b=40,
            l=20,
            r=50
        ),
        xaxis_title=value_label,
        yaxis_title=title,
        yaxis=dict(
            categoryorder="total ascending",
            automargin=True
        ),
        showlegend=False,
        bargap=0.25,
        font=dict(size=12)
    )

    return fig


def create_monthly_chart(
    df,
    value_column,
    title,
    unit="currency"
):

    if df.empty:
        return None

    fig = px.bar(
        df,
        x="month",
        y=value_column,
        template="plotly_white",
        color_discrete_sequence=[CHART_COLOR]
    )

    if unit == "currency":

        text_template = "$%{y:,.2f}"

        fig.update_yaxes(
            tickprefix="$",
            tickformat=",.2f"
        )

    else:

        text_template = "%{y:,.2f} kWh"

        fig.update_yaxes(
            ticksuffix=" kWh",
            tickformat=",.0f"
        )

    fig.update_traces(
        texttemplate=text_template,
        textposition="outside",
        cliponaxis=False
    )

    fig.update_layout(
        height=450,
        title=title,
        showlegend=False,
        xaxis_title="Month",
        margin=dict(
            t=40,
            b=30,
            l=20,
            r=20
        )
    )

    return fig
