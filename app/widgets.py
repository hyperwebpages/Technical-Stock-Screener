from typing import List

import streamlit as st
from models.asset import Stock
from models.tweet import TweetsSearch

import app.plotting as plotting


def tweets_widget(
    tweet_search: TweetsSearch,
    index_in_tweet_search: int,
    length_displayed_tweets: int,
) -> None:
    """Widget composed of a row of tweets.

    Args:
        tweet_search (TweetsSearch): object containing the list of tweets in `tweet_search[i]`
        index_in_tweet_search (int): index of the first tweet in the tweet search to display
        length_displayed_tweets (int): number of tweets to display per row
    """
    cols = st.columns(length_displayed_tweets)
    idx_col = 0
    idx_tweet = index_in_tweet_search
    while idx_col < len(cols):
        col = cols[idx_col]
        with col:
            if idx_tweet >= len(tweet_search):
                break
            try:
                tweet_search[idx_tweet].component()
                idx_col += 1
            except Exception as e:
                pass
            idx_tweet += 1


def expander_widget(
    stock: Stock,
    length_displayed_tweets: int,
    indicators_to_draw_above: List,
    indicators_to_draw_beside: List,
) -> None:
    """Widget which contains every information about a specific stock:
        * its name and industry
        * its financials
        * OHLC chart and some indicator charts
        * some 1-week old tweets related to the stock

    Args:
        stock (Stock): stock to display
        length_displayed_tweets (int): number of tweet widgets displayed per stock
        indicators_to_draw_above (List): indicators to draw above the OHLC chart
        indicators_to_draw_beside (List): indicators to draw beside the OHLC chart
    """
    if isinstance(stock, Stock):
        financials = stock.financials
        st.write(financials.get("longName", stock.symbol) + ", " + financials.get("industry", "N/A"))

        _, col1, col2, _ = st.columns([1, 4, 4, 1])
        financial_cols = stock.financials_to_str()
        for col, financial_col in zip([col1, col2], financial_cols):
            for f_col in financial_col:
                col.write(f_col)

    fig = plotting.mutliple_row_charts(
        stock, indicators_to_draw_above, indicators_to_draw_beside
    )
    st.plotly_chart(fig, use_container_width=True)

    tweet_search = TweetsSearch(stock)

    index_in_tweet_search = st.session_state["tweet_index_" + stock.symbol]
    tweets_widget(tweet_search, index_in_tweet_search, length_displayed_tweets)

    if st.session_state["tweet_index_" + stock.symbol] + length_displayed_tweets < len(
        tweet_search
    ) and st.button("Load more tweets", key="button_tweet_index_" + stock.symbol):
        st.session_state["tweet_index_" + stock.symbol] += length_displayed_tweets


def expanders_widget(
    stocks: List[Stock],
    index_in_stock_list: int,
    length_displayed_stocks: int,
    length_displayed_tweets: int,
    indicators_to_draw_above: List,
    indicators_to_draw_beside: List,
) -> None:
    """Mutiple expander widgets.

    Args:
        stocks (List[Stock]): list of stocks to display in expanders
        index_in_stock_list (int): index of the first stock to display
        length_displayed_stocks (int): number of expander widgets displayed in the page
        length_displayed_tweets (int): number of tweet widgets displayed per stock
        indicators_to_draw_above (List): indicators to draw above the OHLC chart
        indicators_to_draw_beside (List): indicators to draw beside the OHLC chart
    """
    for index in range(
        index_in_stock_list,
        index_in_stock_list + length_displayed_stocks,
    ):
        if index >= len(stocks):
            break
        stock = stocks[index]
        with st.expander(f"{stock.symbol} charts", expanded=False):
            expander_widget(
                stock,
                length_displayed_tweets,
                indicators_to_draw_above,
                indicators_to_draw_beside,
            )

        with st.expander(f"{stock.symbol} raw data", expanded=False):
            st.table(stock.klines)
