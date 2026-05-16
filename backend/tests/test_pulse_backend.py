"""PULSE Smart Trader - Backend API tests.

Covers:
- Root health
- Movers (OKX futures + Binance spot via vision mirror)
- Klines (OKX futures)
- Scan (OKX futures + Binance spot) with AI enrichment
- Signals history (persistence)
- Delete signal
"""
from __future__ import annotations
import os
import re
import time
from datetime import datetime
from typing import Dict, Any

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

# Generous timeout because /api/scan does many klines fetches + an LLM call
SCAN_TIMEOUT = 90
DEFAULT_TIMEOUT = 30


@pytest.fixture(scope="session")
def http():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# Shared cache so we don't run the (slow) scan twice
_state: Dict[str, Any] = {}


# ---------------- Health ----------------
class TestRoot:
    def test_root_status_ok(self, http):
        r = http.get(f"{API}/", timeout=DEFAULT_TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "ok"
        assert "PULSE" in data.get("app", "")


# ---------------- Movers ----------------
class TestMovers:
    def test_okx_futures_movers(self, http):
        r = http.get(f"{API}/movers", params={"exchange": "okx", "market_type": "futures", "top": 5}, timeout=DEFAULT_TIMEOUT)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "gainers" in data and "losers" in data
        assert isinstance(data["gainers"], list) and len(data["gainers"]) > 0
        assert isinstance(data["losers"], list) and len(data["losers"]) > 0
        for it in data["gainers"][:3]:
            for k in ("symbol", "last_price", "change_pct", "volume_quote"):
                assert k in it, f"missing field {k} in mover {it}"
            assert isinstance(it["symbol"], str) and it["symbol"]
            assert it["last_price"] > 0
            assert it["volume_quote"] > 0

    def test_binance_spot_movers_via_vision(self, http):
        r = http.get(f"{API}/movers", params={"exchange": "binance", "market_type": "spot", "top": 5}, timeout=DEFAULT_TIMEOUT)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data.get("gainers"), list) and len(data["gainers"]) > 0
        assert isinstance(data.get("losers"), list) and len(data["losers"]) > 0
        sample = data["gainers"][0]
        # Binance spot symbols end with USDT (no dash)
        assert sample["symbol"].endswith("USDT")
        assert sample["last_price"] > 0


# ---------------- Klines ----------------
class TestKlines:
    def test_klines_okx_futures_btc(self, http):
        r = http.get(
            f"{API}/klines",
            params={"exchange": "okx", "market_type": "futures", "symbol": "BTCUSDT", "interval": "1h", "limit": 50},
            timeout=DEFAULT_TIMEOUT,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["symbol"] == "BTCUSDT"
        assert data["interval"] == "1h"
        klines = data["klines"]
        assert isinstance(klines, list) and len(klines) >= 20
        k0 = klines[0]
        for k in ("open_time", "open", "high", "low", "close", "volume"):
            assert k in k0
        assert k0["high"] >= k0["low"]
        # Ensure oldest-first ordering
        assert klines[0]["open_time"] < klines[-1]["open_time"]


# ---------------- Scan (OKX futures) ----------------
REQUIRED_SIGNAL_FIELDS = [
    "id", "symbol", "exchange", "market_type", "timeframe", "interval",
    "direction", "score", "entry", "stop_loss", "take_profit", "risk_reward",
    "leverage_suggestion", "horizon", "entry_time", "indicators",
    "justification", "confidence", "key_level", "alert", "created_at", "klines",
]

REQUIRED_INDICATOR_FIELDS = [
    "rsi", "macd_hist", "ema20", "ema50", "ema200", "atr",
    "volume_ratio", "swing_high", "swing_low", "bb_upper", "bb_lower",
]


def _validate_signal_shape(sig: Dict[str, Any]):
    for f in REQUIRED_SIGNAL_FIELDS:
        assert f in sig, f"missing field in signal: {f}"
    assert sig["direction"] in ("LONG", "SHORT"), f"direction={sig['direction']}"
    for f in ("entry", "stop_loss", "take_profit", "risk_reward", "score"):
        assert isinstance(sig[f], (int, float))
        assert sig[f] > 0 or f == "score"
    assert isinstance(sig["leverage_suggestion"], str) and sig["leverage_suggestion"]
    assert isinstance(sig["horizon"], str) and sig["horizon"]
    ind = sig["indicators"]
    for f in REQUIRED_INDICATOR_FIELDS:
        assert f in ind, f"missing indicator: {f}"
    assert isinstance(sig["klines"], list) and len(sig["klines"]) > 30


class TestScan:
    def test_scan_okx_futures_short(self, http):
        payload = {"exchange": "okx", "market_type": "futures", "timeframe": "short", "minutes_to_entry": 5}
        r = http.post(f"{API}/scan", json=payload, timeout=SCAN_TIMEOUT)
        assert r.status_code == 200, r.text
        sig = r.json()
        _validate_signal_shape(sig)
        assert sig["exchange"] == "okx"
        assert sig["market_type"] == "futures"
        assert sig["timeframe"] == "short"
        assert sig["interval"] == "1h"
        _state["okx_signal"] = sig

    def test_entry_time_at_least_3_min_in_future(self, http):
        sig = _state.get("okx_signal")
        assert sig, "okx_signal not set"
        created = datetime.fromisoformat(sig["created_at"])
        entry = datetime.fromisoformat(sig["entry_time"])
        delta = (entry - created).total_seconds()
        assert delta >= 3 * 60 - 1, f"entry_time delta {delta}s < 180s"
        # 5 minutes requested -> allow tiny clock-skew tolerance
        assert 270 <= delta <= 330, f"entry_time delta {delta}s not ~5min"

    def test_scan_binance_spot_short(self, http):
        payload = {"exchange": "binance", "market_type": "spot", "timeframe": "short", "minutes_to_entry": 5}
        r = http.post(f"{API}/scan", json=payload, timeout=SCAN_TIMEOUT)
        assert r.status_code == 200, r.text
        sig = r.json()
        _validate_signal_shape(sig)
        assert sig["exchange"] == "binance"
        assert sig["market_type"] == "spot"
        _state["bin_signal"] = sig

    def test_ai_justification_portuguese_non_empty(self, http):
        sig = _state.get("okx_signal") or _state.get("bin_signal")
        assert sig is not None, "no signal produced earlier"
        j = sig.get("justification", "")
        assert isinstance(j, str) and len(j.strip()) >= 10, f"justification too short: {j!r}"
        # Heuristic: PT-BR usually contains accented chars or common PT words
        pt_markers = re.compile(
            r"\b(de|para|com|que|alta|baixa|preço|tendência|forte|média|fraca|suporte|resistência|"
            r"compra|venda|sinal|operação|setup|confluência|topo|fundo|EMA|RSI|MACD|alvo)\b",
            re.IGNORECASE,
        )
        assert pt_markers.search(j), f"justification doesn't look PT-BR: {j!r}"
        assert sig.get("confidence") in ("ALTA", "MEDIA", "MÉDIA", "BAIXA"), sig.get("confidence")

    def test_scan_bad_minutes_validation(self, http):
        # minutes_to_entry < 3 should be rejected by Pydantic
        r = http.post(f"{API}/scan", json={"exchange": "okx", "market_type": "futures",
                                           "timeframe": "short", "minutes_to_entry": 1}, timeout=DEFAULT_TIMEOUT)
        assert r.status_code in (400, 422), r.text


# ---------------- Signals (persistence + delete) ----------------
class TestSignals:
    def test_signals_list_contains_scanned(self, http):
        sig = _state.get("okx_signal")
        assert sig, "okx_signal not set"
        # Allow a brief moment for write propagation
        time.sleep(0.5)
        r = http.get(f"{API}/signals", params={"limit": 50}, timeout=DEFAULT_TIMEOUT)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "signals" in data and isinstance(data["signals"], list)
        ids = [s.get("id") for s in data["signals"]]
        assert sig["id"] in ids, f"persisted signal {sig['id']} not found in history"
        # Sorted latest-first
        times = [s.get("created_at") for s in data["signals"] if s.get("created_at")]
        assert times == sorted(times, reverse=True), "signals are not sorted latest-first"
        # No _id leakage
        assert all("_id" not in s for s in data["signals"]), "Mongo _id leaked in /api/signals"

    def test_delete_signal_removes_it(self, http):
        sig = _state.get("bin_signal") or _state.get("okx_signal")
        assert sig
        sid = sig["id"]
        r = http.delete(f"{API}/signals/{sid}", timeout=DEFAULT_TIMEOUT)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("deleted") == 1
        # Confirm it's gone
        r2 = http.get(f"{API}/signals", params={"limit": 100}, timeout=DEFAULT_TIMEOUT)
        ids = [s.get("id") for s in r2.json().get("signals", [])]
        assert sid not in ids, f"signal {sid} still in history after delete"

    def test_delete_nonexistent_signal_returns_zero(self, http):
        r = http.delete(f"{API}/signals/does-not-exist-xyz", timeout=DEFAULT_TIMEOUT)
        assert r.status_code == 200
        assert r.json().get("deleted") == 0
