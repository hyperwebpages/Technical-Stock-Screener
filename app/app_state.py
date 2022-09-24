from pathlib import Path
from typing import List, Tuple

import streamlit as st
import toml
from models.asset import load_stocks_indices

import app.plotting as plotting


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
    retrieve_mode = config["data_access"]["retrieve_mode"]
    path_to_index_symbols = Path(config["data_access"]["path_to_index_symbols"])
    path_to_stock_symbols = Path(config["data_access"]["path_to_stock_symbols"])
    path_to_ohlcv = Path(config["data_access"]["path_to_ohlcv"])
    path_to_financials = Path(config["data_access"]["path_to_financials"])

    bearer_token = config["twitter_api"]["bearer_token"]
    return (
        length_displayed_stocks,
        length_displayed_tweets,
        fork_mode,
        retrieve_mode,
        path_to_index_symbols,
        path_to_stock_symbols,
        path_to_ohlcv,
        path_to_financials,
        bearer_token,
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


def _initialize_stock_index_state(
    index_symbols: List[str],
    stock_symbols: List[str],
    fork_mode: str,
    retrieve_mode: str,
    force_download: bool,
    path_to_ohlcv: Path,
    path_to_financials: Path,
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
        or force_download
    ):
        with st.spinner(
            f"Retrieving historical and financial data of {len(index_symbols+stock_symbols)} stocks..."
        ):
            (
                st.session_state["original_indices"],
                st.session_state["original_stocks"],
                st.session_state["updated_at"],
            ) = load_stocks_indices(
                index_symbols,
                stock_symbols,
                fork_mode=fork_mode,
                retrieve_mode=retrieve_mode,
                force_download=force_download,
                path_to_ohlcv=path_to_ohlcv,
                path_to_financials=path_to_financials,
            )
