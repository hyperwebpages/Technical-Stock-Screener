import os
import sys
from pathlib import Path

sys.path.append(Path("/app/stock-screener"))
sys.path.append(os.getcwd())

from time import time

import numpy as np
import pandas as pd
import streamlit as st
from models.asset import compute_score
from models.indicator import EMA, MACD, RSI, CipherB, SentimentScore, StochRSI

import app.plotting as plotting
import app_state
import widgets


def run_app():
    st.set_page_config(layout="wide")

    (
        length_displayed_stocks,
        length_displayed_tweets,
        fork_mode,
        path_to_index_symbols,
        path_to_stock_symbols,
        path_to_datasets,
        bearer_token,
    ) = app_state.read_config_file(Path("config.toml"))

    rsi = RSI()
    stochrsi = StochRSI()
    macd = MACD()
    ema = EMA()
    cipher_b = CipherB()
    sentiment_score = SentimentScore()

    indicators = [rsi, stochrsi, ema, macd, cipher_b, sentiment_score]

    index_symbols = list(pd.read_csv(path_to_index_symbols)["symbol"])
    stock_symbols = list(pd.read_csv(path_to_stock_symbols)["symbol"])
    nb_indicators = len(indicators)

    app_state._initialize_variable_state(index_symbols + stock_symbols, nb_indicators)
    app_state._load_asset_data(
        index_symbols,
        stock_symbols,
        fork_mode,
        path_to_datasets,
    )

    with st.sidebar:
        for ind in indicators:
            ind.checkbox()
            if ind.on:
                ind.text_input()
        on_indicators = [ind for ind in indicators if ind.on]
        scan_button = st.button("Scan")

    if scan_button:
        app_state._initialize_variable_state(
            index_symbols + stock_symbols, nb_indicators
        )

        with st.spinner(
            f"Computing indicators on {len(index_symbols)+len(stock_symbols)} assets..."
        ):
            start_time = time()
            st.session_state["indices"] = sorted(
                compute_score(
                    st.session_state["original_indices"], on_indicators, fork_mode
                ),
                key=lambda index: (np.abs(index.global_score), index.symbol),
            )
            st.session_state["stocks"] = sorted(
                compute_score(
                    st.session_state["original_stocks"], on_indicators, fork_mode
                ),
                key=lambda stock: (np.abs(stock.global_score), stock.symbol),
            )
            st.session_state["elapsed_time"] = time() - start_time
            st.session_state["first_scan"] = False

    if st.session_state["first_scan"]:
        with open(Path("templates/welcome.txt"), "r") as welcome_file:
            welcome_str = welcome_file.read()
            st.markdown(welcome_str)
    else:
        indices = st.session_state["indices"]
        stocks = st.session_state["stocks"]
        with open(Path("templates/global_analysis.txt"), "r") as global_analysis_file:
            global_analysis_str = global_analysis_file.read()
            st.markdown(
                global_analysis_str.format(
                    len_assets=len(indices) + len(stocks),
                    elapsed_time=1000 * st.session_state["elapsed_time"],
                    non_neutral_pressures=len(
                        [1 for s in stocks if len(s.detailed_score) > 0]
                    ),
                )
            )

        st.plotly_chart(plotting.indicator_histogram(indices, stocks))

        with open(
            Path("templates/specific_analysis.txt"), "r"
        ) as specific_analysis_file:
            st.markdown(specific_analysis_file.read())

        indicators_to_draw_above = st.multiselect(
            "Indicators to draw above the ohlc chart",
            options=stocks[0].klines.columns,
            default=["Volume"],
        )
        indicators_to_draw_beside = st.multiselect(
            "Indicators to draw beside the ohlc chart",
            options=stocks[0].klines.columns,
            default=[
                ind.flag_column for ind in on_indicators if ind.flag_column is not None
            ],
        )

        agreed_indicators = st.slider(
            label="Filter assets based matching conditions",
            min_value=0,
            max_value=len(on_indicators),
            step=1,
            value=int(np.abs(stocks[-1].global_score)),
        )

        selected_indices = [
            index
            for index in indices
            if np.abs(index.global_score) == agreed_indicators
        ]
        st.write(
            f"{len(selected_indices)} indices found matching {agreed_indicators} conditions."
        )

        widgets.expanders_widget(
            selected_indices,
            bearer_token,
            0,
            5,
            length_displayed_tweets,
            indicators_to_draw_above,
            indicators_to_draw_beside,
        )

        selected_stocks = [
            stock for stock in stocks if np.abs(stock.global_score) == agreed_indicators
        ]
        index_in_stock_list = st.session_state["stock_index_" + str(agreed_indicators)]
        st.write(
            f"{len(selected_stocks)} stocks found matching {agreed_indicators} conditions."
        )

        widgets.expanders_widget(
            selected_stocks,
            bearer_token,
            index_in_stock_list,
            length_displayed_stocks,
            length_displayed_tweets,
            indicators_to_draw_above,
            indicators_to_draw_beside,
        )

        if index_in_stock_list + length_displayed_stocks < len(
            selected_stocks
        ) and st.button("Load more stocks"):
            st.session_state[
                "stock_index_" + str(agreed_indicators)
            ] += length_displayed_stocks

    if st.button("Update data"):
        app_state._download_asset_data(
            index_symbols,
            stock_symbols,
            path_to_datasets,
            fork_mode,
        )
    st.write(f"Last update at: {st.session_state['updated_at']}")


if __name__ == "__main__":
    run_app()
