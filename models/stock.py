import concurrent.futures
import multiprocessing as mp
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
    force_download: bool = False
    path_to_ohlcv: Path = Path()
    path_to_financials: Path = Path()

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
                force_download=self.force_download,
                directory=self.path_to_ohlcv,
            )
        except ValueError as e:
            self.klines = []

        try:
            self.financials = retrieve_financials_function(
                self.symbol,
                date=self.end_date,
                force_download=self.force_download,
                directory=self.path_to_financials,
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
    symbols: List[str],
    max_workers: int,
    retrieve_mode: str,
    force_download: bool,
    path_to_ohlcv: Optional[Path] = None,
    path_to_financials: Optional[Path] = None,
) -> Tuple[List[Stock], datetime]:
    """Create `Stock` instances. Uses multiprocessing.

    Args:
        symbols (List[str]): list of symbols to create Stock instances with
        max_workers (int): max workers for the threading
        retrieve_mode (str): Retrieve mode. One of ["get", "fetch"].
            * `fetch` will only retrieve data from online, and won't save them.
            * `get` will first try to retrieve data from the disk before trying online
        force_download (bool): useful when `retrieve_mode=get`.
            The algorithm will always fetch data from online and save it.
        path_to_ohlcv (Path): path to the ohlcv data if `retrieve_mode=get`
        path_to_financials (Path): path to the financial data if `retrieve_mode=get`

    Returns:
        Tuple[List[Stock], datetime]: List of Stock instances and the time the data were lastly updated.
    """
    stocks = []
    with concurrent.futures.ProcessPoolExecutor(
        max_workers, mp_context=mp.get_context("fork")
    ) as executor:
        future_proc = [
            executor.submit(
                Stock,
                symbol,
                retrieve_mode=retrieve_mode,
                force_download=force_download,
                path_to_ohlcv=path_to_ohlcv,
                path_to_financials=path_to_financials,
            )
            for symbol in symbols
        ]
        for future in concurrent.futures.as_completed(future_proc):
            result = future.result()
            if len(result.klines) == 0:
                st.warning(f"{result.symbol} OHLCV cannot be found.", icon="⚠️")
                continue
            if len(result.financials) == 0:
                st.warning(f"{result.symbol} financials cannot be found.", icon="⚠️")
                continue
            stocks.append(result)
    if retrieve_mode == "fetch":
        updated_at = datetime.now()
    elif retrieve_mode == "get":

        modified_dates_ohlcv = pd.to_datetime(
            [
                1000 * x.lstat().st_mtime
                for x in path_to_financials.glob("*")
                if x.is_file()
            ]
            + [
                1000 * x.lstat().st_mtime
                for x in path_to_ohlcv.glob("*")
                if x.is_file()
            ],
            utc=True,
            unit="ms",
        )
        LOCAL_TIMEZONE = datetime.now(timezone.utc).astimezone().tzinfo
        updated_at = modified_dates_ohlcv.max().tz_convert(LOCAL_TIMEZONE)
    return stocks, updated_at


def add_indicators(stock: Stock, indicators: List[Indicator]) -> Stock:
    """Add indicators to the klines of a stock

    Args:
        stock (Stock): Stock to add klines to
        indicators (List[Indicator]): List of indicators to add

    Returns:
        Stock: modified stock (no copy)
    """
    for indicator in indicators:
        stock.add_indicator(indicator)
    return stock


def compute_score(
    stocks: List[Stock], indicators: List[Indicator], max_workers: int
) -> List[Stock]:
    """Computes the global and detailed score of each stock in list. Uses multiprocessing.

    Args:
        stocks (List[Stock]): List of stocks to compute score
        indicators (List[Indicator]): List of indicators giving score
        max_workers (int): max workers for the threading

    Returns:
        List[Stock]: list of updated stocks (no copy)
    """
    updated_stocks = []
    with concurrent.futures.ProcessPoolExecutor(
        max_workers, mp_context=mp.get_context("fork")
    ) as executor:
        future_proc = [
            executor.submit(add_indicators, stock, indicators) for stock in stocks
        ]
    for future in concurrent.futures.as_completed(future_proc):
        updated_stocks.append(future.result())
    return updated_stocks
