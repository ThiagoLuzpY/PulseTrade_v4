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
from scanner import scan_market
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
    try:
        result = await scan_market(req.exchange, req.market_type, req.timeframe)
        if not result:
            raise HTTPException(status_code=404, detail="Nenhuma oportunidade encontrada agora. Tente outro mercado ou timeframe.")

        # Strip klines before AI call to save tokens; keep separately
        klines_data = result.pop("klines", [])
        result = await enrich_signal(result)

        now = datetime.now(timezone.utc)
        entry_time = now + timedelta(minutes=req.minutes_to_entry)

        signal = {
            "id": str(uuid.uuid4()),
            "symbol": result["symbol"],
            "exchange": result["exchange"],
            "market_type": result["market_type"],
            "timeframe": result["timeframe"],
            "interval": result["interval"],
            "direction": result["direction"],
            "score": result["score"],
            "entry": result["entry"],
            "stop_loss": result["stop_loss"],
            "take_profit": result["take_profit"],
            "risk_reward": result["risk_reward"],
            "leverage_suggestion": result["leverage_suggestion"],
            "horizon": result["horizon"],
            "entry_time": entry_time.isoformat(),
            "indicators": result["indicators"],
            "justification": result.get("justification", ""),
            "confidence": result.get("confidence", "MEDIA"),
            "key_level": result.get("key_level", ""),
            "alert": result.get("alert", ""),
            "created_at": now.isoformat(),
        }

        # Persist
        await db.signals.insert_one({**signal})

        # Return with klines for chart
        return {**signal, "klines": klines_data}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("scan failed")
        raise HTTPException(status_code=500, detail=f"Erro no scan: {e}")


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
