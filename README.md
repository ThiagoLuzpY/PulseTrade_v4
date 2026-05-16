# PULSE TRADE

> **Scanner inteligente de oportunidades de trading em tempo real, com análise técnica algorítmica + IA.**
>
> Aperte um botão. Receba o melhor setup do mercado: par, direção, entrada, stop, alvo, alavancagem e justificativa — pronto pra você executar na sua corretora.

---

## 🎯 O que é o Pulse Trade

O **Pulse Trade** é uma ferramenta pessoal de assistência ao trader que escaneia dezenas de pares em tempo real, computa indicadores técnicos clássicos em paralelo e usa **GPT-5.2** para validar a confluência e devolver um plano de trade completo em **menos de 10 segundos**.

A decisão final — entrar, ajustar alavancagem, gerenciar risco — é sempre do operador. O Pulse só faz o trabalho pesado de varredura, cálculo e contexto.

### Por que existe
Robôs de varredura comerciais são caros, lentos (Claude conectado ao TradingView demora 5+ minutos por análise) e travados em uma única exchange. O Pulse Trade resolve isso:

- ⚡ **Varredura paralela** de até 25 ativos em < 4s
- 🧠 **IA enxuta**: GPT-5.2 com prompt cirúrgico devolve resposta em ~5s, máximo 3 frases de justificativa
- ⏱️ **Hora exata de entrada com countdown** — sempre ≥ 3 minutos no futuro para você ter tempo de abrir a corretora
- 📊 **Gráfico ao vivo** com linhas de Entry/SL/TP sobrepostas
- 🎨 **UI estilo terminal Bloomberg/TradingView** — denso, escuro, profissional

---

## 🚀 Como funciona — Fluxo do usuário

```
1. Escolher EXCHANGE        →  OKX  ou  Binance (Spot)
2. Escolher MERCADO         →  Futuros Perpétuos  ou  Spot
3. Escolher PRAZO           →  Scalp (5m)  ·  Curto (1h)  ·  Longo (4h)
4. Escolher ENTRADA EM      →  3, 5, 10, 15 ou 30 minutos
5. Clicar  ▶  VARRER MERCADO
6. ... 5s depois ...
7. Toast: "Oportunidade encontrada: BTCUSDT LONG"
   └─ Card de sinal completo + gráfico ao vivo
```

### Detalhamento técnico de cada scan

Quando você clica em **VARRER MERCADO**, o backend:

1. **Busca os ~25 pares de maior volume 24h** da exchange escolhida
2. **Em paralelo (8 conexões simultâneas)** baixa 200 candles de cada par no timeframe certo
3. **Computa indicadores** para cada par:
   - RSI(14)
   - MACD(12,26,9) — linha, sinal e histograma
   - EMA(20), EMA(50), EMA(200)
   - ATR(14) — usado para dimensionar SL/TP
   - Bollinger Bands(20, 2σ)
   - Volume ratio (últimas 5 barras vs. baseline 30)
4. **Atribui um score 0-100** por confluência:
   - Alinhamento de tendência (EMA20 > EMA50 > EMA200)
   - Momentum MACD
   - Zona de RSI
   - Confirmação por volume
   - Rompimentos de Bollinger
5. **Seleciona o par de maior score** (mínimo 35/100) e calcula:
   - **Entry** = preço atual
   - **Stop Loss** = Entry ∓ ATR × multiplier (depende do timeframe)
   - **Take Profit** = Entry ± ATR × multiplier (R:R típico 1:2 ou 1:3)
   - **Alavancagem sugerida** conservadora por timeframe
6. **Envia o pacote pro GPT-5.2** com um prompt forçando JSON estrito:
   - `justification` (≤ 3 frases, PT-BR)
   - `confidence` (ALTA / MEDIA / BAIXA)
   - `key_level` (nível-chave a observar)
   - `alert` (condição que invalida o setup)
7. **Persiste no MongoDB** e retorna pro frontend com 200 candles para o gráfico

Tempo total típico: **4–10 segundos**.

---

## 🧠 Stack técnica

### Backend
| Componente | Tecnologia |
|---|---|
| Framework | FastAPI (Python 3.11) |
| Banco | MongoDB (Motor — driver async) |
| HTTP async | httpx |
| Indicadores | pandas + numpy (sem TA-Lib) |
| IA | OpenAI GPT-5.2 via `emergentintegrations` |
| Servidor | Uvicorn + Supervisor |

### Frontend
| Componente | Tecnologia |
|---|---|
| Framework | React 19 + React Router 7 |
| Estilo | Tailwind CSS 3 + Shadcn/UI |
| Gráficos | `lightweight-charts` (TradingView) |
| Ticker rolante | `react-fast-marquee` |
| Ícones | `@phosphor-icons/react` |
| Tipografia | Chivo · IBM Plex Sans · JetBrains Mono |
| Toasts | `sonner` |
| HTTP | Axios |

### Fontes de dados de mercado

| Exchange | Mercado | Endpoint | Status |
|---|---|---|---|
| **OKX** | Spot + Perpétuos | `www.okx.com/api/v5` | ✅ Ativo |
| **Binance** | Spot (mirror) | `data-api.binance.vision/api/v3` | ✅ Ativo |
| Binance Futures (`fapi`) | Perpétuos | `fapi.binance.com` | ❌ Geo-bloqueado no servidor |
| Bybit | Perpétuos | `api.bybit.com` | ❌ Geo-bloqueado no servidor |

> 💡 **Nota:** OKX é uma das 3 maiores corretoras globais de perpetuals e oferece os mesmos pares (BTC-USDT-SWAP, ETH-USDT-SWAP, etc.) com liquidez equivalente à Binance Futures e Bybit. Os preços são praticamente idênticos por arbitragem.

---

## 📐 Arquitetura

```
┌──────────────────────────────────────────────────────────────┐
│                       Frontend (React)                        │
│  Dashboard → FiltersPanel → ScanButton                        │
│         ↓                                                      │
│     SignalCard ← PriceChart ← HistoryList                     │
└─────────────────────────┬────────────────────────────────────┘
                          │  HTTPS + /api/*
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                  Backend (FastAPI)                            │
│                                                                │
│  /api/scan ──┬──► scanner.py (concurrent fetch + score)       │
│              │                                                 │
│              ├──► indicators.py (RSI/MACD/EMA/ATR/BB)         │
│              │                                                 │
│              ├──► ai_analyst.py ────► GPT-5.2                 │
│              │                                                 │
│              └──► db.signals (Mongo persist)                  │
│                                                                │
│  /api/movers, /api/klines, /api/symbols, /api/signals         │
└──────────────────┬─────────────────────────┬─────────────────┘
                   │                         │
                   ▼                         ▼
        ┌──────────────────┐      ┌──────────────────┐
        │   OKX  /  Vision │      │     MongoDB      │
        │   public market  │      │   signals coll.  │
        └──────────────────┘      └──────────────────┘
```

---

## 📁 Estrutura de pastas

```
/app
├── backend/
│   ├── server.py          # Rotas FastAPI (/api/scan, /api/movers, etc.)
│   ├── market_data.py     # Fetchers OKX + Binance Vision
│   ├── indicators.py      # RSI, MACD, EMA, ATR, Bollinger
│   ├── scanner.py         # Lógica de varredura + scoring
│   ├── ai_analyst.py      # Enriquecimento via GPT-5.2
│   ├── requirements.txt
│   └── .env               # MONGO_URL, OPENAI_API_KEY, EMERGENT_LLM_KEY
├── frontend/
│   ├── src/
│   │   ├── App.js
│   │   ├── pages/
│   │   │   └── Dashboard.jsx     # Página principal (única)
│   │   ├── components/
│   │   │   ├── ScanButton.jsx
│   │   │   ├── FiltersPanel.jsx
│   │   │   ├── SignalCard.jsx
│   │   │   ├── PriceChart.jsx
│   │   │   ├── TickerMarquee.jsx
│   │   │   ├── HistoryList.jsx
│   │   │   └── ui/               # Shadcn primitives
│   │   ├── lib/
│   │   │   └── api.js            # Cliente axios
│   │   └── index.css             # Tema dark, fontes, animações
│   ├── tailwind.config.js
│   └── package.json
├── memory/
│   └── PRD.md                    # Product requirements (vivo)
└── README.md                     # Este arquivo
```

---

## 🔌 API Reference

Todas as rotas são prefixadas com `/api`.

### `GET /api/`
Health check.
```json
{ "status": "ok", "app": "PULSE Smart Trader" }
```

### `GET /api/movers?exchange=okx&market_type=futures&top=12`
Top gainers e losers nas últimas 24h.
```json
{
  "gainers": [{ "symbol": "BTCUSDT", "last_price": 79000, "change_pct": 3.5, "volume_quote": 2.5e9 }],
  "losers":  [{ "symbol": "...", "last_price": ..., "change_pct": -5.2, "volume_quote": ... }]
}
```

### `GET /api/klines?exchange=okx&market_type=futures&symbol=BTCUSDT&interval=1h&limit=200`
Candles OHLCV ordenados do mais antigo ao mais recente.

### `POST /api/scan`
**O endpoint principal.**

Request:
```json
{
  "exchange": "okx",          // "okx" | "binance"
  "market_type": "futures",   // "futures" | "spot"  (binance só aceita spot)
  "timeframe": "short",       // "scalp" | "short" | "long"
  "minutes_to_entry": 5       // 3-60
}
```

Response (parcial):
```json
{
  "id": "uuid",
  "symbol": "DOGEUSDT",
  "exchange": "okx",
  "market_type": "futures",
  "interval": "1h",
  "direction": "SHORT",
  "score": 60.0,
  "entry": 0.11172,
  "stop_loss": 0.113347,
  "take_profit": 0.108466,
  "risk_reward": 2.0,
  "leverage_suggestion": "3x - 5x",
  "horizon": "4h - 1 dia",
  "entry_time": "2026-02-16T05:09:36+00:00",
  "indicators": { "rsi": 38.63, "macd_hist": -8.8e-05, "ema20": 0.1129, ... },
  "justification": "Viés de baixa moderado: preço abaixo das EMA20/50 e MACD hist negativo...",
  "confidence": "MEDIA",
  "key_level": "0.1133 (EMA50)",
  "alert": "Fechamento de 1h acima de 0.1133 invalida o viés short.",
  "klines": [ /* 200 candles para o gráfico */ ]
}
```

### `GET /api/signals?limit=50`
Histórico de sinais (mais recentes primeiro).

### `DELETE /api/signals/{id}`
Remove um sinal do histórico.

---

## 🎚️ Configuração de prazo

| Timeframe | Interval | Horizonte | SL (× ATR) | TP (× ATR) | Alavancagem |
|---|---|---|---|---|---|
| **Scalp** | 5m | 15min – 2h | 1.0 | 1.8 | 5x – 10x |
| **Curto** | 1h | 4h – 1 dia | 1.5 | 3.0 | 3x – 5x |
| **Longo** | 4h | 3 – 14 dias | 2.0 | 5.0 | 1x – 3x |

---

## ⚙️ Variáveis de ambiente

`/app/backend/.env`:
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=test_database
CORS_ORIGINS=*
OPENAI_API_KEY=sk-proj-...     # chave do dono — usada primeiro
EMERGENT_LLM_KEY=sk-emergent-... # fallback
```

`/app/frontend/.env`:
```
REACT_APP_BACKEND_URL=https://<seu-app>.preview.emergentagent.com
```

> A função `enrich_signal` prefere `OPENAI_API_KEY` quando presente; senão usa `EMERGENT_LLM_KEY`.

---

## ▶️ Como rodar localmente (dev)

Pré-requisitos: Python 3.11, Node 20, MongoDB rodando local.

```bash
# Backend
cd /app/backend
pip install -r requirements.txt
uvicorn server:app --reload --host 0.0.0.0 --port 8001

# Frontend
cd /app/frontend
yarn install
yarn start
```

No container Emergent o supervisor já cuida disso — só `sudo supervisorctl restart backend` quando mexer no `.env`.

---

## 🗺️ Roadmap

### Fase 1 — MVP ✅ (concluída)
- [x] Scanner OKX (perpetuals + spot) + Binance Spot
- [x] Análise técnica algorítmica (RSI/MACD/EMA/ATR/BB)
- [x] Enriquecimento via GPT-5.2
- [x] UI dark estilo terminal
- [x] Gráfico ao vivo com SL/Entry/TP
- [x] Histórico persistido
- [x] Countdown até a hora de entrada

### Fase 2 — Próximas (a definir por ordem do operador)
- [ ] Botão "Abrir no TradingView" no card do sinal
- [ ] Retornar Top 3 oportunidades por scan (não só a melhor)
- [ ] Alertas push via Telegram/Webhook quando confiança = ALTA
- [ ] Scanner de Forex / US stocks via Alpha Vantage (precisa API key)
- [ ] Custom risk: tamanho de conta % + max leverage do trader
- [ ] Modo "auto-scan" — varre a cada N minutos e notifica
- [ ] Backtest do setup (taxa de acerto histórica em padrões similares)
- [ ] Multi-timeframe confluence (confirma 1h com 4h e 15m)

### Fase 3 — Avançada
- [ ] Conexão opcional com conta Bybit/OKX via API key (modo leitura — saldo, posições)
- [ ] Calculadora de tamanho de posição baseada em % de risco da conta
- [ ] Funding rate awareness para perpétuos (penaliza sinais com funding adverso)
- [ ] Sentimento de mercado (fear & greed, social listening) como input extra

---

## ⚠️ Aviso

Pulse Trade é uma **ferramenta de assistência técnica**, não recomendação de investimento. Toda decisão de execução, gestão de risco e tamanho de posição é responsabilidade exclusiva do operador. Trading com alavancagem pode resultar em perda total do capital.

---

## 📜 Versão

**v1.0.0** — Fevereiro/2026

Built with focus, not flash.
