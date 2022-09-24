from dataclasses import fields
from typing import List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from models.asset import Index, Stock
from plotly.graph_objects import Figure
from plotly.subplots import make_subplots


def indicator_histogram(indices: List[Index], stocks: List[Stock]) -> Figure:
    """Creates a figure containing a summary of the scanned stocks

    Args:
        stocks (List[Stock]): relevant stocks among the scanned stocks

    Returns:
        Figure: plotly figure
    """
    fig = make_subplots(rows=1, cols=2)

    l = []
    for index, (asset_type, assets) in enumerate(
        {"index": indices, "stock": stocks}.items()
    ):
        for asset in assets:
            for ind, score_ind in asset.detailed_score.items():
                l.append(
                    [asset.symbol, asset.global_score, asset_type, str(ind), score_ind]
                )
    df = pd.DataFrame(
        l, columns=["symbols", "score", "asset_type", "indicator", "indicator_score"]
    )

    _index = df[df["score"] < 0].index
    df.loc[_index, "indicator_score"] *= -1

    color_map = {
        indicator_name: px.colors.qualitative.Plotly[i]
        for i, indicator_name in enumerate(df["indicator"].unique())
    }
    for indicator_name in df["indicator"].unique():
        for index, (asset_type, assets) in enumerate(
            {"index": indices, "stock": stocks}.items()
        ):
            df_with_indicator_name_asset_type = df[
                (df["indicator"] == indicator_name) & (df["asset_type"] == asset_type)
            ]
            fig.add_trace(
                go.Histogram(
                    histfunc="sum",
                    y=df_with_indicator_name_asset_type["indicator_score"],
                    x=df_with_indicator_name_asset_type["score"],
                    legendgroup=indicator_name,
                    name=indicator_name,
                    hovertemplate=f"<b>{indicator_name}</b>:"
                    + "<br>%{y}"
                    + f" {asset_type} detected."
                    + "<extra></extra>",
                    xbins=dict(  # bins used for histogram
                        start=df["score"].min(), end=df["score"].max() + 1, size=1
                    ),
                    marker_color=color_map[indicator_name],
                    xaxis="x" + str(index + 1),
                    showlegend=index > 0,
                ),
                row=1,
                col=index + 1,
            )

            fig.update_xaxes(
                title_text=f"Number of {asset_type} detected",
                tickmode="array",
                tickvals=list(
                    np.arange(df["score"].min() + 0.5, df["score"].max() + 1.5, 1)
                ),
                ticktext=list(range(df["score"].min(), df["score"].max() + 1, 1)),
                range=[df["score"].min(), df["score"].max() + 1],
                row=1,
                col=index + 1,
            )
    fig.update_yaxes(title_text="Global score", row=1, col=1)

    fig.update_layout(
        title="Number of assets detected having a trend on specific indicators",
        legend_title="Indicators",
        hovermode="x unified",
        height=600,
        width=1000,
        margin_b=190,  # increase the bottom margin to have space for caption
        annotations=[
            dict(
                xref="paper",
                yref="paper",
                x=0.5,
                y=-0.35,
                showarrow=False,
                text="A negative global score means a sell pressure <br>given by the conditions, and vice versa. <br>"
                + "The higher the absolute value, the more powerful is the pressure.",
            )
        ],
    )
    return fig


def mutliple_row_charts(
    stock: Stock,
    indicators_to_draw_above: List[str] = [],
    indicators_to_draw_beside: List[str] = [],
) -> Figure:
    """Creates a figure containing multiple rows of charts:
        * a first OHLC chart, and the `indicators_to_draw_above` on top.
        * a chart of each indicator in `indicators_to_draw_beside`

    Args:
        stock (Stock): selected stock
        indicators_to_draw_above (List[str], optional): Indicators to draw below the OHLC chart. Defaults to [].
        indicators_to_draw_beside (List[str], optional): Indicators to draw on top of the OHLC chart. Defaults to [].

    Returns:
        Figure: plotly figure containing all the chart
    """
    row_heights = [0.7] + [0.2] * len(indicators_to_draw_beside)
    fig = make_subplots(
        rows=len(indicators_to_draw_beside) + 1,
        cols=1,
        shared_xaxes=True,
        row_heights=row_heights,
        specs=[[{"secondary_y": True}]] + [[{}]] * len(indicators_to_draw_beside),
        vertical_spacing=0.02,
    )

    for indicator_name in indicators_to_draw_above:
        if indicator_name == "Volume":
            trace = go.Bar(
                x=stock.klines.index,
                y=stock.klines["Volume"],
                marker={"color": "lightgrey",},
                name=indicator_name,
                opacity=0.7,
            )

        else:
            trace = go.Scatter(
                x=stock.klines.index,
                y=stock.klines[indicator_name],
                name=indicator_name,
            )
        fig.add_trace(
            trace, row=1, col=1, secondary_y=True,
        )

    fig.add_trace(
        go.Candlestick(
            x=stock.klines.index,
            open=stock.klines["Open"],
            high=stock.klines["High"],
            low=stock.klines["Low"],
            close=stock.klines["Close"],
            name="OHLC",
        ),
        row=1,
        col=1,
        secondary_y=False,
    )
    for index, indicator_name in enumerate(indicators_to_draw_beside):
        fig.add_trace(
            go.Scatter(
                x=stock.klines.index,
                y=stock.klines[indicator_name],
                name=indicator_name,
            ),
            row=index + 2,
            col=1,
        )
    fig.update_xaxes(
        rangebreaks=[
            dict(bounds=["sat", "mon"], pattern="day of week"),  # hide weekends
        ],
        title_text="Date",
        row=len(indicators_to_draw_beside) + 1,
        col=1,
    )

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=np.sum(row_heights) * 800,
        legend_title="Indicators",
        hovermode="x unified",
        title_text="OHLC chart and Indicators",
        font=dict(size=18),
    )
    return fig
