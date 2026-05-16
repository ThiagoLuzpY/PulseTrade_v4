"""Lightweight technical indicators using pandas/numpy (no TA-Lib dependency)."""
from __future__ import annotations
import pandas as pd
import numpy as np
from typing import List, Dict, Any


def klines_to_df(klines: List[Dict[str, float]]) -> pd.DataFrame:
    df = pd.DataFrame(klines)
    return df


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def bollinger(series: pd.Series, period: int = 20, num_std: float = 2):
    ma = series.rolling(period).mean()
    sd = series.rolling(period).std()
    upper = ma + num_std * sd
    lower = ma - num_std * sd
    return upper, ma, lower


def compute_signal(klines: List[Dict[str, float]]) -> Dict[str, Any] | None:
    """Compute a directional signal score from klines.
    Returns dict with: direction (LONG/SHORT/NEUTRAL), score (0..100), price, atr, rsi, macd_hist,
    ema20, ema50, ema200, breakout_level, volume_ratio.
    """
    if len(klines) < 60:
        return None
    df = klines_to_df(klines)
    close = df["close"]

    ema20 = ema(close, 20)
    ema50 = ema(close, 50)
    ema200 = ema(close, min(200, len(close) - 1))
    rsi_s = rsi(close, 14)
    macd_line, signal_line, macd_hist = macd(close)
    atr_s = atr(df, 14)
    upper_bb, mid_bb, lower_bb = bollinger(close, 20, 2)

    last = -1
    price = float(close.iloc[last])
    rsi_v = float(rsi_s.iloc[last])
    mh = float(macd_hist.iloc[last])
    mh_prev = float(macd_hist.iloc[last - 1])
    e20 = float(ema20.iloc[last])
    e50 = float(ema50.iloc[last])
    e200 = float(ema200.iloc[last])
    atr_v = float(atr_s.iloc[last])
    vol_recent = float(df["volume"].iloc[-5:].mean())
    vol_baseline = float(df["volume"].iloc[-30:-5].mean()) or 1.0
    vol_ratio = vol_recent / vol_baseline

    long_score = 0.0
    short_score = 0.0

    # Trend alignment
    if price > e20 > e50:
        long_score += 25
    if price < e20 < e50:
        short_score += 25
    if e50 > e200:
        long_score += 10
    if e50 < e200:
        short_score += 10

    # MACD momentum
    if mh > 0 and mh > mh_prev:
        long_score += 20
    if mh < 0 and mh < mh_prev:
        short_score += 20

    # RSI zones
    if 50 < rsi_v < 70:
        long_score += 15
    elif rsi_v <= 30:
        long_score += 10  # potential reversal long
    if 30 < rsi_v < 50:
        short_score += 15
    elif rsi_v >= 70:
        short_score += 10  # potential reversal short

    # Volume confirmation
    if vol_ratio > 1.3:
        if mh > 0:
            long_score += 15
        if mh < 0:
            short_score += 15

    # Bollinger breakout
    if price > float(upper_bb.iloc[last]):
        long_score += 10
    if price < float(lower_bb.iloc[last]):
        short_score += 10

    if long_score >= short_score:
        direction = "LONG"
        score = long_score
    else:
        direction = "SHORT"
        score = short_score

    if score < 35:
        direction = "NEUTRAL"

    # Recent swing high/low for breakout level
    swing_high = float(df["high"].iloc[-30:].max())
    swing_low = float(df["low"].iloc[-30:].min())

    return {
        "direction": direction,
        "score": round(score, 1),
        "price": price,
        "atr": atr_v,
        "rsi": round(rsi_v, 2),
        "macd_hist": round(mh, 6),
        "ema20": round(e20, 6),
        "ema50": round(e50, 6),
        "ema200": round(e200, 6),
        "swing_high": swing_high,
        "swing_low": swing_low,
        "volume_ratio": round(vol_ratio, 2),
        "bb_upper": round(float(upper_bb.iloc[last]), 6),
        "bb_lower": round(float(lower_bb.iloc[last]), 6),
    }
