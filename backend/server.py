from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict

from market_data import get_top_symbols, get_klines, get_movers
from scanner import scan_market, scan_market_top_n
from ai_analyst import enrich_signal


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="PULSE Smart Trader API")
api_router = APIRouter(prefix="/api")


# ---------------- Models ----------------
class ScanRequest(BaseModel):
    exchange: Literal["binance", "okx"] = "okx"
    market_type: Literal["futures", "spot"] = "futures"
    timeframe: Literal["scalp", "short", "long"] = "short"
    minutes_to_entry: int = Field(default=5, ge=3, le=60)


class Indicators(BaseModel):
    rsi: float
    macd_hist: float
    ema20: float
    ema50: float
    ema200: float
    atr: float
    volume_ratio: float
    swing_high: float
    swing_low: float
    bb_upper: float
    bb_lower: float


class Signal(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    exchange: str
    market_type: str
    timeframe: str
    interval: str
    direction: str
    score: float
    entry: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    leverage_suggestion: str
    horizon: str
    entry_time: str  # ISO string
    indicators: Indicators
    justification: str
    confidence: str
    key_level: str = ""
    alert: str = ""
    created_at: str


# ---------------- Routes ----------------
@api_router.get("/")
async def root():
    return {"status": "ok", "app": "PULSE Smart Trader"}


@api_router.get("/movers")
async def movers(
    exchange: Literal["binance", "okx"] = "okx",
    market_type: Literal["futures", "spot"] = "futures",
    top: int = 12,
):
    try:
        return await get_movers(exchange, market_type, top)
    except Exception as e:
        logger.error(f"movers failed: {e}")
        raise HTTPException(status_code=502, detail=f"Falha ao buscar movers: {e}")


@api_router.get("/klines")
async def klines(
    exchange: Literal["binance", "okx"] = "okx",
    market_type: Literal["futures", "spot"] = "futures",
    symbol: str = Query(...),
    interval: str = "1h",
    limit: int = 200,
):
    try:
        data = await get_klines(exchange, market_type, symbol, interval, limit)
        return {"symbol": symbol, "interval": interval, "klines": data}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Falha ao buscar klines: {e}")


@api_router.get("/symbols")
async def symbols(
    exchange: Literal["binance", "okx"] = "okx",
    market_type: Literal["futures", "spot"] = "futures",
    limit: int = 30,
):
    try:
        data = await get_top_symbols(exchange, market_type, limit)
        return {"symbols": data}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Falha ao buscar símbolos: {e}")


@api_router.post("/scan")
async def scan(req: ScanRequest):
    """Run a market scan and return up to 3 best opportunities.

    Only the first (top-ranked) candidate is enriched by the AI to keep response time
    low. Other candidates have null AI fields and can be enriched on demand via
    /api/enrich.
    """
    try:
        results = await scan_market_top_n(req.exchange, req.market_type, req.timeframe, n=3)
        if not results:
            raise HTTPException(status_code=404, detail="Nenhuma oportunidade encontrada agora. Tente outro mercado ou timeframe.")

        now = datetime.now(timezone.utc)
        entry_time = now + timedelta(minutes=req.minutes_to_entry)

        candidates = []
        for idx, raw in enumerate(results):
            klines_data = raw.pop("klines", [])
            # Only enrich the top candidate via AI (cheaper + faster).
            if idx == 0:
                raw = await enrich_signal(raw)
                justification = raw.get("justification", "")
                confidence = raw.get("confidence", "MEDIA")
                key_level = raw.get("key_level", "")
                alert = raw.get("alert", "")
                ai_enriched = True
            else:
                justification, confidence, key_level, alert = "", "", "", ""
                ai_enriched = False

            candidate = {
                "id": str(uuid.uuid4()),
                "symbol": raw["symbol"],
                "exchange": raw["exchange"],
                "market_type": raw["market_type"],
                "timeframe": raw["timeframe"],
                "interval": raw["interval"],
                "direction": raw["direction"],
                "score": raw["score"],
                "entry": raw["entry"],
                "stop_loss": raw["stop_loss"],
                "take_profit": raw["take_profit"],
                "risk_reward": raw["risk_reward"],
                "leverage_suggestion": raw["leverage_suggestion"],
                "horizon": raw["horizon"],
                "entry_time": entry_time.isoformat(),
                "indicators": raw["indicators"],
                "justification": justification,
                "confidence": confidence,
                "key_level": key_level,
                "alert": alert,
                "ai_enriched": ai_enriched,
                "created_at": now.isoformat(),
                "klines": klines_data,
            }
            candidates.append(candidate)

        # Persist only the top candidate (the one with AI). Others are persisted
        # later if/when the user enriches them via /api/enrich.
        top = {k: v for k, v in candidates[0].items() if k != "klines"}
        await db.signals.insert_one({**top})

        return {"candidates": candidates}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("scan failed")
        raise HTTPException(status_code=500, detail=f"Erro no scan: {e}")


class EnrichRequest(BaseModel):
    candidate: dict


@api_router.post("/enrich")
async def enrich_candidate(req: EnrichRequest):
    """Run AI enrichment on a candidate the user clicked on. Persists to history."""
    try:
        candidate = dict(req.candidate)
        # Keep klines aside so we don't pass them to the LLM
        klines_data = candidate.pop("klines", [])
        if candidate.get("ai_enriched"):
            # Already enriched; just return as-is with klines
            return {**candidate, "klines": klines_data}

        enriched = await enrich_signal(candidate)
        enriched["ai_enriched"] = True

        # Persist a fresh history record
        record = {k: v for k, v in enriched.items() if k != "klines"}
        record["id"] = str(uuid.uuid4())
        record["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.signals.insert_one({**record})

        return {**enriched, "id": record["id"], "klines": klines_data}
    except Exception as e:
        logger.exception("enrich failed")
        raise HTTPException(status_code=500, detail=f"Erro ao analisar com IA: {e}")


@api_router.get("/signals")
async def list_signals(limit: int = 50):
    docs = await db.signals.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return {"signals": docs}


@api_router.delete("/signals/{signal_id}")
async def delete_signal(signal_id: str):
    res = await db.signals.delete_one({"id": signal_id})
    return {"deleted": res.deleted_count}


# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
