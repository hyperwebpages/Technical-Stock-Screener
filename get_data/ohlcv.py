from datetime import datetime
from pathlib import Path

import pandas as pd
import pytz
import yfinance as yf

PATH_TO_DATASETS = Path("../datasets/daily")
FORMAT = "%d-%m-%Y"
"""Expected datetime format"""
INDICES_TRANSLATIONS = {
    "BTC": "BTC-USD",
    "DOW": "^DJI",
    "EUR": "EURUSD=X",
    "SP500": "^GSPC",
    "Nasdaq": "^NDX",
}


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
    klines = yf.download(
        tickers=symbol,
        start=beginning_date,
        end=datetime.now(),
        interval=interval,
        progress=False,
        show_errors=True,
    )
    try:
        klines.index = klines.index.tz_convert(pytz.UTC).rename("Datetime")
    except TypeError as e:
        klines.index = klines.index.tz_localize(pytz.UTC).rename("Datetime")
    except AttributeError as e:
        pass
    klines = klines.drop(
        labels=["Adj Close"],
        axis=1,
    )
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
