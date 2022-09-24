import concurrent.futures
import multiprocessing as mp
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st
from get_data.financial_data import download_financials, fetch_financials
from get_data.ohlcv_data import download_klines, fetch_klines

from models.indicator import Indicator


def format_int_or_na(value, format="\${:,}") -> str:
    if value is None:
        return "N/A"
    else:
        return format.format(value).replace(",", " ")


@dataclass
class Index:
    symbol: str
    start_date: datetime = datetime(2021, 1, 1)
    end_date: datetime = datetime.today()
    global_score: float = 0
    detailed_score: Dict[str, int] = field(default_factory=lambda: ({}))
    interval: str = "1d"

    def retrieve_klines(self, retrieve_mode, force_download, directory):
        if retrieve_mode == "get":
            retrieve_klines_function = download_klines
        elif retrieve_mode == "fetch":
            retrieve_klines_function = fetch_klines
        else:
            raise NotImplementedError(
                f"retrieve_mode must be in ['get', 'fetch']. Got {retrieve_mode}"
            )
        try:
            return retrieve_klines_function(
                self.symbol,
                beginning_date=self.start_date,
                ending_date=self.end_date,
                interval=self.interval,
                force_download=force_download,
                directory=directory,
            )
        except ValueError as e:
            return []

    def add_indicator(self, indicator: Indicator):
        self.klines = indicator.apply_indicator(self.klines)

        if indicator.flag_column is not None:
            if np.abs(self.klines[indicator.flag_column].iloc[-1]) > 0:
                self.detailed_score[str(indicator)] = self.klines[
                    indicator.flag_column
                ].iloc[-1]
            self.global_score += self.klines[indicator.flag_column].iloc[-1]

    @classmethod
    def load_index(
        cls,
        symbol: str,
        retrieve_mode: str,
        force_download: bool,
        path_to_ohlcv: Optional[Path] = None,
        **kwargs,
    ):
        current_cls = cls(symbol=symbol)
        current_cls.klines = current_cls.retrieve_klines(
            retrieve_mode=retrieve_mode,
            force_download=force_download,
            directory=path_to_ohlcv,
        )
        return current_cls


class Stock(Index):
    def retrieve_financials(self, retrieve_mode, force_download, directory):
        if retrieve_mode == "get":
            retrieve_financials_function = download_financials
        elif retrieve_mode == "fetch":
            retrieve_financials_function = fetch_financials
        else:
            raise NotImplementedError(
                f"retrieve_mode must be in ['get', 'fetch']. Got {retrieve_mode}"
            )
        try:
            return retrieve_financials_function(
                self.symbol,
                date=self.end_date,
                force_download=force_download,
                directory=directory,
            )
        except ValueError as e:
            return {}

    def financials_to_str(self):
        cols = [[], []]
        cols[0].append(
            "Target price (1 year): "
            + format_int_or_na(self.financials["targetMeanPrice"])
        )
        cols[0].append(
            "\nDay Low - Day High: "
            + format_int_or_na(self.financials["regularMarketDayLow"])
            + " - "
            + format_int_or_na(self.financials["regularMarketDayHigh"])
        )
        cols[0].append(
            "\nMarket Change: "
            + format_int_or_na(
                self.financials["regularMarketChangePercent"], format="{:.3f}%"
            )
        )
        cols[0].append(
            "\n1 year week change: "
            + format_int_or_na(self.financials["52WeekChange"], format="{:.3f}%")
        )
        cols[1].append("Market Cap: " + format_int_or_na(self.financials["marketCap"]))
        cols[1].append(
            "\nTotal Revenue: " + format_int_or_na(self.financials["totalRevenue"])
        )
        cols[1].append(
            "\nAverage Daily Volume (last 10 days): "
            + format_int_or_na(
                self.financials["averageDailyVolume10Day"], format="{:,}"
            )
        )
        return cols

    @classmethod
    def load_stock(
        cls,
        symbol: str,
        retrieve_mode: str,
        force_download: bool,
        path_to_ohlcv: Optional[Path] = None,
        path_to_financials: Optional[Path] = None,
        **kwargs,
    ):
        current_cls = cls(symbol=symbol)
        current_cls.klines = current_cls.retrieve_klines(
            retrieve_mode=retrieve_mode,
            force_download=force_download,
            directory=path_to_ohlcv,
        )
        current_cls.financials = current_cls.retrieve_financials(
            retrieve_mode=retrieve_mode,
            force_download=force_download,
            directory=path_to_financials,
        )
        return current_cls


def load_asset(
    symbols: List[str],
    loading_function: Callable,
    fork_mode: int,
    retrieve_mode: str,
    force_download: bool,
    path_to_ohlcv: Optional[Path] = None,
    path_to_financials: Optional[Path] = None,
) -> Tuple[List[Stock], datetime]:
    """Create `Stock` instances. Uses multiprocessing.

    Args:
        symbols (List[str]): list of symbols to create Stock instances with
        fork_mode (str): fork mode. One of ["fork", "spawn"]
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

    def callback(result):
        if hasattr(result, "klines") and len(result.klines) == 0:
            st.warning(f"{result.symbol} OHLCV cannot be found.", icon="⚠️")
        elif hasattr(result, "financials") and len(result.financials) == 0:
            st.warning(f"{result.symbol} financials cannot be found.", icon="⚠️")
        else:
            stocks.append(result)

    pool = mp.get_context(fork_mode).Pool()
    for symbol in symbols:
        pool.apply_async(
            loading_function,
            kwds=dict(
                symbol=symbol,
                retrieve_mode=retrieve_mode,
                force_download=force_download,
                path_to_ohlcv=path_to_ohlcv,
                path_to_financials=path_to_financials,
            ),
            callback=callback,
        )
    pool.close()
    pool.join()
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


def load_stocks_indices(
    index_symbols: List[str],
    stock_symbols: List[str],
    fork_mode: int,
    retrieve_mode: str,
    force_download: bool,
    path_to_ohlcv: Optional[Path] = None,
    path_to_financials: Optional[Path] = None,
) -> Tuple[List[Stock], datetime]:
    """Create `Stock` instances. Uses multiprocessing.

    Args:
        index_symbols (List[str]): list of symbols to create Index instances with
        stock_symbols (List[str]): list of symbols to create Stock instances with
        fork_mode (str): fork mode. One of ["fork", "spawn"]
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
    indices, index_updated_at = load_asset(
        index_symbols,
        Index.load_index,
        fork_mode,
        retrieve_mode,
        force_download,
        path_to_ohlcv,
        path_to_financials,
    )
    stocks, stock_updated_at = load_asset(
        stock_symbols,
        Stock.load_stock,
        fork_mode,
        retrieve_mode,
        force_download,
        path_to_ohlcv,
        path_to_financials,
    )

    return indices, stocks, min(index_updated_at, stock_updated_at)


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
    stocks: List[Stock], indicators: List[Indicator], fork_mode: str
) -> List[Stock]:
    """Computes the global and detailed score of each stock in list. Uses multiprocessing.

    Args:
        stocks (List[Stock]): List of stocks to compute score
        indicators (List[Indicator]): List of indicators giving score
        fork_mode (str): fork mode. One of ["fork", "spawn"]

    Returns:
        List[Stock]: list of updated stocks (no copy)
    """
    updated_stocks = []

    def callback(result):
        updated_stocks.append(result)

    pool = mp.get_context(fork_mode).Pool()
    for stock in stocks:
        pool.apply_async(
            add_indicators, (stock, indicators), callback=callback,
        )
    pool.close()
    pool.join()
    return updated_stocks
