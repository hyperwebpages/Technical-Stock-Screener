import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytz
import requests
import yfinance as yf
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from requests.adapters import HTTPAdapter, Retry

PATH_TO_DATASETS = Path("../datasets/daily")
FORMAT = "%Y-%m-%d"
"""Expected datetime format"""
INDICES_TRANSLATIONS = {
    "BTC": "BTC-USD",
    "DOW": "^DJI",
    "EUR": "EURUSD=X",
    "SP500": "^GSPC",
    "Nasdaq": "^NDX",
}


def fetch_sentiment(
    symbol: str,
    beginning_date: datetime,
    interval: str,
    **kwargs,
) -> pd.DataFrame:
    """Retrieve klines thanks to the Yahoo Finance API.

    Args:
        symbol (str): ticker to download eg `AAPL`
        beginning_date (datetime): open time
        interval (str): interval of klines, eg `6h`.

    Returns:
        pd.DataFrame: dataframe containing the klines fetched online.
    """
    news = []

    api = os.environ.get("ALPACA_API")
    api_secret = os.environ.get("ALPACA_API_SECRET")
    headers = {"Apca-Api-Key-Id": api, "Apca-Api-Secret-Key": api_secret}
    url = "https://data.alpaca.markets/v1beta1/news?"

    ending_date = datetime.now(timezone.utc)
    beginning_date = pytz.utc.localize(beginning_date)
    sentiment = []
    while ending_date > beginning_date:
        querystring = {
            "symbols": symbol,
            "start": beginning_date.strftime(FORMAT),
            "end": ending_date.strftime(FORMAT),
            "limit": 50,
        }

        request_session = requests.Session()
        retries = Retry(total=7, backoff_factor=2, status_forcelist=[429])
        request_session.mount("https://", HTTPAdapter(max_retries=retries))
        request = request_session.get(url, headers=headers, params=querystring).json()

        if len(request["news"]) == 0:
            break

        _sentiment = pd.DataFrame.from_dict(request["news"]).drop(
            labels=[
                "author",
                "content",
                "id",
                "images",
                "source",
                "summary",
                "symbols",
                "updated_at",
                "url",
            ],
            axis=1,
        )
        _sentiment.loc[:, "created_at"] = pd.to_datetime(
            _sentiment.pop("created_at"), utc=True
        )
        _sentiment = _sentiment.set_index("created_at", drop=True)
        _sentiment.index = _sentiment.index.tz_convert(pytz.UTC).rename("Datetime")
        news.append(_sentiment)

        ending_date = _sentiment.index[-1]

    vader = SentimentIntensityAnalyzer()
    sentiment = pd.concat(news)
    sentiment["score"] = sentiment["headline"].apply(
        lambda headline: vader.polarity_scores(headline)["compound"]
    )
    sentiment = sentiment.groupby([sentiment.index.date]).sum()
    sentiment.index = pd.to_datetime(sentiment.index, utc=True).rename("Datetime")
    sentiment = sentiment.astype("float64")
    return sentiment[beginning_date:]


def save_sentiment(
    data: pd.DataFrame,
    symbol: str,
    interval: str,
    directory: Path,
    **kwargs,
) -> str:
    """Save sentiment data in `directory`.

    Args:
        data (pd.DataFrame): data/ sentiment to save
        symbol (str): ticker to download eg `AAPL`
        interval (str): interval of sentiment, eg `6h`.
        directory (Path): directory to save the sentiment.

    Raises:
        ValueError: if data is an empty dataframe.

    Returns:
        str: filename containing the data
    """
    filename = Path(directory) / "_".join(
        [
            symbol,
            interval,
        ]
    )
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    filename = str(filename) + ".csv"
    if len(data) > 0:
        data.to_csv(filename)
    else:
        raise ValueError("Data is empty")
    return filename


def fetch_and_save_sentiment(
    symbol: str,
    beginning_date: datetime,
    interval: str,
    directory: Path,
    **kwargs,
) -> str:
    """
    Downloads sentiment of `symbol` from `beginning_date` to `ending_date`, at interval `interval`
    and saves them in `directory`.
    Args:
        symbol (str): ticker to download eg `AAPL`
        beginning_date (datetime): open time
        ending_date (datetime): close time
        interval (str): interval of sentiment, eg `6h`.
        directory (Path): directory to save the sentiment.
    Returns:
        str: filename of csv file containing the sentiment
    """
    sentiment = fetch_sentiment(
        symbol,
        beginning_date,
        interval,
    )
    filename = save_sentiment(
        sentiment,
        symbol,
        interval,
        directory,
    )
    return filename


def select_sentiment(
    symbol: str, interval: str, directory: Path, **kwargs
) -> pd.DataFrame:

    """
    Selects sentiment of `symbol` from `beginning_date` to `to_date`, at interval `ending_date`.
    If the sentiment have already been downloaded, it fetches it in the csv file, unless `force_download=True`.
    Otherwise, it downloads the data from the Yahoo Finance API.
    Args:
        symbol (str): ticker to download eg `AAPL`
        beginning_date (datetime): open time
        ending_date (datetime): close time
        interval (str): interval of sentiment, eg `6h`.
        force_download (bool): whether to re-download the financials, even it they are already located in `directory`.
        directory (Path): directory to save the sentiment.
    Returns:
        pd.DataFrame: dataframe containing sentiment
    """
    p = Path(directory).glob("*.csv")
    files = [x for x in p if x.is_file()]
    filenames = [x.stem.split("_") for x in files]
    df_files = pd.DataFrame(filenames, columns=["symbol", "interval"])

    perfect_file = df_files[
        (df_files["symbol"] == symbol) & (df_files["interval"] == interval)
    ]

    if not perfect_file.empty:
        filename = files[perfect_file.index[0]]
        sentiment = pd.read_csv(filename)
        sentiment = sentiment.rename(columns={sentiment.columns[0]: "Datetime"})
        sentiment.loc[:, "Datetime"] = pd.to_datetime(sentiment["Datetime"], utc=True)
        sentiment = sentiment.set_index("Datetime", drop=True)
        return sentiment

    else:
        raise FileNotFoundError(f"There is no sentiment data associated to {symbol}.")
