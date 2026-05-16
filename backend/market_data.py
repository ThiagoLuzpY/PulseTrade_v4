"""Fetchers for crypto market data (spot + perpetual futures).

NOTE on data sources:
- Binance Spot: data-api.binance.vision public mirror (Binance Futures and Bybit are
  geo-blocked from this server's region, so we use the Binance Vision mirror for spot
  and OKX for both spot and perpetual swaps. OKX is one of the top global derivatives
  exchanges with the same liquidity profile as Binance Futures / Bybit.)
- OKX: api.okx.com (spot + perpetual swaps)
"""
from __future__ import annotations
import httpx
from typing import List, Dict, Any, Optional

BINANCE_SPOT = "https://data-api.binance.vision/api/v3"
OKX = "https://www.okx.com/api/v5"

INTERVAL_MAP_BINANCE = {
    "1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d",
}
INTERVAL_MAP_OKX = {
    "1m": "1m", "5m": "5m", "15m": "15m", "1h": "1H", "4h": "4H", "1d": "1D",
}


async def _get(client: httpx.AsyncClient, url: str, params: Optional[Dict] = None) -> Any:
    r = await client.get(url, params=params, timeout=10.0)
    r.raise_for_status()
    return r.json()


def _okx_inst_id(symbol: str, market_type: str) -> str:
    """Convert symbol like BTCUSDT -> BTC-USDT or BTC-USDT-SWAP."""
    if "-" in symbol:
        base = symbol
    elif symbol.endswith("USDT"):
        base = f"{symbol[:-4]}-USDT"
    elif symbol.endswith("USDC"):
        base = f"{symbol[:-4]}-USDC"
    else:
        base = symbol
    return f"{base}-SWAP" if market_type == "futures" else base


def _from_okx_inst(inst_id: str) -> str:
    """Convert OKX inst id like BTC-USDT-SWAP -> BTCUSDT for display."""
    parts = inst_id.split("-")
    if len(parts) >= 2:
        return f"{parts[0]}{parts[1]}"
    return inst_id


async def get_top_symbols(exchange: str, market_type: str, limit: int = 30) -> List[Dict[str, Any]]:
    """Return list of top pairs by 24h quote volume."""
    async with httpx.AsyncClient() as client:
        if exchange == "binance" and market_type == "spot":
            data = await _get(client, f"{BINANCE_SPOT}/ticker/24hr")
            items = [
                {
                    "symbol": d["symbol"],
                    "last_price": float(d["lastPrice"]),
                    "change_pct": float(d["priceChangePercent"]),
                    "volume_quote": float(d["quoteVolume"]),
                }
                for d in data
                if d["symbol"].endswith("USDT")
                and not d["symbol"].endswith("UPUSDT")
                and not d["symbol"].endswith("DOWNUSDT")
                and not d["symbol"].endswith("BULLUSDT")
                and not d["symbol"].endswith("BEARUSDT")
            ]
        elif exchange == "okx":
            inst_type = "SWAP" if market_type == "futures" else "SPOT"
            data = await _get(client, f"{OKX}/market/tickers", {"instType": inst_type})
            rows = data.get("data", [])
            items = []
            for r in rows:
                inst_id = r.get("instId", "")
                if inst_type == "SWAP" and not inst_id.endswith("USDT-SWAP"):
                    continue
                if inst_type == "SPOT" and not inst_id.endswith("-USDT"):
                    continue
                last = float(r.get("last") or 0)
                open24 = float(r.get("open24h") or 0)
                change = ((last - open24) / open24 * 100) if open24 > 0 else 0.0
                # volCcy24h is base-currency volume; for SWAP use volCcy24h*last to approximate quote vol
                vol_quote = float(r.get("volCcy24h") or 0) * last
                items.append({
                    "symbol": _from_okx_inst(inst_id),
                    "okx_inst_id": inst_id,
                    "last_price": last,
                    "change_pct": change,
                    "volume_quote": vol_quote,
                })
        else:
            return []

    items = [x for x in items if x["last_price"] > 0 and x["volume_quote"] > 0]
    items.sort(key=lambda x: x["volume_quote"], reverse=True)
    return items[:limit]


async def get_klines(exchange: str, market_type: str, symbol: str, interval: str, limit: int = 200) -> List[Dict[str, float]]:
    """Return klines: [{open_time, open, high, low, close, volume}, ...] sorted oldest -> newest."""
    async with httpx.AsyncClient() as client:
        if exchange == "binance":
            if market_type != "spot":
                # Binance Futures is geo-blocked; we don't expose it
                return []
            iv = INTERVAL_MAP_BINANCE.get(interval, "1h")
            data = await _get(client, f"{BINANCE_SPOT}/klines", {"symbol": symbol, "interval": iv, "limit": limit})
            return [
                {
                    "open_time": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                }
                for k in data
            ]
        elif exchange == "okx":
            iv = INTERVAL_MAP_OKX.get(interval, "1H")
            inst_id = _okx_inst_id(symbol, market_type)
            data = await _get(client, f"{OKX}/market/candles", {"instId": inst_id, "bar": iv, "limit": min(limit, 300)})
            rows = data.get("data", [])
            # OKX returns newest first; reverse to oldest first
            rows = list(reversed(rows))
            return [
                {
                    "open_time": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                }
                for k in rows
            ]
    return []


async def get_movers(exchange: str = "okx", market_type: str = "futures", top: int = 12) -> Dict[str, List[Dict[str, Any]]]:
    items = await get_top_symbols(exchange, market_type, limit=200)
    gainers = sorted(items, key=lambda x: x["change_pct"], reverse=True)[:top]
    losers = sorted(items, key=lambda x: x["change_pct"])[:top]
    return {"gainers": gainers, "losers": losers}
