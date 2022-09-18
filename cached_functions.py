from typing import List

import numpy as np
import streamlit as st

from indicator import Indicator
from stock import Stock, get_all_symbols_df


@st.experimental_memo()
def load_stocks():
    symbols_df = get_all_symbols_df()
    stocks = []

    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(" ")

    with col2:
        st.write("Downloading and loading stocks candlesticks...")

    with col3:
        st.write(" ")

    progress_bar = st.progress(0)
    for index, symbol in enumerate(symbols_df["symbol"]):
        stock = Stock(symbol)

        if len(stock.klines) == 0:
            st.warning(f"{stock.symbol} cannot be found.", icon="⚠️")
            continue

        progress_bar.progress(index / len(symbols_df))
        stocks.append(stock)
    progress_bar.empty()
    return stocks


@st.experimental_memo()
def compute_score(stocks: List[Stock], indicators: List[Indicator]):
    progress_bar = st.progress(0)
    for index, stock in enumerate(stocks):
        for indicator in indicators:
            stock.add_indicator(indicator)
        progress_bar.progress(index / len(stocks))
    progress_bar.empty()

    return stocks
