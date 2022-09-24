from dataclasses import dataclass

import numpy as np
import pandas as pd
import streamlit as st
import talib
from ta.momentum import RSIIndicator, StochRSIIndicator
from ta.trend import MACD, EMAIndicator, SMAIndicator


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
        for param, _ in type(self).__dataclass_fields__.items():
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

    def apply_indicator(self, ohlc: pd.DataFrame) -> pd.DataFrame:
        ohlc["RSI"] = RSIIndicator(ohlc["Close"], int(self.period)).rsi()
        ohlc["RSIflag"] = 0
        condSold = ohlc["RSI"] < float(self.oversold)
        ohlc["RSIflag"] = np.where(condSold, 1, ohlc["RSIflag"])
        condBought = ohlc["RSI"] > float(self.overbought)
        ohlc["RSIflag"] = np.where(condBought, -1, ohlc["RSIflag"])
        return ohlc


@dataclass
class StochRSI(Indicator):
    period: int = 14
    k: int = 3
    d: int = 3
    buy_level: float = 20
    sell_level: float = 80

    flag_column: str = "StochRSIflag"

    def apply_indicator(self, ohlc: pd.DataFrame) -> pd.DataFrame:
        stoch_rsi_ind = StochRSIIndicator(
            ohlc["Close"],
            int(self.period),
            smooth1=float(self.k),
            smooth2=float(self.d),
        )
        ohlc["fastk"], ohlc["fastd"] = (
            stoch_rsi_ind.stochrsi_k(),
            stoch_rsi_ind.stochrsi_d(),
        )
        ohlc["StochRSIflag"] = 0
        ##Stoch conditions to test for
        ### k val < 20 and crossing above d val => Buy pressure
        StochBuyCondition = (
            (ohlc["fastk"] < float(self.buy_level))
            & (ohlc["fastk"].shift(1) < ohlc["fastd"].shift(1))
            & (ohlc["fastk"] >= ohlc["fastd"])
        )
        ohlc["StochRSIflag"] = np.where(StochBuyCondition, 1, ohlc["StochRSIflag"])

        ### k val > 80 and crossing above d val => Buy pressure
        StochSellCondition = (
            (ohlc["fastk"] > float(self.sell_level))
            & (ohlc["fastk"].shift(1) > ohlc["fastd"].shift(1))
            & (ohlc["fastk"] <= ohlc["fastd"])
        )
        ohlc["StochRSIflag"] = np.where(StochSellCondition, -1, ohlc["StochRSIflag"])
        return ohlc


@dataclass
class EMA(Indicator):
    fast_period: int = 20
    medium_period: int = 50
    slow_period: int = 200

    def apply_indicator(self, ohlc: pd.DataFrame) -> pd.DataFrame:
        ohlc["EMA_fast"] = EMAIndicator(
            ohlc["Close"], int(self.fast_period)
        ).ema_indicator()

        ohlc["EMA_medium"] = EMAIndicator(
            ohlc["Close"], int(self.medium_period)
        ).ema_indicator()
        ohlc["EMA_slow"] = EMAIndicator(
            ohlc["Close"], int(self.slow_period)
        ).ema_indicator()
        return ohlc


@dataclass
class MACD(Indicator):
    fast_period: int = 12
    slow_period: int = 26
    signal_period: int = 9

    ema_fast_period: int = 20
    ema_medium_period: int = 50
    ema_slow_period: int = 200

    flag_column: str = "MACohlclag"

    def apply_indicator(self, ohlc: pd.DataFrame) -> pd.DataFrame:
        ema = EMA(
            fast_period=self.ema_fast_period,
            medium_period=self.ema_medium_period,
            slow_period=self.ema_slow_period,
        )
        ohlc = ema.apply_indicator(ohlc)

        macd_indicator = MACD(
            ohlc["Close"],
            window_slow=int(self.slow_period),
            window_fast=int(self.fast_period),
            window_sign=int(self.signal_period),
        )
        ohlc["macd"], ohlc["macdsignal"], ohlc["macdhist"] = (
            macd_indicator.macd(),
            macd_indicator.macd_signal(),
            macd_indicator.macd_diff(),
        )
        ohlc["MACohlclag"] = 0

        MacdBuyCondition = (
            (ohlc["Close"] > ohlc["EMA_medium"])
            & (ohlc["macd"] < 0)
            & (ohlc["macd"].shift(1) < ohlc["macdsignal"].shift(1))
            & (ohlc["macd"] >= ohlc["macdsignal"])
        )
        ohlc["MACohlclag"] = np.where(MacdBuyCondition, 1, ohlc["MACohlclag"])

        ##MACD Condition to test for Strong Sell
        MacdSellCondition = (
            (ohlc["Close"] < ohlc["EMA_medium"])
            & (ohlc["macd"] > 0)
            & (ohlc["macd"].shift(1) > ohlc["macdsignal"].shift(1))
            & (ohlc["macd"] <= ohlc["macdsignal"])
        )
        ohlc["MACohlclag"] = np.where(MacdSellCondition, -1, ohlc["MACohlclag"])

        return ohlc


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

    def apply_indicator(self, ohlc: pd.DataFrame) -> pd.DataFrame:
        ohlc["ap"] = (ohlc["High"] + ohlc["Low"] + ohlc["Close"]) / 3
        esa = EMAIndicator(ohlc["ap"], int(self.n1)).ema_indicator()
        ohlc["esa"] = esa
        ohlc["dval"] = abs(ohlc["ap"] - ohlc["esa"])
        ohlc["d"] = EMAIndicator(ohlc["dval"], int(self.n1)).ema_indicator()

        ohlc["ci"] = (ohlc["ap"] - ohlc["esa"]) / (0.015 * ohlc["d"])
        ohlc["tci"] = EMAIndicator(ohlc["ci"], int(self.n2)).ema_indicator()

        ohlc["wt1"] = ohlc["tci"]
        ohlc["wt2"] = SMAIndicator(ohlc["wt1"], int(self.wt_smoothing)).sma_indicator()
        ohlc["CipherFlag"] = 0

        CipherBullCond = (ohlc["wt1"].shift(1) < ohlc["wt2"].shift(1)) & (
            ohlc["wt1"] >= ohlc["wt2"]
        )
        ohlc["CipherFlag"] = np.where(CipherBullCond, 1, ohlc["CipherFlag"])

        CipherSellCond = (ohlc["wt1"].shift(1) > ohlc["wt2"].shift(1)) & (
            ohlc["wt1"] <= ohlc["wt2"]
        )
        ohlc["CipherFlag"] = np.where(CipherSellCond, -1, ohlc["CipherFlag"])
        return ohlc
