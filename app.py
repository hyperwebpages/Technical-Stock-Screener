from dataclasses import fields

import numpy as np
import pandas as pd
import streamlit as st

from indicator import EMA, MACD, RSI, CipherB, StochRSI
from market_data import download_klines
from stock import Stock, get_all_symbols_df

st.set_page_config(layout="wide")


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
    scan = st.button("Scan")


symbols_df = get_all_symbols_df()
stocks = []
for symbol in symbols_df["symbol"]:
    stock = Stock(symbol)
    for ind in indicators:
        if ind == macd:
            stock.klines = ind.add_indicator_to_dataframe(stock.klines, ema)
        else:
            stock.klines = ind.add_indicator_to_dataframe(stock.klines)
        if not ind.flag_column is None and stock.klines[ind.flag_column].iloc[-1] != 0:
            print("houra on stock", stock.symbol)
            print(stock.klines[ind.flag_column].index[-1])

    stocks.append(stock)
