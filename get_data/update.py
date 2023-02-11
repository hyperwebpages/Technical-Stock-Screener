from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import bs4 as bs
import nltk
import pandas as pd
import pytz
import requests
import traceback
import toml
from tqdm import tqdm

from get_data.financial import fetch_and_save_financials
from get_data.ohlcv import fetch_and_save_klines
from get_data.sentiment import fetch_and_save_sentiment


def sync_symbols(path_to_stock_symbols: Path):
    """Sync symbols with active symbols of S&P500, while keeping the stocks manually set

    Args:
        path_to_stock_symbols (Path): Path to the DataFrame of symbols
    """
    original_symbols = pd.read_csv(path_to_stock_symbols)
    force_watch_symbols = original_symbols[original_symbols["force_watch"]]

    resp = requests.get("http://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
    soup = bs.BeautifulSoup(resp.text, "lxml")
    table = soup.find("table", {"class": "wikitable sortable"})

    current_symbols = []
    for row in table.findAll("tr")[1:]:
        ticker = row.findAll("td")[0].text
        current_symbols.append(ticker.replace("\n", ""))
    current_symbols = sorted(current_symbols)

    no_force_watch_symbols = pd.DataFrame(current_symbols, columns=["symbol"])
    no_force_watch_symbols["force_watch"] = False
    no_force_watch_symbols["from_date"] = datetime.today().strftime("%Y-%m-%d")

    new_symbols = pd.concat([force_watch_symbols, no_force_watch_symbols], axis=0).sort_values(
        by="symbol", axis=0
    )
    new_symbols.loc[new_symbols["symbol"].isin(original_symbols["symbol"]), "from_date"] = original_symbols["from_date"]
    new_symbols.to_csv(path_to_stock_symbols, index=False)


def update_data(
    index_symbols: pd.DataFrame,
    stock_symbols: pd.DataFrame,
    path_to_datasets: Path,
) -> Tuple[List[str], List[str], List[str]]:
    """Update the `path_to_datasets` folder by fetching the financials, sentiment score and klines of the assets

    Args:
        index_symbols (pd.DataFrame): list of indices to update
        stock_symbols (pd.DataFrame): list of stocks to update
        path_to_datasets (Path): path of the datasets to update

    Returns:
        Tuple[List[str], List[str], List[str]]: tuple made of
            * list of symbols having problems when fetching their klines
            * list of symbols having problems when fetching their sentiments
            * list of symbols having problems when fetching their financials
    """
    nltk.downloader.download("vader_lexicon")

    problematic_ohlcv = []
    problematic_sentiment = []
    problematic_financials = []

    pbar = tqdm(total=len(index_symbols) + 3 * len(stock_symbols))

    for _, row in stock_symbols.iterrows():
        symbol = row["symbol"]
        from_date = row["from_date"]
        try:
            financials = fetch_and_save_financials(
                symbol=symbol,
                directory=path_to_datasets / "financial",
            )
        except Exception as e:
            print(f"Problem fetching {symbol} financials")
            print(traceback.format_exc())
            problematic_financials.append(symbol)
        pbar.update(1)
        # try:
        #     sentiments = fetch_and_save_sentiment(
        #         symbol=symbol,
        #         beginning_date=datetime(2021, 1, 1),
        #         interval="1d",
        #         directory=path_to_datasets / "sentiment",
        #     )
        # except Exception as e:
        #     print(f"Problem fetching {symbol} sentiment")
        #     print(traceback.format_exc())
        #     problematic_sentiment.append(symbol)
        pbar.update(1)
        # try:
        #     klines = fetch_and_save_klines(
        #         symbol=symbol,
        #         beginning_date=from_date,
        #         interval="1d",
        #         directory=path_to_datasets / "ohlcv",
        #     )
        # except Exception as e:
        #     print(f"Problem fetching {symbol} klines")
        #     print(traceback.format_exc())
        #     problematic_ohlcv.append(symbol)
        pbar.update(1)
    for _, row in index_symbols.iterrows():
        symbol = row["symbol"]
        from_date = row["from_date"]
        try:
            klines = fetch_and_save_klines(
                symbol=symbol,
                beginning_date=datetime(2021, 1, 1),
                interval="1d",
                directory=path_to_datasets / "ohlcv",
            )
        except Exception as e:
            print(f"Problem fetching {symbol} klines")
            print(traceback.format_exc())
            problematic_ohlcv.append(symbol)
        pbar.update(1)

    pbar.close()
    return problematic_ohlcv, problematic_sentiment, problematic_financials


if __name__ == "__main__":
    current_datetime_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
    current_datetime_nyc = current_datetime_utc.astimezone(pytz.timezone("US/Eastern"))

    print("Current UTC time:", current_datetime_utc)
    print("Current NYC / Market time:", current_datetime_nyc)
    config = toml.load(Path("config.toml"))

    path_to_index_symbols = Path(config["data_access"]["path_to_index_symbols"])
    path_to_stock_symbols = Path(config["data_access"]["path_to_stock_symbols"])
    path_to_datasets = Path(config["data_access"]["path_to_datasets"])

    # sync active symbols
    sync_symbols(path_to_stock_symbols)

    index_symbols = pd.read_csv(path_to_index_symbols)
    index_symbols["from_date"] = pd.to_datetime(index_symbols["from_date"])
    stock_symbols = pd.read_csv(path_to_stock_symbols)
    stock_symbols["from_date"] = pd.to_datetime(stock_symbols["from_date"])
    # update assets
    problematic_ohlcv, problematic_sentiment, problematic_financials = update_data(
        index_symbols,
        stock_symbols,
        path_to_datasets,
    )
