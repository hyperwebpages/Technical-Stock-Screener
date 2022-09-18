import select
from dataclasses import fields
from os import stat
from time import time
from tracemalloc import start
from typing import List

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import plotting
from cached_functions import compute_score, load_stocks
from indicator import EMA, MACD, RSI, CipherB, Indicator, StochRSI
from market_data import download_klines
from stock import Stock, get_all_symbols_df

st.set_page_config(layout="wide")


if "current_index" not in st.session_state:
    st.session_state["current_index"] = 0
if "first_scan" not in st.session_state:
    st.session_state["first_scan"] = True
if "elapsed_time" not in st.session_state:
    st.session_state["elapsed_time"] = 0
if "stocks" not in st.session_state:
    st.session_state["stocks"] = load_stocks()


rsi = RSI()
stochrsi = StochRSI()
macd = MACD()
ema = EMA()
cipher_b = CipherB()

indicators = [rsi, stochrsi, ema, macd, cipher_b]

with st.sidebar:
    for ind in indicators:
        ind.checkbox()
        if ind.on:
            ind.text_input()
    on_indicators = [ind for ind in indicators if ind.on]

    scan_button = st.button("Scan")

if scan_button:
    start_time = time()
    st.session_state["stocks"] = compute_score(
        st.session_state["stocks"], on_indicators
    )
    st.session_state["stocks"].sort(
        key=lambda x: (x.global_score, x.symbol), reverse=True
    )
    st.session_state["elapsed_time"] = time() - start_time

    st.session_state["first_scan"] = False

if st.session_state["first_scan"]:
    st.header("Welcome !")
    st.write("On this page, you'll have the chance to monitor stocks.")
    st.write(
        "By defining indicators and threshold, you will be able to detect in real time if a stock meets your condition."
    )
else:
    stocks = st.session_state["stocks"]
    st.write(f"Studied stocks: {len(stocks)}")
    st.write("Elapsed time: {:.0f}ms".format(st.session_state["elapsed_time"] * 1000))
    st.write(
        f"Non neutral predictions: {len([1 for s in stocks if len(s.detailed_score)>0])}"
    )

    st.plotly_chart(plotting.indicator_histogram(stocks))

    indicators_to_draw_above = st.multiselect(
        "Indicators to draw above the ohlc chart",
        options=stocks[0].klines.columns,
        default=["Volume"],
    )
    indicators_to_draw_beside = st.multiselect(
        "Indicators to draw beside the ohlc chart",
        options=stocks[0].klines.columns,
        default=[
            ind.flag_column for ind in on_indicators if ind.flag_column is not None
        ],
    )

    agreed_indicators = st.slider(
        label="Filter on agreeing indicators",
        min_value=0,
        max_value=len(on_indicators),
        step=1,
        value=int(stocks[0].global_score),
    )
    selected_stocks = [
        stock for stock in stocks if np.abs(stock.global_score) == agreed_indicators
    ]

    length_displayed_stocks = 10

    def display_expanders(selected_stocks, length=length_displayed_stocks):
        for index in range(st.session_state["current_index"] + length):
            if index >= len(selected_stocks):
                break
            stock = selected_stocks[index]
            with st.expander(f"{stock.symbol} charts", expanded=False):
                fig = plotting.mutliple_row_charts(
                    stock, indicators_to_draw_above, indicators_to_draw_beside
                )
                st.plotly_chart(fig, use_container_width=True)

    display_expanders(selected_stocks, length=length_displayed_stocks)
    if st.session_state["current_index"] + length_displayed_stocks < len(
        selected_stocks
    ) and st.button("Load more"):
        st.session_state["current_index"] += length_displayed_stocks

    st.write(st.session_state["current_index"])
    st.write(
        st.session_state["current_index"], length_displayed_stocks, len(selected_stocks)
    )
