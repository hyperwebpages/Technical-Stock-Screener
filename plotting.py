from dataclasses import fields
from typing import List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from cached_functions import compute_score, load_stocks
from indicator import EMA, MACD, RSI, CipherB, Indicator, StochRSI
from market_data import download_klines
from stock import Stock, get_all_symbols_df


def indicator_histogram(stocks: List[Stock]):
    l = []
    for stock in stocks:
        for ind, score_ind in stock.detailed_score.items():
            l.append([stock.symbol, stock.global_score, str(ind), score_ind])
    df = pd.DataFrame(l, columns=["symbols", "score", "indicator", "indicator_score"])

    _index = df[df["score"] < 0].index
    df.loc[_index, "indicator_score"] *= -1

    fig = go.Figure()
    for indicator_name in df["indicator"].unique():
        fig.add_trace(
            go.Histogram(
                histfunc="sum",
                y=df[df["indicator"] == indicator_name]["indicator_score"],
                x=df[df["indicator"] == indicator_name]["score"],
                name=indicator_name,
                hovertemplate=f"<b>{indicator_name}</b>:"
                + "<br>%{y} stocks detected."
                + "<extra></extra>",
            )
        )
    fig.update_layout(
        title="Number of stocks detected having a trend on specific indicators",
        xaxis_title="Score",
        yaxis_title="Number of stocks detected",
        legend_title="Indicators",
        hovermode="x unified",
    )
    return fig


def mutliple_row_charts(stock, indicators_to_draw_above, indicators_to_draw_beside):
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
                marker={
                    "color": "lightgrey",
                },
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
            trace,
            row=1,
            col=1,
            secondary_y=True,
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
