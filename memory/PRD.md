# PULSE · Smart Trader · PRD

## Original Problem Statement (Portuguese, voice transcript)
User wants an app to assist live trading: a market scanner button that finds best entry opportunities and returns entry price, direction (long/short), stop loss, take profit, entry time, and suggested leverage. Primary focus: crypto perpetual futures (Binance, Bybit). Secondary: spot, forex, stocks. Must NOT use delayed data (Yahoo has 15-min delay). Wants AI to refine the algorithmic analysis but to be FAST. No login, no Emergent branding. User decides; tool just suggests.

## User choices captured (Iteration 1)
- Exchanges: Binance + Bybit (user requested). FINDING: Binance Futures and Bybit are GEO-BLOCKED from server region. Pivoted to: Binance Spot (via `data-api.binance.vision` mirror) + OKX (Spot + Perpetual Swaps) — OKX is equivalent in liquidity to Bybit/Binance Futures and not geo-blocked.
- Analysis: Hybrid (technical indicators + AI). User offered own OpenAI key; currently using EMERGENT_LLM_KEY with GPT-5.2.
- MVP scope: simple scan button + filters (exchange, market type, timeframe, minutes-to-entry).
- Entry time always ≥ 3 minutes in future (configurable 3/5/10/15/30 min).
- No authentication. No Emergent branding (badge hidden).
- Disclaimer included (subtle footer).

## Architecture
**Backend (FastAPI + MongoDB + httpx + emergentintegrations)**
- `market_data.py`: Binance Spot (vision mirror) + OKX (spot + swap) fetchers
- `indicators.py`: RSI, MACD, EMA20/50/200, ATR, Bollinger, volume ratio
- `scanner.py`: concurrent scan of top-N symbols by volume; scoring; ATR-based SL/TP
- `ai_analyst.py`: GPT-5.2 enrichment (justification, confidence, key level, alert)
- `server.py`: routes `/api/scan`, `/api/klines`, `/api/movers`, `/api/symbols`, `/api/signals`

**Frontend (React 19 + Tailwind + lightweight-charts + react-fast-marquee + phosphor-icons)**
- Single dashboard `/`
- Header with PULSE branding + LIVE indicator + ticker marquee
- Filters panel: exchange, market_type, timeframe (scalp/short/long), minutes_to_entry
- Big "VARRER MERCADO" button with tracing-beam animation
- SignalCard: direction badge (LONG/SHORT), entry/SL/TP, RR, leverage, horizon, confidence, key level, countdown to entry_time, AI justification (terminal style), alert
- PriceChart: lightweight-charts candlesticks with entry/SL/TP price lines
- HistoryList: previous signals (click to reload chart, delete supported)
- Disclaimer footer

## Implemented (2026-02-16)
- ✅ Backend market data via OKX + Binance Spot vision mirror
- ✅ Technical indicators (RSI/MACD/EMA/ATR/BB/Volume)
- ✅ Concurrent scanning, scoring, ATR-based plan
- ✅ AI enrichment via GPT-5.2 in Portuguese with strict JSON
- ✅ Frontend dashboard with filters, scan button, signal card, chart, history
- ✅ Ticker marquee with real-time top movers
- ✅ Dark theme (Chivo/IBM Plex Sans/JetBrains Mono)
- ✅ No Emergent branding (badge hidden, title updated)
- ✅ Countdown timer to entry_time
- ✅ MongoDB persistence of signals

## Known Limits
- Binance Futures and Bybit APIs are geo-blocked from server's region; replaced by OKX (equivalent perpetuals exchange).
- Forex/Stocks not yet integrated (deferred; user said it's not main focus).
- OTC/binary options not integrated (no reliable public API found).
- No automated order execution (intentional per user safety).

## Backlog
- P1: Add Forex / US stocks scanner via Alpha Vantage (requires user API key)
- P1: Multi-signal scan (return top 3 opportunities, not just best)
- P2: Custom risk parameters (account size %, max leverage)
- P2: Alerts via Telegram/Webhook when a high-confidence signal is found
- P2: Backtest module — show historical accuracy of similar setups
- P3: TradingView Webhook integration for one-click chart open
- P3: User-supplied OpenAI API key (UI to swap from EMERGENT_LLM_KEY)
