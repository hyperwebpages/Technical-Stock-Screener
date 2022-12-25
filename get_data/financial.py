import json
from datetime import datetime
from pathlib import Path
from pstats import Stats

import pandas as pd
import pytz
import yfinance as yf

FORMAT = "%d-%m-%Y"
"""Expected datetime format"""


def fetch_financials(symbol: str, **kwargs) -> dict:
    """Retrieve financials thanks to the Yahoo Finance API.

    Args:
        symbol (str): ticker to download eg `AAPL`

    Returns:
        dict: dict containing selected financials.
    """
    stats = yf.Ticker(symbol.replace(".", "-")).stats()
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
    financials = {}
    for keys in financial_keys:
        item = stats.get(keys[0], {})
        if item == None:
            item = {}
        financials[keys[1]] = item.get(keys[1], None)
    return financials


def save_financials(data: dict, symbol: str, directory: Path, **kwargs) -> str:
    """Save financials data in `directory`.

    Args:
        data (dict): data to save
        symbol (str): ticker to download eg `AAPL`
        date (datetime): date the financials were retrieved
        directory (Path): directory to save the klines.

    Raises:
        ValueError: if data is an empty dataframe.

    Returns:
        str: filename containing the data
    """
    filename = Path(directory) / symbol
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    filename = str(filename) + ".json"
    if len(data) > 0:
        with open(filename, "w") as outfile:
            json.dump(data, outfile, indent=4)
    else:
        raise ValueError("Data is empty")
    return filename


def fetch_and_save_financials(symbol: str, directory: Path, **kwargs) -> str:
    """
    Downloads financials of `symbol` save them in `directory`.
    Args:
        symbol (str): ticker to download eg `AAPL`
        date (datetime): date the financials were retrieved
        directory (Path): directory to save the klines.
    Returns:
        str: filename of csv file containing the financials
    """
    klines = fetch_financials(
        symbol,
    )
    filename = save_financials(
        klines,
        symbol,
        directory,
    )
    return filename


def select_financials(symbol: str, directory: Path, **kwargs) -> pd.DataFrame:
    """
    Selects the financials of `symbol`.
    If the financials have already been downloaded, it fetches it in the csv file, unless `force_download=True`.
    Otherwise, it downloads the data from the Yahoo Finance API.
    Args:
        symbol (str): ticker to download eg `AAPL`
        date (datetime): date the financials were retrieved
        force_download (bool): whether to re-download the financials, even it they are already located in `directory`.
        directory (Path): directory to save the klines.
    Returns:
        pd.DataFrame: dataframe containing klines
    """
    p = Path(directory).glob("*.json")
    files = [x for x in p if x.is_file()]
    filenames = [x.stem.split("_") for x in files]
    df_files = pd.DataFrame(filenames, columns=["symbol"])

    perfect_file = df_files[(df_files["symbol"] == symbol)]
    if not perfect_file.empty:
        filename = files[perfect_file.index[0]]
        with open(filename) as financial_file:
            return json.load(financial_file)

    else:
        raise FileNotFoundError(f"There is no financials data associated to {symbol}.")
