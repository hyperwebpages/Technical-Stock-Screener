from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import streamlit as st

from indicator import Indicator
from market_data import download_klines


def get_all_symbols_df(path_to_symbols: Path = Path("datasets/symbols.csv")):
    return pd.read_csv(path_to_symbols)


@dataclass
class Stock:
    symbol: str
    start_date: datetime = datetime(2021, 1, 1)
    end_date: datetime = datetime.today()
    global_score: float = 0
    detailed_score: Dict[str, int] = field(default_factory=lambda: ({}))
    interval: str = "1d"

    def __post_init__(self):
        try:
            self.klines = download_klines(
                self.symbol,
                self.start_date,
                self.end_date,
                "1d",
                Path("datasets/daily"),
            )
        except ValueError as e:
            self.klines = []

    def add_indicator(self, indicator: Indicator):
        self.klines = indicator.apply_indicator(self.klines)

        if indicator.flag_column is not None:
            if np.abs(self.klines[indicator.flag_column].iloc[-1]) > 0:
                self.detailed_score[str(indicator)] = self.klines[
                    indicator.flag_column
                ].iloc[-1]
            self.global_score += self.klines[indicator.flag_column].iloc[-1]


@st.experimental_memo()
def load_stocks() -> List[Stock]:
    symbols_df = get_all_symbols_df()
    stocks = []
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


def compute_score(stocks: List[Stock], indicators: List[Indicator]) -> List[Stock]:
    progress_bar = st.progress(0)
    for index, stock in enumerate(stocks):
        for indicator in indicators:
            stock.add_indicator(indicator)
        progress_bar.progress(index / len(stocks))
    progress_bar.empty()
    return stocks
