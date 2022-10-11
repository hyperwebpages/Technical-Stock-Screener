import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytz
import requests
import yfinance as yf
from requests.adapters import HTTPAdapter, Retry

FORMAT = "%d-%m-%Y"
"""Expected datetime format"""
INDICES_TRANSLATIONS = {
    "BTC": "BTCUSD",
    "Dow": "DOW",
    "SP500": "SPY",
    "Nasdaq": "NDAQ",
}


def get_asset_class(symbol):
    api = os.environ.get("ALPACA_API")
    api_secret = os.environ.get("ALPACA_API_SECRET")
    headers = {"Apca-Api-Key-Id": api, "Apca-Api-Secret-Key": api_secret}
    url = f"https://broker-api.alpaca.markets/v1/assets/{symbol}"
    request = requests.get(url, headers=headers).json()
    return request["class"], request["symbol"]


def fetch_klines(
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
    symbol = INDICES_TRANSLATIONS.get(symbol, symbol)
    interval = {"1d": "1Day"}[interval]
    api = os.environ.get("ALPACA_API")
    api_secret = os.environ.get("ALPACA_API_SECRET")
    headers = {"Apca-Api-Key-Id": api, "Apca-Api-Secret-Key": api_secret}

    querystring = {}
    symbol_class, symbol = get_asset_class(symbol)
    if symbol_class in ["us_equity"]:
        url = f"https://data.alpaca.markets/v2/stocks/{symbol}/bars"
    if symbol_class in ["crypto"]:
        url = f"https://data.alpaca.markets/v1beta2/crypto/bars"
        querystring["symbols"] = symbol

    # Alpaca prevents from retrieving the last 15min
    ending_date = datetime.now(timezone.utc) - timedelta(minutes=16)
    beginning_date = pytz.utc.localize(beginning_date)
    klines = []
    while ending_date.day > (beginning_date + timedelta(days=3)).day:
        querystring.update(
            {
                "start": beginning_date.isoformat(),
                "end": ending_date.isoformat(),
                "timeframe": interval,
                "limit": 10000,
            }
        )

        request_session = requests.Session()
        retries = Retry(total=7, backoff_factor=2, status_forcelist=[429])
        request_session.mount("https://", HTTPAdapter(max_retries=retries))
        request = request_session.get(url, headers=headers, params=querystring).json()

        if symbol_class in ["us_equity"]:
            bars = request["bars"]
        if symbol_class in ["crypto"]:
            bars = request["bars"][symbol]

        try:
            if len(request["bars"]) == 0:
                break

            _klines = pd.DataFrame.from_dict(bars).drop(
                labels=[
                    "n",
                ],
                axis=1,
            )
            _klines = _klines.rename(
                columns={
                    "c": "Close",
                    "h": "High",
                    "l": "Low",
                    "o": "Open",
                    "t": "Datetime",
                    "v": "Volume",
                    "vw": "Weighted Volume",
                }
            )
            _klines = _klines.set_index("Datetime", drop=True)
            _klines.index = pd.to_datetime(_klines.index).tz_convert(pytz.UTC)
            klines.append(_klines)

            ending_date = _klines.index[0]
        except Exception as e:
            print(e)
            break

    klines = pd.concat(klines)
    klines = klines.astype("float64")
    return klines


def save_klines(
    data: pd.DataFrame,
    symbol: str,
    interval: str,
    directory: Path,
    **kwargs,
) -> str:
    """Save klines data in `directory`.

    Args:
        data (pd.DataFrame): data/ klines to save
        symbol (str): ticker to download eg `AAPL`
        interval (str): interval of klines, eg `6h`.
        directory (Path): directory to save the klines.

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


def fetch_and_save_klines(
    symbol: str,
    beginning_date: datetime,
    interval: str,
    directory: Path,
    **kwargs,
) -> str:
    """
    Downloads klines of `symbol` from `beginning_date` to `ending_date`, at interval `interval`
    and saves them in `directory`.
    Args:
        symbol (str): ticker to download eg `AAPL`
        beginning_date (datetime): open time
        ending_date (datetime): close time
        interval (str): interval of klines, eg `6h`.
        directory (Path): directory to save the klines.
    Returns:
        str: filename of csv file containing the klines
    """
    klines = fetch_klines(
        symbol,
        beginning_date,
        interval,
    )
    filename = save_klines(
        klines,
        symbol,
        interval,
        directory,
    )
    return filename


def select_klines(
    symbol: str, interval: str, directory: Path, **kwargs
) -> pd.DataFrame:

    """
    Selects klines of `symbol` from `beginning_date` to `to_date`, at interval `ending_date`.
    If the klines have already been downloaded, it fetches it in the csv file, unless `force_download=True`.
    Otherwise, it downloads the data from the Yahoo Finance API.
    Args:
        symbol (str): ticker to download eg `AAPL`
        beginning_date (datetime): open time
        ending_date (datetime): close time
        interval (str): interval of klines, eg `6h`.
        force_download (bool): whether to re-download the financials, even it they are already located in `directory`.
        directory (Path): directory to save the klines.
    Returns:
        pd.DataFrame: dataframe containing klines
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
        klines = pd.read_csv(filename)
        klines = klines.rename(columns={klines.columns[0]: "Datetime"})
        klines.loc[:, "Datetime"] = pd.to_datetime(klines["Datetime"], utc=True)
        klines = klines.set_index("Datetime", drop=True)
        return klines

    else:
        raise FileNotFoundError(f"There is no OHLCV data associated to {symbol}.")
