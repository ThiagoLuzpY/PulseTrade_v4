"""Market scanner: scans top symbols on the chosen exchange, scores them, returns best opportunity."""
from __future__ import annotations
import asyncio
from typing import Dict, Any, List
from market_data import get_top_symbols, get_klines
from indicators import compute_signal

# Map our app timeframe to exchange interval and an estimated hold horizon
TIMEFRAME_CONFIG = {
    "scalp": {"interval": "5m", "horizon": "15min - 2h", "kline_limit": 200, "sl_atr": 1.0, "tp_atr": 1.8, "lev": "5x - 10x"},
    "short": {"interval": "1h", "horizon": "4h - 1 dia", "kline_limit": 200, "sl_atr": 1.5, "tp_atr": 3.0, "lev": "3x - 5x"},
    "long":  {"interval": "4h", "horizon": "3 - 14 dias", "kline_limit": 200, "sl_atr": 2.0, "tp_atr": 5.0, "lev": "1x - 3x"},
}


async def _scan_symbol(exchange: str, market_type: str, symbol: str, interval: str, limit: int) -> Dict[str, Any] | None:
    try:
        kl = await get_klines(exchange, market_type, symbol, interval, limit)
        sig = compute_signal(kl)
        if sig is None:
            return None
        sig["symbol"] = symbol
        sig["klines"] = kl
        return sig
    except Exception:
        return None


def _build_candidate(best: Dict[str, Any], cfg: Dict[str, Any], exchange: str, market_type: str, timeframe: str) -> Dict[str, Any]:
    price = best["price"]
    atr_v = best["atr"]
    direction = best["direction"]
    if direction == "LONG":
        entry = price
        stop_loss = entry - atr_v * cfg["sl_atr"]
        take_profit = entry + atr_v * cfg["tp_atr"]
    else:
        entry = price
        stop_loss = entry + atr_v * cfg["sl_atr"]
        take_profit = entry - atr_v * cfg["tp_atr"]
    rr = abs(take_profit - entry) / max(abs(entry - stop_loss), 1e-9)
    return {
        "symbol": best["symbol"],
        "exchange": exchange,
        "market_type": market_type,
        "timeframe": timeframe,
        "interval": cfg["interval"],
        "direction": direction,
        "score": best["score"],
        "entry": round(entry, 6),
        "stop_loss": round(stop_loss, 6),
        "take_profit": round(take_profit, 6),
        "risk_reward": round(rr, 2),
        "leverage_suggestion": cfg["lev"],
        "horizon": cfg["horizon"],
        "indicators": {
            "rsi": best["rsi"],
            "macd_hist": best["macd_hist"],
            "ema20": best["ema20"],
            "ema50": best["ema50"],
            "ema200": best["ema200"],
            "atr": round(atr_v, 6),
            "volume_ratio": best["volume_ratio"],
            "swing_high": best["swing_high"],
            "swing_low": best["swing_low"],
            "bb_upper": best["bb_upper"],
            "bb_lower": best["bb_lower"],
        },
        "klines": best["klines"],
    }


async def scan_market(exchange: str, market_type: str, timeframe: str, max_symbols: int = 25) -> Dict[str, Any] | None:
    """Return the single best opportunity (kept for backwards compatibility / tests)."""
    candidates = await scan_market_top_n(exchange, market_type, timeframe, n=1, max_symbols=max_symbols)
    return candidates[0] if candidates else None


async def scan_market_top_n(exchange: str, market_type: str, timeframe: str, n: int = 3, max_symbols: int = 25) -> List[Dict[str, Any]]:
    """Return the top N opportunities ranked by confluence score."""
    cfg = TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG["short"])
    top = await get_top_symbols(exchange, market_type, limit=max_symbols)
    if not top:
        return []

    sem = asyncio.Semaphore(8)

    async def task(symbol: str):
        async with sem:
            return await _scan_symbol(exchange, market_type, symbol, cfg["interval"], cfg["kline_limit"])

    results = await asyncio.gather(*[task(t["symbol"]) for t in top])
    results = [r for r in results if r and r["direction"] != "NEUTRAL"]
    if not results:
        return []

    results.sort(key=lambda r: r["score"], reverse=True)
    return [_build_candidate(r, cfg, exchange, market_type, timeframe) for r in results[:n]]
