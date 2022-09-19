import concurrent.futures
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import streamlit as st
from get_data.financial_data import download_financials, fetch_financials
from get_data.ohlcv_data import download_klines, fetch_klines

from models.indicator import Indicator


@dataclass
class Stock:
    symbol: str
    start_date: datetime = datetime(2021, 1, 1)
    end_date: datetime = datetime.today()
    global_score: float = 0
    detailed_score: Dict[str, int] = field(default_factory=lambda: ({}))
    interval: str = "1d"

    retrieve_mode: str = "get"
    force_retrieve: bool = False

    def __post_init__(self):
        if self.retrieve_mode == "get":
            retrieve_klines_function = download_klines
            retrieve_financials_function = download_financials
        elif self.retrieve_mode == "fetch":
            retrieve_klines_function = fetch_klines
            retrieve_financials_function = fetch_financials
        else:
            raise NotImplementedError(
                f"retrieve_mode must be in ['get', 'fetch']. Got {self.retrieve_mode}"
            )
        try:
            self.klines = retrieve_klines_function(
                self.symbol,
                beginning_date=self.start_date,
                ending_date=self.end_date,
                interval="1d",
                force_download=self.force_retrieve,
                directory=Path("datasets/daily/ohlcv"),
            )
        except ValueError as e:
            self.klines = []

        try:
            self.financials = retrieve_financials_function(
                self.symbol,
                date=self.end_date,
                force_download=self.force_retrieve,
                directory=Path("datasets/daily/financials"),
            )
        except ValueError as e:
            self.financials = {}

    def add_indicator(self, indicator: Indicator):
        self.klines = indicator.apply_indicator(self.klines)

        if indicator.flag_column is not None:
            if np.abs(self.klines[indicator.flag_column].iloc[-1]) > 0:
                self.detailed_score[str(indicator)] = self.klines[
                    indicator.flag_column
                ].iloc[-1]
            self.global_score += self.klines[indicator.flag_column].iloc[-1]


def load_stocks(
    symbols,
    max_workers: int = 61,
    retrieve_mode: str = "get",
    force_retrieve: bool = False,
) -> Tuple[List[Stock], datetime]:
    stocks = []
    with concurrent.futures.ProcessPoolExecutor(max_workers) as executor:
        future_proc = [
            executor.submit(
                Stock,
                symbol,
                retrieve_mode=retrieve_mode,
                force_retrieve=force_retrieve,
            )
            for symbol in symbols
        ]
        for future in concurrent.futures.as_completed(future_proc):
            result = future.result()
            if len(result.klines) == 0:
                st.warning(f"{result.symbol} cannot be found.", icon="⚠️")
                continue
            stocks.append(result)
    if retrieve_mode == "fetch":
        updated_at = datetime.now()
    elif retrieve_mode == "get":
        modified_dates_ohlcv = pd.to_datetime(
            [
                1000 * x.lstat().st_mtime
                for x in Path("datasets/daily/financials").glob("*.json")
                if x.is_file()
            ]
            + [
                1000 * x.lstat().st_mtime
                for x in Path("datasets/daily/ohlcv").glob("*.csv")
                if x.is_file()
            ],
            utc=True,
            unit="ms",
        )
        LOCAL_TIMEZONE = datetime.now(timezone.utc).astimezone().tzinfo
        updated_at = modified_dates_ohlcv.max().tz_convert(LOCAL_TIMEZONE)
    return stocks, updated_at


def add_indicators(stock: Stock, indicators: List[Indicator]) -> Stock:
    for indicator in indicators:
        stock.add_indicator(indicator)
    return stock


def compute_score(
    stocks: List[Stock], indicators: List[Indicator], max_workers: int = 61
) -> List[Stock]:
    updated_stocks = []
    with concurrent.futures.ProcessPoolExecutor(max_workers) as executor:
        future_proc = [
            executor.submit(add_indicators, stock, indicators) for stock in stocks
        ]
    for future in concurrent.futures.as_completed(future_proc):
        updated_stocks.append(future.result())
    return updated_stocks
