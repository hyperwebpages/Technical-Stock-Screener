import concurrent.futures
import multiprocessing as mp
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import nltk
import numpy as np
import pandas as pd
import pytz
import streamlit as st
import toml
from models.asset import Index, Stock
from tqdm import tqdm

from get_data.financial import fetch_and_save_financials
from get_data.ohlcv import fetch_and_save_klines
from get_data.sentiment import fetch_and_save_sentiment


def update_data(
    index_symbols,
    stock_symbols,
    path_to_datasets,
):
    nltk.downloader.download("vader_lexicon")

    problematic_ohlcv = []
    problematic_financials = []

    pbar = tqdm(total=len(index_symbols) + 2 * len(stock_symbols))

    def health_check(result):
        pbar.update(1)
        if hasattr(result, "klines") and len(result.klines) == 0:
            problematic_ohlcv.append(result.symbol)
        if hasattr(result, "financials") and len(result.financials) == 0:
            problematic_financials.append(result.symbol)

    with concurrent.futures.ProcessPoolExecutor(mp.get_context("spawn")) as executor:
        future_financials = [
            executor.submit(
                fetch_and_save_financials,
                symbol=symbol,
                directory=path_to_datasets / "financial",
            )
            for symbol in stock_symbols
        ]
        future_sentiment = [
            executor.submit(
                fetch_and_save_sentiment,
                symbol=symbol,
                beginning_date=datetime(2021, 1, 1),
                interval="1d",
                directory=path_to_datasets / "sentiment",
            )
            for symbol in stock_symbols
        ]
        future_klines = [
            executor.submit(
                fetch_and_save_klines,
                symbol=symbol,
                beginning_date=datetime(2021, 1, 1),
                interval="1d",
                directory=path_to_datasets / "ohlcv",
            )
            for symbol in stock_symbols
        ]
        for future in concurrent.futures.as_completed(
            future_financials + future_sentiment + future_klines
        ):
            health_check(future.result())

    pbar.close()
    return problematic_ohlcv, problematic_financials


if __name__ == "__main__":
    current_datetime_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
    current_datetime_nyc = current_datetime_utc.astimezone(pytz.timezone("US/Eastern"))

    print("Current UTC time:", current_datetime_utc)
    print("Current NYC / Market time:", current_datetime_nyc)
    config = toml.load(Path("config.toml"))

    path_to_index_symbols = Path(config["data_access"]["path_to_index_symbols"])
    path_to_stock_symbols = Path(config["data_access"]["path_to_stock_symbols"])
    path_to_datasets = Path(config["data_access"]["path_to_datasets"])

    index_symbols = list(pd.read_csv(path_to_index_symbols)["symbol"])
    stock_symbols = list(pd.read_csv(path_to_stock_symbols)["symbol"])

    problematic_ohlcv, problematic_financials = update_data(
        index_symbols,
        stock_symbols,
        path_to_datasets,
    )

    for p_ohlcv in problematic_ohlcv:
        print(f"Probleme retrieving OHLCV data on {p_ohlcv}.")
    for p_ohlcv in problematic_ohlcv:
        print(f"Probleme retrieving financial data on {p_ohlcv}.")
