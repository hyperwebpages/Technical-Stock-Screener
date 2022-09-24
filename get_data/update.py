import concurrent.futures
import multiprocessing as mp
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import toml
from models.asset import Index, Stock

from get_data.financial import fetch_and_save_financials
from get_data.ohlcv import fetch_and_save_klines


def update_data(
    index_symbols,
    stock_symbols,
    path_to_ohlcv,
    path_to_financials,
    fork_mode,
):
    problematic_ohlcv = []
    problematic_financials = []

    def health_check(result):
        if hasattr(result, "klines") and len(result.klines) == 0:
            problematic_ohlcv.append(result.symbol)
        if hasattr(result, "financials") and len(result.financials) == 0:
            problematic_financials.append(result.symbol)

    pool = mp.get_context(fork_mode).Pool()
    for symbol in stock_symbols:
        pool.apply_async(
            fetch_and_save_financials,
            kwds=dict(
                symbol=symbol,
                directory=path_to_financials,
            ),
            callback=health_check,
        )
    for symbol in index_symbols + stock_symbols:
        pool.apply_async(
            fetch_and_save_klines,
            kwds=dict(
                symbol=symbol,
                beginning_date=datetime(2021, 1, 1),
                interval="1d",
                directory=path_to_ohlcv,
            ),
            callback=health_check,
        )
    pool.close()
    pool.join()
    return problematic_ohlcv, problematic_financials


if __name__ == "__main__":
    pass
