import concurrent.futures
import multiprocessing as mp
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st
from get_data.financial import select_financials
from get_data.ohlcv import select_klines
from get_data.sentiment import select_sentiment


def format_int_or_na(value, format="\${:,}") -> str:
    if value is None:
        return "N/A"
    else:
        return format.format(value).replace(",", " ")


@dataclass
class Index:
    symbol: str
    global_score: float = 0
    detailed_score: Dict[str, int] = field(default_factory=lambda: ({}))
    interval: str = "1d"

    def add_indicator(self, indicator):
        indicator.apply_indicator(self)

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
        path_to_datasets: Path,
        **kwargs,
    ):
        current_cls = cls(symbol=symbol)
        current_cls.klines = select_klines(
            symbol=current_cls.symbol,
            interval=current_cls.interval,
            directory=path_to_datasets / "ohlcv",
        )
        return current_cls


class Stock(Index):
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
        path_to_datasets: Path,
        **kwargs,
    ):
        current_cls = cls(symbol=symbol)
        current_cls.klines = select_klines(
            symbol=current_cls.symbol,
            interval=current_cls.interval,
            directory=path_to_datasets / "ohlcv",
        )
        current_cls.klines["score"] = 0
        sentiments = select_sentiment(
            symbol=current_cls.symbol,
            interval=current_cls.interval,
            directory=path_to_datasets / "sentiment",
        )
        current_cls.klines = (
            pd.concat([current_cls.klines, sentiments])
            .sort_index(inplace=False)
            .fillna(method="ffill")
            .fillna(method="bfill")
        )
        current_cls.klines = current_cls.klines.groupby(
            [current_cls.klines.index.date]
        ).max()
        current_cls.klines.index = pd.to_datetime(current_cls.klines.index, utc=True)
        current_cls.klines = current_cls.klines.loc[: sentiments.index[-1]]

        current_cls.financials = select_financials(
            symbol=current_cls.symbol,
            directory=path_to_datasets / "financial",
        )
        return current_cls


def load_asset(
    symbols: List[str],
    loading_function: Callable,
    path_to_datasets: Path,
) -> Tuple[List[Stock], datetime]:
    """Create `Stock` instances. Uses multiprocessing.

    Args:
        symbols (List[str]): list of symbols to create Stock instances with
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
        mp_context=mp.get_context("spawn")
    ) as executor:
        future_proc = [
            executor.submit(
                loading_function,
                symbol=symbol,
                path_to_datasets=path_to_datasets,
            )
            for symbol in symbols
        ]
        for future in concurrent.futures.as_completed(future_proc):
            result = future.result()
            stocks.append(result)
    return stocks


def load_stocks_indices(
    index_symbols: List[str],
    stock_symbols: List[str],
    path_to_datasets: Path,
) -> Tuple[List[Stock], datetime]:
    """Create `Stock` instances. Uses multiprocessing.

    Args:
        index_symbols (List[str]): list of symbols to create Index instances with
        stock_symbols (List[str]): list of symbols to create Stock instances with
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
    indices = load_asset(
        index_symbols,
        Index.load_index,
        path_to_datasets,
    )
    stocks = load_asset(
        stock_symbols,
        Stock.load_stock,
        path_to_datasets,
    )
    updated_at = modified_dates_ohlcv = pd.to_datetime(
        [
            1000 * x.lstat().st_mtime
            for x in path_to_datasets.glob("**/*")
            if x.is_file()
        ],
        utc=True,
        unit="ms",
    )
    LOCAL_TIMEZONE = datetime.now(timezone.utc).astimezone().tzinfo
    updated_at = modified_dates_ohlcv.max().tz_convert(LOCAL_TIMEZONE)
    return indices, stocks, updated_at


def initialize_indicators(stock: Stock, indicators) -> Stock:
    """Add indicators to the klines of a stock

    Args:
        stock (Stock): Stock to add klines to
        indicators (List[Indicator]): List of indicators to add

    Returns:
        Stock: modified stock (no copy)
    """
    stock.global_score = 0
    stock.detailed_score = {}
    for indicator in indicators:
        stock.add_indicator(indicator)
    return stock


def compute_score(stocks: List[Stock], indicators) -> List[Stock]:
    """Computes the global and detailed score of each stock in list. Uses multiprocessing.

    Args:
        stocks (List[Stock]): List of stocks to compute score
        indicators (List[Indicator]): List of indicators giving score

    Returns:
        List[Stock]: list of updated stocks (no copy)
    """
    updated_stocks = []
    with concurrent.futures.ProcessPoolExecutor(
        mp_context=mp.get_context("spawn")
    ) as executor:
        future_proc = [
            executor.submit(
                initialize_indicators,
                stock=stock,
                indicators=indicators,
            )
            for stock in stocks
        ]
        for future in concurrent.futures.as_completed(future_proc):
            result = future.result()
            updated_stocks.append(result)
    return updated_stocks
