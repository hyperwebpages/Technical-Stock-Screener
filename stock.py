from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

from market_data import download_klines


class Stock:
    symbol: str
    start_date: datetime = datetime(2010, 1, 1)
    end_date: datetime = datetime.today()
    global_score: float = 0
    detailed_score: Dict[str, int] = field(default_factory=lambda: ({}))
    interval: str = "1d"

    def __post_init__(self):
        try:
            self.klines = download_klines(
                self.symbol,
                self.start_date,
                self.end_date,
                "1d",
                Path("datasets/daily"),
            )
        except ValueError as e:
            self.klines = []

    def add_indicator(self, indicator):
        self.klines = indicator.apply_indicator(self.klines)

        if indicator.flag_column is not None:
            if np.abs(self.klines[indicator.flag_column].iloc[-1]) > 0:
                self.detailed_score[str(indicator)] = self.klines[
                    indicator.flag_column
                ].iloc[-1]
            self.global_score += self.klines[indicator.flag_column].iloc[-1]


def get_all_symbols_df(path_to_symbols: Path = Path("datasets/symbols.csv")):
    return pd.read_csv(path_to_symbols)
