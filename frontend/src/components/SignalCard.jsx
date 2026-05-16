import React, { useEffect, useState } from "react";
import { ArrowUpRight, ArrowDownRight, Target, ShieldCheck, Stack, Clock, WarningCircle } from "@phosphor-icons/react";

const fmt = (n, d = 4) => {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  return Number(n).toLocaleString(undefined, { maximumFractionDigits: d, minimumFractionDigits: Math.min(2, d) });
};

const useCountdown = (target) => {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  if (!target) return null;
  const diff = new Date(target).getTime() - now;
  if (diff <= 0) return "AGORA";
  const m = Math.floor(diff / 60000);
  const s = Math.floor((diff % 60000) / 1000);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
};

const Metric = ({ label, value, accent, mono = true, testId }) => (
  <div className="flex flex-col gap-1" data-testid={testId}>
    <span className="overline">{label}</span>
    <span className={`${mono ? "font-mono" : "font-heading"} text-lg ${accent || "text-white"}`}>{value}</span>
  </div>
);

export const SignalCard = ({ signal }) => {
  const countdown = useCountdown(signal?.entry_time);

  if (!signal) {
    return (
      <div data-testid="signal-card-empty" className="relative border border-border rounded-sm bg-surface/60 min-h-[420px] flex flex-col items-center justify-center text-center p-8 overflow-hidden">
        <div className="absolute inset-0 grid-bg opacity-40" />
        <div className="relative z-10 max-w-md flex flex-col items-center gap-4">
          <div className="size-14 rounded-full border border-electric/40 flex items-center justify-center animate-pulse">
            <div className="size-2 rounded-full bg-electric animate-flicker" />
          </div>
          <h2 className="font-heading text-2xl tracking-tight">Aguardando varredura</h2>
          <p className="text-sm text-muted-foreground max-w-sm">
            Configure o mercado, o prazo e clique em <span className="text-white">VARRER MERCADO</span>. O motor analisa volume, momentum, tendência e volatilidade em paralelo e trava na melhor oportunidade.
          </p>
          <div className="overline text-muted-foreground/60 pt-2">PULSE · v1.0</div>
        </div>
      </div>
    );
  }

  const isLong = signal.direction === "LONG";
  const dirColor = isLong ? "text-long" : "text-short";
  const dirBg = isLong ? "bg-long/15 border-long/40" : "bg-short/15 border-short/40";
  const Icon = isLong ? ArrowUpRight : ArrowDownRight;
  const confColor = signal.confidence === "ALTA" ? "text-long" : signal.confidence === "BAIXA" ? "text-short" : "text-yellow-400";

  return (
    <div data-testid="signal-card" className="relative border border-border rounded-sm bg-surface/80 backdrop-blur-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-5 border-b border-border">
        <div className="flex items-center gap-3">
          <div className={`px-3 py-1.5 border ${dirBg} rounded-sm flex items-center gap-2`}>
            <Icon size={18} weight="bold" className={dirColor} />
            <span className={`font-heading font-bold tracking-widest text-sm ${dirColor}`} data-testid="signal-direction">{signal.direction}</span>
          </div>
          <div className="flex flex-col">
            <span className="font-heading text-2xl tracking-tight" data-testid="signal-symbol">{signal.symbol}</span>
            <span className="overline">{signal.exchange.toUpperCase()} · {signal.market_type.toUpperCase()} · {signal.interval}</span>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className="overline">entrar em</span>
          <span data-testid="signal-countdown" className="font-mono text-2xl text-electric tabular-nums">{countdown || "—"}</span>
          <span className="overline text-muted-foreground/70">{signal.entry_time ? new Date(signal.entry_time).toLocaleTimeString() : ""}</span>
        </div>
      </div>

      {/* Price grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6 p-5 border-b border-border">
        <Metric label="ENTRADA" testId="metric-entry" value={fmt(signal.entry, 6)} />
        <Metric label="STOP LOSS" testId="metric-sl" value={fmt(signal.stop_loss, 6)} accent="text-short" />
        <Metric label="TAKE PROFIT" testId="metric-tp" value={fmt(signal.take_profit, 6)} accent="text-long" />
        <Metric label="RISCO / RETORNO" testId="metric-rr" value={`1 : ${fmt(signal.risk_reward, 2)}`} />
      </div>

      {/* Meta grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6 p-5 border-b border-border">
        <div className="flex flex-col gap-1">
          <span className="overline flex items-center gap-1"><Stack size={11} weight="bold" /> ALAVANCAGEM</span>
          <span data-testid="signal-leverage" className="font-mono text-base text-white">{signal.leverage_suggestion}</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="overline flex items-center gap-1"><Clock size={11} weight="bold" /> HORIZONTE</span>
          <span className="font-mono text-base">{signal.horizon}</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="overline flex items-center gap-1"><ShieldCheck size={11} weight="bold" /> CONFIANÇA</span>
          <span data-testid="signal-confidence" className={`font-mono text-base ${confColor}`}>{signal.confidence} · {signal.score}/100</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="overline flex items-center gap-1"><Target size={11} weight="bold" /> NÍVEL-CHAVE</span>
          <span className="font-mono text-base text-zinc-300">{signal.key_level || "—"}</span>
        </div>
      </div>

      {/* AI Justification */}
      <div className="p-5 space-y-3">
        <div className="flex items-center gap-2">
          <span className="overline">análise técnica · ia</span>
          <div className="flex-1 h-px bg-border" />
        </div>
        <div data-testid="signal-justification" className="terminal p-3 rounded-sm">
          <span className="text-electric">$</span> {signal.justification}
        </div>
        {signal.alert && (
          <div data-testid="signal-alert" className="flex items-start gap-2 text-xs text-yellow-300/90">
            <WarningCircle size={14} weight="bold" className="mt-0.5 flex-none" />
            <span>{signal.alert}</span>
          </div>
        )}
        <details className="text-xs text-muted-foreground">
          <summary className="cursor-pointer hover:text-white" data-testid="indicators-toggle">indicadores brutos</summary>
          <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-3 font-mono">
            {signal.indicators && Object.entries(signal.indicators).map(([k, v]) => (
              <div key={k} className="flex justify-between border-b border-border/50 py-1">
                <span className="text-zinc-500">{k}</span>
                <span className="text-zinc-200">{fmt(v, 6)}</span>
              </div>
            ))}
          </div>
        </details>
      </div>
    </div>
  );
};

export default SignalCard;
