import sys
from pathlib import Path
from typing import List, Tuple

import pandas as pd
import streamlit as st
import toml
from get_data.update import update_data
from models.asset import load_stocks_indices


def read_config_file(path: Path) -> Tuple:
    """Reads the config file located at `path`.

    Args:
        path (Path): path to the config file

    Returns:
        Tuple: tuple containing all the values of the config file.
    """
    config = toml.load(path)
    length_displayed_stocks = config["displaying"]["length_displayed_stocks"]
    length_displayed_tweets = config["displaying"]["length_displayed_tweets"]

    fork_mode = config["data_access"]["fork_mode"]
    path_to_index_symbols = Path(config["data_access"]["path_to_index_symbols"])
    path_to_stock_symbols = Path(config["data_access"]["path_to_stock_symbols"])
    path_to_datasets = Path(config["data_access"]["path_to_datasets"])
    return (
        length_displayed_stocks,
        length_displayed_tweets,
        fork_mode,
        path_to_index_symbols,
        path_to_stock_symbols,
        path_to_datasets,
    )


def _initialize_variable_state(symbols: List[str], nb_indicators: int):
    """Initializes streamlit `session_state`.

    Args:
        symbols (List[str]): list of symbols
        nb_indicators (int): number of indicators used in the website.
    """
    if "current_index" not in st.session_state:
        st.session_state["current_index"] = 0
    if "first_scan" not in st.session_state:
        st.session_state["first_scan"] = True
    if "elapsed_time" not in st.session_state:
        st.session_state["elapsed_time"] = 0
    for symbol in symbols:
        if "tweet_index_" + symbol not in st.session_state:
            st.session_state["tweet_index_" + symbol] = 0
    for i in range(nb_indicators):
        if "stock_index_" + str(i) not in st.session_state:
            st.session_state["stock_index_" + str(i)] = 0


def _load_asset_data(
    index_symbols: List[str],
    stock_symbols: List[str],
    fork_mode: str,
    path_to_datasets: Path,
):
    """Loads the original stocks, without any indicators in it.

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
    """
    if (
        "original_stocks" not in st.session_state
        or "updated_at" not in st.session_state
    ):
        with st.spinner(
            f"Loading historical and financial data of {len(index_symbols+stock_symbols)} assets..."
        ):
            (
                st.session_state["original_indices"],
                st.session_state["original_stocks"],
                st.session_state["updated_at"],
            ) = load_stocks_indices(
                index_symbols,
                stock_symbols,
                fork_mode=fork_mode,
                path_to_datasets=path_to_datasets,
            )


def _download_asset_data(
    index_symbols: List,
    stock_symbols: List,
    path_to_datasets: Path,
    fork_mode: str,
):
    with st.spinner(
        f"Downloading historical and financial data of {len(index_symbols+stock_symbols)} assets..."
    ):
        problematic_ohlcv, problematic_financials = update_data(
            index_symbols,
            stock_symbols,
            path_to_datasets,
            fork_mode,
        )
    for pb_index in problematic_ohlcv:
        st.warning(f"{pb_index.symbol} OHLCV cannot be found.", icon="⚠️")
    for pb_index in problematic_financials:
        st.warning(f"{pb_index.symbol} financials cannot be found.", icon="⚠️")
