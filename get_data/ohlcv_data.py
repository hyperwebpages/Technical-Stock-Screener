from datetime import datetime
from pathlib import Path

import pandas as pd
import pytz
import yfinance as yf

PATH_TO_DATASETS = Path("../datasets/daily")
FORMAT = "%d-%m-%Y"
"""Expected datetime format"""


def fetch_klines(
    symbol: str,
    beginning_date: datetime,
    ending_date: datetime,
    interval: str = "1d",
    **kwargs
) -> pd.DataFrame:
    """Retrieve klines thanks to the Yahoo Finance API.

    Args:
        symbol (str): ticker to download eg `AAPL`
        beginning_date (datetime): open time
        ending_date (datetime): close time
        interval (str): interval of klines, eg `6h`. Defaults to `1d`.

    Returns:
        pd.DataFrame: dataframe containing the klines fetched online.
    """
    klines = yf.download(
        tickers=symbol,
        start=beginning_date,
        end=ending_date,
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
    beginning_date: datetime,
    ending_date: datetime,
    interval: str = "1d",
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
            interval,
            beginning_date.strftime(FORMAT),
            ending_date.strftime(FORMAT),
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
    ending_date: datetime,
    interval: str = "1d",
    directory: Path = PATH_TO_DATASETS,
    **kwargs
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
    klines = fetch_klines(
        symbol,
        beginning_date,
        ending_date,
        interval,
    )
    filename = save_klines(
        klines,
        symbol,
        beginning_date,
        ending_date,
        interval,
        directory,
    )
    return filename


def select_klines_from_file(
    beginning_date: datetime, ending_date: datetime, filename: str, **kwargs
) -> pd.DataFrame:
    """
    Selects klines from a csv file. These klines open at `beginning_date` and close at `ending_date`.
    Args:
        beginning_date (datetime): open time
        ending_date (datetime): close time
        filename (str): filename of the csv file to open
    Returns:
        pd.DataFrame: dataframe containing klines
    """
    klines = pd.read_csv(filename)
    klines = klines.rename(columns={klines.columns[0]: "Datetime"})
    klines.loc[:, "Datetime"] = pd.to_datetime(klines["Datetime"], utc=True)
    klines = klines.set_index("Datetime", drop=True)
    klines = klines.loc[beginning_date:ending_date]
    return klines


def download_klines(
    symbol: str,
    beginning_date: datetime,
    ending_date: datetime,
    interval: str = "1d",
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
    p = Path(directory).glob("*.csv")
    files = [x for x in p if x.is_file()]
    filenames = [x.stem.split("_") for x in files]
    df_files = pd.DataFrame(
        filenames, columns=["symbol", "interval", "start_date", "end_date"]
    )
    df_files.loc[:, ["start_date", "end_date"]] = df_files[
        ["start_date", "end_date"]
    ].apply(lambda x: pd.to_datetime(x, format=FORMAT).dt.tz_localize("UTC"))

    beginning_date = beginning_date.replace(tzinfo=pytz.UTC)
    ending_date = datetime(ending_date.year, ending_date.month, ending_date.day)
    if force_download:
        ending_date = datetime.now()
    ending_date = ending_date.replace(tzinfo=pytz.UTC)

    symbol_to_string = "-".join(symbol) if isinstance(symbol, list) else symbol
    perfect_file = df_files[
        (df_files["symbol"] == symbol_to_string)
        & (df_files["interval"] == interval)
        & (df_files["start_date"] <= beginning_date)
        & (df_files["end_date"] >= ending_date)
    ]
    useless_file = df_files[
        (df_files["symbol"] == symbol_to_string)
        & (df_files["interval"] == interval)
        & (
            (df_files["start_date"] > beginning_date)
            | (df_files["end_date"] < ending_date)
        )
    ]

    if not perfect_file.empty:
        filename = files[perfect_file.index[0]]
        return select_klines_from_file(
            beginning_date,
            ending_date,
            filename,
        )

    for index in useless_file.index:
        filename = files[index]
        Path.unlink(filename)

    new_filename = fetch_and_save_klines(
        symbol,
        beginning_date,
        ending_date,
        interval,
        directory,
    )
    return select_klines_from_file(
        beginning_date,
        ending_date,
        new_filename,
    )
