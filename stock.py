from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from market_data import download_klines


@dataclass
class Stock:
    symbol: str
    start_date: datetime = datetime(2010, 1, 1)
    end_date: datetime = datetime.today()
    interval: str = "1d"

    def __post_init__(self):
        self.klines = download_klines(
            self.symbol,
            self.start_date,
            self.end_date,
            "1d",
            Path("datasets/daily"),
        )


def get_all_symbols_df(path_to_symbols: Path = Path("datasets/symbols.csv")):
    return pd.read_csv(path_to_symbols)
