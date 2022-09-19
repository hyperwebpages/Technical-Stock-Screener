import streamlit as st
from models.stock import load_stocks
from models.tweet import TweetsSearch

import app.plotting as plotting


def format_int_or_na(value, format="\${:,}"):
    if value is None:
        return "N/A"
    else:
        return format.format(value).replace(",", " ")


def tweets_widget(
    tweet_search,
    index_in_tweet_search,
    length_displayed_tweets,
):
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


def expanders_widget(
    selected_stocks,
    index_in_stock_list,
    length_displayed_stocks,
    length_displayed_tweets,
    indicators_to_draw_above,
    indicators_to_draw_beside,
):
    for index in range(
        index_in_stock_list,
        index_in_stock_list + length_displayed_stocks,
    ):
        if index >= len(selected_stocks):
            break
        stock = selected_stocks[index]
        with st.expander(f"{stock.symbol} charts", expanded=False):
            financials = stock.financials

            st.write(financials["longName"] + ", " + financials["industry"])

            _, col1, col2, _ = st.columns([1, 5, 5, 1])

            with col1:
                st.write(
                    "Target price (1 year): "
                    + format_int_or_na(financials["targetMeanPrice"])
                )
                st.write(
                    "Day Low - Day High: "
                    + format_int_or_na(financials["regularMarketDayLow"])
                    + " - "
                    + format_int_or_na(financials["regularMarketDayHigh"])
                )
                st.write(
                    "Market Change: "
                    + format_int_or_na(
                        financials["regularMarketChangePercent"], format="{:.3f}%"
                    )
                )
                st.write(
                    "1 year week change: "
                    + format_int_or_na(financials["52WeekChange"], format="{:.3f}%")
                )

            with col2:
                st.write("Market Cap: " + format_int_or_na(financials["marketCap"]))
                st.write(
                    "Total Revenue: " + format_int_or_na(financials["totalRevenue"])
                )
                st.write(
                    "Average Daily Volume (last 10 days): "
                    + format_int_or_na(
                        financials["averageDailyVolume10Day"], format="{:,}"
                    )
                )

            fig = plotting.mutliple_row_charts(
                stock, indicators_to_draw_above, indicators_to_draw_beside
            )
            st.plotly_chart(fig, use_container_width=True)

            tweet_search = TweetsSearch(stock)

            index_in_tweet_search = st.session_state["tweet_index_" + stock.symbol]
            tweets_widget(tweet_search, index_in_tweet_search, length_displayed_tweets)

            if st.session_state[
                "tweet_index_" + stock.symbol
            ] + length_displayed_tweets < len(tweet_search) and st.button(
                "Load more tweets", key="button_tweet_index_" + stock.symbol
            ):
                st.session_state[
                    "tweet_index_" + stock.symbol
                ] += length_displayed_tweets

        with st.expander(f"{stock.symbol} raw data", expanded=False):
            st.table(stock.klines)
