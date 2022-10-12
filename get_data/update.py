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

    pbar = tqdm(total=len(index_symbols) + 3 * len(stock_symbols))

    for symbol in stock_symbols:
        try:
            financials = fetch_and_save_financials(
                symbol=symbol,
                directory=path_to_datasets / "financial",
            )
        except Exception as e:
            print(f"Problme fetching {symbol} financials")
            print(e)
        # TODO: add future financials
        pbar.update(1)
        try:
            sentiments = fetch_and_save_sentiment(
                symbol=symbol,
                beginning_date=datetime(2021, 1, 1),
                interval="1d",
                directory=path_to_datasets / "sentiment",
            )
        except Exception as e:
            print(f"Problme fetching {symbol} sentiment")
            print(e)
        pbar.update(1)
        try:
            klines = fetch_and_save_klines(
                symbol=symbol,
                beginning_date=datetime(2021, 1, 1),
                interval="1d",
                directory=path_to_datasets / "ohlcv",
            )
        except Exception as e:
            print(f"Problme fetching {symbol} klines")
            print(e)
        pbar.update(1)
    for symbol in index_symbols:
        try:
            klines = fetch_and_save_klines(
                symbol=symbol,
                beginning_date=datetime(2021, 1, 1),
                interval="1d",
                directory=path_to_datasets / "ohlcv",
            )
        except Exception as e:
            print(f"Problme fetching {symbol} klines")
            print(e)
        pbar.update(1)

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
