from pathlib import Path
from time import time

import numpy as np
import streamlit as st

import plotting
from indicator import EMA, MACD, RSI, CipherB, StochRSI
from stock import compute_score, load_stocks

st.set_page_config(layout="wide")


if "current_index" not in st.session_state:
    st.session_state["current_index"] = 0
if "first_scan" not in st.session_state:
    st.session_state["first_scan"] = True
if "elapsed_time" not in st.session_state:
    st.session_state["elapsed_time"] = 0
if "stocks" not in st.session_state:
    st.session_state["stocks"] = load_stocks()

stocks = st.session_state["stocks"]

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
    stocks = compute_score(stocks, on_indicators)
    stocks.sort(key=lambda stock: (np.abs(stock.global_score), stock.symbol))
    st.session_state["elapsed_time"] = time() - start_time
    st.session_state["first_scan"] = False

if st.session_state["first_scan"]:
    with open(Path("templates/welcome.txt"), "r") as welcome_file:
        welcome_str = welcome_file.read()
        st.markdown(welcome_str)
else:
    with open(Path("templates/global_analysis.txt"), "r") as global_analysis_file:
        global_analysis_str = global_analysis_file.read()
        st.markdown(
            global_analysis_str.format(
                len_stocks=len(stocks),
                elapsed_time=1000 * st.session_state["elapsed_time"],
                non_neutral_pressures=len(
                    [1 for s in stocks if len(s.detailed_score) > 0]
                ),
            )
        )

    st.write(type(plotting.indicator_histogram(stocks)))
    st.plotly_chart(plotting.indicator_histogram(stocks))

    with open(Path("templates/specific_analysis.txt"), "r") as global_analysis_file:
        global_analysis_str = global_analysis_file.read()
        st.markdown(
            global_analysis_str.format(
                len_stocks=len(stocks),
                elapsed_time=1000 * st.session_state["elapsed_time"],
                non_neutral_pressures=len(
                    [1 for s in stocks if len(s.detailed_score) > 0]
                ),
            )
        )

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
        value=int(np.abs(stocks[-1].global_score)),
    )
    selected_stocks = [
        stock for stock in stocks if np.abs(stock.global_score) == agreed_indicators
    ]

    length_displayed_stocks = 10

    def display_expanders(selected_stocks, length=length_displayed_stocks):
        for index in range(
            st.session_state["current_index"],
            st.session_state["current_index"] + length,
        ):
            if index >= len(selected_stocks):
                break
            stock = selected_stocks[index]
            with st.expander(f"{stock.symbol} charts", expanded=False):
                fig = plotting.mutliple_row_charts(
                    stock, indicators_to_draw_above, indicators_to_draw_beside
                )
                st.plotly_chart(fig, use_container_width=True)

            with st.expander(f"{stock.symbol} raw data", expanded=False):
                st.table(stock.klines)

    display_expanders(selected_stocks, length=length_displayed_stocks)
    if st.session_state["current_index"] + length_displayed_stocks < len(
        selected_stocks
    ) and st.button("Load more"):
        st.session_state["current_index"] += length_displayed_stocks
