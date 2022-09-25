from dataclasses import dataclass
from typing import Union

import numpy as np
import pandas as pd
import streamlit as st
from ta import momentum, trend

from models.asset import Index, Stock


def beautiful_str(s: str) -> str:
    """Transform ugly strings in beautiful strings.
    For instance, `love_tacos` is transformed into `Love tacos`.

    Args:
        s (str): original string

    Returns:
        str: beautiful string
    """
    s = list(str(s))
    s = [" " if c == "_" else c for c in s]
    s[0] = s[0].upper()
    return "".join(s)


@dataclass
class Indicator:
    flag_column: str = None

    def __str__(self) -> str:
        return type(self).__name__

    def checkbox(
        self,
    ):
        self.on = st.checkbox(type(self).__name__)

    def text_input(self):
        for param in type(self).__dataclass_fields__.keys():
            if param != "flag_column" and param[0] != "_":
                setattr(
                    self,
                    param,
                    st.text_input(
                        label=beautiful_str(param),
                        value=getattr(self, param),
                        key=str(type(self).__name__) + str(param),
                    ),
                )


@dataclass
class RSI(Indicator):
    period: int = 14
    overbought: float = 70
    oversold: float = 30

    flag_column: str = "RSIflag"

    def apply_indicator(self, asset: Union[Index, Stock]) -> pd.DataFrame:
        asset.klines["RSI"] = momentum.RSIIndicator(
            asset.klines["Close"], int(self.period)
        ).rsi()
        asset.klines["RSIflag"] = 0
        condSold = asset.klines["RSI"] < float(self.oversold)
        asset.klines["RSIflag"] = np.where(condSold, 1, asset.klines["RSIflag"])
        condBought = asset.klines["RSI"] > float(self.overbought)
        asset.klines["RSIflag"] = np.where(condBought, -1, asset.klines["RSIflag"])
        return asset.klines


@dataclass
class StochRSI(Indicator):
    period: int = 14
    k: int = 3
    d: int = 3
    buy_level: float = 20
    sell_level: float = 80

    flag_column: str = "StochRSIflag"

    def apply_indicator(self, asset: Union[Index, Stock]) -> pd.DataFrame:
        stoch_rsi_ind = momentum.StochRSIIndicator(
            asset.klines["Close"],
            int(self.period),
            smooth1=int(self.k),
            smooth2=int(self.d),
        )
        asset.klines["fastk"], asset.klines["fastd"] = (
            stoch_rsi_ind.stochrsi_k(),
            stoch_rsi_ind.stochrsi_d(),
        )
        asset.klines["StochRSIflag"] = 0
        ##Stoch conditions to test for
        ### k val < 20 and crossing above d val => Buy pressure
        StochBuyCondition = (
            (asset.klines["fastk"] < float(self.buy_level))
            & (asset.klines["fastk"].shift(1) < asset.klines["fastd"].shift(1))
            & (asset.klines["fastk"] >= asset.klines["fastd"])
        )
        asset.klines["StochRSIflag"] = np.where(
            StochBuyCondition, 1, asset.klines["StochRSIflag"]
        )

        ### k val > 80 and crossing above d val => Buy pressure
        StochSellCondition = (
            (asset.klines["fastk"] > float(self.sell_level))
            & (asset.klines["fastk"].shift(1) > asset.klines["fastd"].shift(1))
            & (asset.klines["fastk"] <= asset.klines["fastd"])
        )
        asset.klines["StochRSIflag"] = np.where(
            StochSellCondition, -1, asset.klines["StochRSIflag"]
        )
        return asset.klines


@dataclass
class EMA(Indicator):
    fast_period: int = 20
    medium_period: int = 50
    slow_period: int = 200

    def apply_indicator(self, asset: Union[Index, Stock]) -> pd.DataFrame:
        asset.klines["EMA_fast"] = trend.EMAIndicator(
            asset.klines["Close"], int(self.fast_period)
        ).ema_indicator()

        asset.klines["EMA_medium"] = trend.EMAIndicator(
            asset.klines["Close"], int(self.medium_period)
        ).ema_indicator()
        asset.klines["EMA_slow"] = trend.EMAIndicator(
            asset.klines["Close"], int(self.slow_period)
        ).ema_indicator()
        return asset.klines


@dataclass
class MACD(Indicator):
    fast_period: int = 12
    slow_period: int = 26
    signal_period: int = 9

    ema_fast_period: int = 20
    ema_medium_period: int = 50
    ema_slow_period: int = 200

    flag_column: str = "MACDflag"

    def apply_indicator(self, asset: Union[Index, Stock]) -> pd.DataFrame:
        ema = EMA(
            fast_period=self.ema_fast_period,
            medium_period=self.ema_medium_period,
            slow_period=self.ema_slow_period,
        )
        asset.klines = ema.apply_indicator(asset)

        macd_indicator = trend.MACD(
            asset.klines["Close"],
            window_slow=int(self.slow_period),
            window_fast=int(self.fast_period),
            window_sign=int(self.signal_period),
        )
        asset.klines["macd"], asset.klines["macdsignal"], asset.klines["macdhist"] = (
            macd_indicator.macd(),
            macd_indicator.macd_signal(),
            macd_indicator.macd_diff(),
        )
        asset.klines["MACDflag"] = 0

        MacdBuyCondition = (
            (asset.klines["Close"] > asset.klines["EMA_medium"])
            & (asset.klines["macd"] < 0)
            & (asset.klines["macd"].shift(1) < asset.klines["macdsignal"].shift(1))
            & (asset.klines["macd"] >= asset.klines["macdsignal"])
        )
        asset.klines["MACDflag"] = np.where(
            MacdBuyCondition, 1, asset.klines["MACDflag"]
        )

        ##MACD Condition to test for Strong Sell
        MacdSellCondition = (
            (asset.klines["Close"] < asset.klines["EMA_medium"])
            & (asset.klines["macd"] > 0)
            & (asset.klines["macd"].shift(1) > asset.klines["macdsignal"].shift(1))
            & (asset.klines["macd"] <= asset.klines["macdsignal"])
        )
        asset.klines["lag"] = np.where(MacdSellCondition, -1, asset.klines["MACDflag"])

        return asset.klines


@dataclass
class CipherB(Indicator):
    n1: int = 10
    n2: int = 21
    over_bought_level_1: int = 60
    over_bought_level_2: int = 53
    over_sold_level_1: int = -60
    over_sold_level_2: int = -53
    wt_smoothing: int = 4

    flag_column: str = "CipherFlag"

    def apply_indicator(self, asset: Union[Index, Stock]) -> pd.DataFrame:
        asset.klines["ap"] = (
            asset.klines["High"] + asset.klines["Low"] + asset.klines["Close"]
        ) / 3
        esa = trend.EMAIndicator(asset.klines["ap"], int(self.n1)).ema_indicator()
        asset.klines["esa"] = esa
        asset.klines["dval"] = abs(asset.klines["ap"] - asset.klines["esa"])
        asset.klines["d"] = trend.EMAIndicator(
            asset.klines["dval"], int(self.n1)
        ).ema_indicator()

        asset.klines["ci"] = (asset.klines["ap"] - asset.klines["esa"]) / (
            0.015 * asset.klines["d"]
        )
        asset.klines["tci"] = trend.EMAIndicator(
            asset.klines["ci"], int(self.n2)
        ).ema_indicator()

        asset.klines["wt1"] = asset.klines["tci"]
        asset.klines["wt2"] = trend.SMAIndicator(
            asset.klines["wt1"], int(self.wt_smoothing)
        ).sma_indicator()
        asset.klines["CipherFlag"] = 0

        CipherBullCond = (
            asset.klines["wt1"].shift(1) < asset.klines["wt2"].shift(1)
        ) & (asset.klines["wt1"] >= asset.klines["wt2"])
        asset.klines["CipherFlag"] = np.where(
            CipherBullCond, 1, asset.klines["CipherFlag"]
        )

        CipherSellCond = (
            asset.klines["wt1"].shift(1) > asset.klines["wt2"].shift(1)
        ) & (asset.klines["wt1"] <= asset.klines["wt2"])
        asset.klines["CipherFlag"] = np.where(
            CipherSellCond, -1, asset.klines["CipherFlag"]
        )
        return asset.klines


@dataclass
class SentimentScore(Indicator):
    above_threshold: float = 0.1
    below_threshold: float = -0.1

    flag_column: str = "SentimentFlag"

    def apply_indicator(self, asset: Union[Index, Stock]) -> pd.DataFrame:
        if not isinstance(asset, Stock):
            asset.klines["score"] = 0

        asset.klines[self.flag_column] = 0
        above_score = asset.klines["score"] >= float(self.above_threshold)
        below_score = asset.klines["score"] <= float(self.below_threshold)

        asset.klines[self.flag_column] = np.where(
            above_score, 1, asset.klines[self.flag_column]
        )
        asset.klines[self.flag_column] = np.where(
            below_score, -1, asset.klines[self.flag_column]
        )

        return asset.klines
