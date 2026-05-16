"""AI analyst using Emergent LLM Key (OpenAI GPT-5.2) to produce concise, fast trade justifications."""
from __future__ import annotations
import os
import uuid
import json
from typing import Dict, Any
from emergentintegrations.llm.chat import LlmChat, UserMessage


SYSTEM_PROMPT = (
    "Você é um analista de trading sênior especialista em criptomoedas, futuros perpétuos, forex e ações. "
    "Seu trabalho é validar e refinar sinais técnicos gerados algoritmicamente. Seja extremamente conciso e direto. "
    "Resposta SEMPRE em português, JSON estrito conforme schema. Sem rodeios, sem disclaimers genéricos. "
    "Avalie a confluência dos indicadores, mencione o nível-chave mais importante (suporte/resistência ou EMA) e "
    "indique se a operação tem confluência forte, média ou fraca. Máximo 3 frases na justificativa."
)


async def enrich_signal(signal: Dict[str, Any]) -> Dict[str, Any]:
    """Add AI-generated justification, confidence, and final notes to a signal."""
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        signal["justification"] = "Análise técnica algorítmica (IA desativada)."
        signal["confidence"] = "MEDIA"
        return signal

    ind = signal.get("indicators", {})
    user_text = (
        f"Sinal técnico para validar:\n"
        f"Par: {signal['symbol']} ({signal['exchange']} {signal['market_type']})\n"
        f"Direção sugerida: {signal['direction']} | Score: {signal['score']}/100\n"
        f"Preço atual / entrada: {signal['entry']}\n"
        f"Stop loss: {signal['stop_loss']} | Take profit: {signal['take_profit']} | RR: {signal['risk_reward']}\n"
        f"Timeframe: {signal['interval']} | Horizonte: {signal['horizon']}\n"
        f"Indicadores: RSI={ind.get('rsi')}, MACD_hist={ind.get('macd_hist')}, "
        f"EMA20={ind.get('ema20')}, EMA50={ind.get('ema50')}, EMA200={ind.get('ema200')}, "
        f"ATR={ind.get('atr')}, Volume_ratio={ind.get('volume_ratio')}, "
        f"Swing_high={ind.get('swing_high')}, Swing_low={ind.get('swing_low')}, "
        f"BB_upper={ind.get('bb_upper')}, BB_lower={ind.get('bb_lower')}\n\n"
        "Responda APENAS com JSON válido neste schema:\n"
        "{\n"
        '  "justification": "máx 3 frases explicando a confluência técnica",\n'
        '  "confidence": "ALTA" | "MEDIA" | "BAIXA",\n'
        '  "key_level": "nível-chave a observar (preço numérico ou conceito curto)",\n'
        '  "alert": "alerta ou condição que invalidaria o setup, máx 1 frase"\n'
        "}"
    )

    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"signal-{uuid.uuid4()}",
            system_message=SYSTEM_PROMPT,
        ).with_model("openai", "gpt-5.2")

        resp = await chat.send_message(UserMessage(text=user_text))
        text = str(resp).strip()
        # Strip potential code fences
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        data = json.loads(text)
        signal["justification"] = data.get("justification", "")
        signal["confidence"] = data.get("confidence", "MEDIA")
        signal["key_level"] = data.get("key_level", "")
        signal["alert"] = data.get("alert", "")
    except Exception as e:
        signal["justification"] = (
            f"Análise algorítmica: confluência {'forte' if signal['score'] >= 70 else 'média'} "
            f"em RSI {ind.get('rsi')}, MACD {'positivo' if (ind.get('macd_hist') or 0) > 0 else 'negativo'}, "
            f"preço {'acima' if signal['direction']=='LONG' else 'abaixo'} da EMA20."
        )
        signal["confidence"] = "ALTA" if signal["score"] >= 70 else ("MEDIA" if signal["score"] >= 50 else "BAIXA")
        signal["key_level"] = str(ind.get("swing_high") if signal["direction"] == "LONG" else ind.get("swing_low"))
        signal["alert"] = f"Setup invalida se preço fechar {'abaixo do stop loss' if signal['direction']=='LONG' else 'acima do stop loss'}."
        signal["ai_error"] = str(e)

    return signal
