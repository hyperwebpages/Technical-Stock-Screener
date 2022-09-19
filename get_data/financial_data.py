import json
from datetime import datetime
from pathlib import Path
from pstats import Stats

import pandas as pd
import pytz
import yfinance as yf

PATH_TO_DATASETS = Path("datasets/daily/financials")
FORMAT = "%d-%m-%Y"
"""Expected datetime format"""


def fetch_financials(symbol: str, **kwargs) -> pd.DataFrame:
    """Retrieve klines thanks to the Yahoo Finance API.

    Args:
        symbol (str): ticker to download eg `AAPL`
        beginning_date (datetime): open time
        ending_date (datetime): close time
        interval (str): interval of klines, eg `6h`. Defaults to `1d`.

    Returns:
        pd.DataFrame: dataframe containing the klines fetched online.
    """
    stats = yf.Ticker(symbol).stats()
    financial_keys = [
        ["price", "longName"],
        ["price", "shortName"],
        ["summaryProfile", "industry"],
        ["price", "marketCap"],
        ["financialData", "totalRevenue"],
        ["financialData", "targetMeanPrice"],
        ["price", "regularMarketDayLow"],
        ["price", "regularMarketDayHigh"],
        ["defaultKeyStatistics", "52WeekChange"],
        ["price", "averageDailyVolume10Day"],
        ["price", "regularMarketChangePercent"],
    ]
    return {keys[1]: stats[keys[0]][keys[1]] for keys in financial_keys}


def save_financials(
    data: dict,
    symbol: str,
    date: datetime,
    directory: Path = PATH_TO_DATASETS,
    **kwargs
) -> str:
    """_summary_

    Args:
        data (pd.DataFrame): data/ klines to save
        symbol (str): ticker to download eg `AAPL`
        beginning_date (datetime): open time
        ending_date (datetime): close time
        interval (str): interval of klines, eg `6h`. Defaults to `1d`.
        directory (Path): directory to save the klines. Defaults to `PATH_TO_DATASETS`.

    Raises:
        ValueError: if data is an empty dataframe.

    Returns:
        str: filename containing the data
    """
    filename = Path(directory) / "_".join(
        [
            symbol,
            date.strftime(FORMAT),
        ]
    )
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    filename = str(filename) + ".json"
    if len(data) > 0:
        with open(filename, "w") as outfile:
            json.dump(data, outfile)
    else:
        raise ValueError("Data is empty")
    return filename


def fetch_and_save_financials(
    symbol: str, date: datetime, directory: Path = PATH_TO_DATASETS, **kwargs
) -> str:
    """
    Downloads klines of `symbol` from `beginning_date` to `ending_date`, at interval `interval`.
    Args:
        symbol (str): ticker to download eg `AAPL`
        beginning_date (datetime): open time
        ending_date (datetime): close time
        interval (str): interval of klines, eg `6h`. Defaults to `1d`.
        directory (Path): directory to save the klines. Defaults to `PATH_TO_DATASETS`.
    Returns:
        str: filename of csv file containing the klines
    """
    klines = fetch_financials(
        symbol,
    )
    filename = save_financials(
        klines,
        symbol,
        date,
        directory,
    )
    return filename


def download_financials(
    symbol: str,
    date: datetime,
    force_download: bool = False,
    directory: Path = PATH_TO_DATASETS,
    **kwargs
) -> pd.DataFrame:

    """
    Selects klines of `symbol` from `beginning_date` to `to_date`, at interval `ending_date`.
    If the klines have already been downloaded, it fetches it in the csv file.
    Otherwise, it downloads the data from the Yahoo Finance API.
    Args:
        symbol (str): ticker to download eg `AAPL`
        beginning_date (datetime): open time
        ending_date (datetime): close time
        interval (str): interval of klines, eg `6h`. Defaults to `1d`.
        directory (Path): directory to save the klines. Defaults to `PATH_TO_DATASETS`.
    Returns:
        pd.DataFrame: dataframe containing klines
    """
    p = Path(directory).glob("*.json")
    files = [x for x in p if x.is_file()]
    filenames = [x.stem.split("_") for x in files]
    df_files = pd.DataFrame(filenames, columns=["symbol", "date"])
    df_files.loc[:, "date"] = df_files["date"].apply(
        lambda x: pd.to_datetime(x, format=FORMAT).tz_localize("UTC")
    )

    ending_date = datetime(date.year, date.month, date.day)
    if force_download:
        ending_date = datetime.now()
    ending_date = ending_date.replace(tzinfo=pytz.UTC)

    symbol_to_string = "-".join(symbol) if isinstance(symbol, list) else symbol

    perfect_file = df_files[
        (df_files["symbol"] == symbol_to_string) & (df_files["date"] >= ending_date)
    ]
    useless_file = df_files[
        (df_files["symbol"] == symbol_to_string) & (df_files["date"] < ending_date)
    ]
    if not perfect_file.empty:
        filename = files[perfect_file.index[0]]
        with open(filename) as financial_file:
            return json.load(financial_file)

    for index in useless_file.index:
        filename = files[index]
        Path.unlink(filename)

    new_filename = fetch_and_save_financials(
        symbol,
        ending_date,
        directory,
    )
    with open(new_filename) as financial_file:
        return json.load(financial_file)
