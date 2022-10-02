import os

import requests
import streamlit as st
import streamlit.components.v1 as components
import tweepy

from models.asset import Stock


class Tweet(object):
    """Streamlit component containing an embed tweet."""

    def __init__(self, tweet_id):
        api = "https://publish.twitter.com/oembed?url=https://twitter.com/twitter/statuses/{tweet_id}".format(
            tweet_id=tweet_id
        )
        response = requests.get(api, timeout=5)
        self.text = response.json()["html"]
        self.text = self.text.replace(
            'class="twitter-tweet"', 'class="twitter-tweet" width="50"'
        )

    def _repr_html_(self):
        return self.text

    def component(self):
        return components.html(self.text, height=500, width=500)


class TweetsSearch:
    """Contains the result of a tweet search."""

    def __init__(self, stock: Stock) -> None:
        bearer_token = os.environ.get("TWITTER_BEARER")
        self.client = tweepy.Client(bearer_token)
        self.stock = stock
        self.query = f"stock #{stock.symbol} lang:en -is:retweet"
        self.tweet_search = self.client.search_recent_tweets(
            query=self.query,
            max_results=100,
            tweet_fields=["id", "public_metrics"],
        )[0]
        if self.tweet_search is None:
            self.tweet_search = []
        self.tweet_search.sort(
            key=lambda t: t.public_metrics["like_count"], reverse=True
        )

    def __len__(self):
        return len(self.tweet_search)

    def __getitem__(self, i):
        return Tweet(self.tweet_search[i].id)
