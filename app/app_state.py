import streamlit as st
from models.stock import load_stocks

import app.plotting as plotting


def _initialize_variable_state(stock_symbols, nb_indicators):
    if "current_index" not in st.session_state:
        st.session_state["current_index"] = 0
    if "first_scan" not in st.session_state:
        st.session_state["first_scan"] = True
    if "elapsed_time" not in st.session_state:
        st.session_state["elapsed_time"] = 0
    for symbol in stock_symbols:
        if "tweet_index_" + symbol not in st.session_state:
            st.session_state["tweet_index_" + symbol] = 0
    for i in range(nb_indicators):
        if "stock_index_" + str(i) not in st.session_state:
            st.session_state["stock_index_" + str(i)] = 0


def _initialize_stock_state(
    symbols,
    max_workers,
    retrieve_mode,
    force_retrieve,
):

    if (
        "original_stocks" not in st.session_state
        or "updated_at" not in st.session_state
        or force_retrieve
    ):
        with st.spinner(f"Retrieving historical and financial data of {len(symbols)} stocks..."):
            (
                st.session_state["original_stocks"],
                st.session_state["updated_at"],
            ) = load_stocks(
                symbols,
                max_workers=max_workers,
                retrieve_mode=retrieve_mode,
                force_retrieve=force_retrieve,
            )
