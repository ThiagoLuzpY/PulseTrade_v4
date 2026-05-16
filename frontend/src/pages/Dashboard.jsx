import React, { useEffect, useMemo, useState } from "react";
import { Toaster, toast } from "sonner";
import { Pulse, Sparkle } from "@phosphor-icons/react";
import { api } from "@/lib/api";
import TickerMarquee from "@/components/TickerMarquee";
import FiltersPanel from "@/components/FiltersPanel";
import ScanButton from "@/components/ScanButton";
import SignalCard from "@/components/SignalCard";
import PriceChart from "@/components/PriceChart";
import HistoryList from "@/components/HistoryList";

const DEFAULT_FILTERS = {
  exchange: "okx",
  market_type: "futures",
  timeframe: "short",
  minutes_to_entry: 5,
};

export default function Dashboard() {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [loading, setLoading] = useState(false);
  const [signal, setSignal] = useState(null);
  const [klines, setKlines] = useState([]);
  const [history, setHistory] = useState([]);

  const loadHistory = async () => {
    try {
      const data = await api.signals(50);
      setHistory(data.signals || []);
    } catch (e) { /* silent */ }
  };

  useEffect(() => { loadHistory(); }, []);

  const handleScan = async () => {
    setLoading(true);
    setSignal(null);
    setKlines([]);
    toast.loading("Varrendo mercado…", { id: "scan", description: `${filters.exchange.toUpperCase()} · ${filters.market_type} · ${filters.timeframe}` });
    try {
      const data = await api.scan(filters);
      const { klines: kl, ...sig } = data;
      setSignal(sig);
      setKlines(kl || []);
      toast.success(`Oportunidade encontrada: ${sig.symbol} ${sig.direction}`, { id: "scan" });
      loadHistory();
    } catch (e) {
      const msg = e?.response?.data?.detail || e.message || "Falha ao varrer mercado";
      toast.error(msg, { id: "scan" });
    } finally {
      setLoading(false);
    }
  };

  const handleSelectHistory = async (s) => {
    setSignal(s);
    try {
      const data = await api.klines({ exchange: s.exchange, market_type: s.market_type, symbol: s.symbol, interval: s.interval, limit: 200 });
      setKlines(data.klines || []);
    } catch (e) { /* silent */ }
  };

  const handleDelete = async (s) => {
    await api.deleteSignal(s.id);
    toast.success("Sinal removido");
    loadHistory();
    if (signal?.id === s.id) { setSignal(null); setKlines([]); }
  };

  const subtitle = useMemo(() => {
    const map = { scalp: "scalp · 5min", short: "curto prazo · 1h", long: "longo prazo · 4h" };
    return map[filters.timeframe] || "";
  }, [filters.timeframe]);

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <Toaster theme="dark" position="top-right" toastOptions={{ className: "font-mono text-xs" }} />

      {/* Header */}
      <header className="sticky top-0 z-30 border-b border-border bg-black/80 backdrop-blur-md">
        <div className="max-w-[1600px] mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <Pulse size={28} weight="duotone" className="text-electric" />
              <span className="absolute -right-1 -bottom-1 size-2 rounded-full bg-long animate-pulse" />
            </div>
            <div className="flex items-baseline gap-2">
              <h1 className="font-heading font-black text-2xl tracking-tighter">PULSE</h1>
              <span className="overline text-muted-foreground/70 hidden sm:inline">SMART TRADER · {subtitle}</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden md:flex items-center gap-2 text-xs font-mono text-muted-foreground">
              <Sparkle size={12} weight="bold" className="text-long" />
              motor: análise técnica + IA
            </span>
            <span className="overline text-electric border border-electric/40 px-2 py-1 rounded-sm" data-testid="status-live">● LIVE</span>
          </div>
        </div>
        <TickerMarquee exchange={filters.exchange} market_type={filters.market_type} />
      </header>

      {/* Main */}
      <main className="flex-1 max-w-[1600px] mx-auto w-full px-6 py-8 space-y-6">
        {/* Filters + Scan */}
        <section className="space-y-5">
          <FiltersPanel filters={filters} setFilters={setFilters} disabled={loading} />
          <div className="flex items-center justify-center">
            <ScanButton onClick={handleScan} loading={loading} />
          </div>
        </section>

        {/* Signal + Chart */}
        <section className="grid grid-cols-1 lg:grid-cols-5 gap-5">
          <div className="lg:col-span-3">
            <SignalCard signal={signal} />
          </div>
          <div className="lg:col-span-2 min-h-[420px]">
            <PriceChart
              klines={klines}
              symbol={signal?.symbol}
              direction={signal?.direction}
              entry={signal?.entry}
              stop_loss={signal?.stop_loss}
              take_profit={signal?.take_profit}
            />
          </div>
        </section>

        {/* History */}
        <section>
          <HistoryList signals={history} onSelect={handleSelectHistory} onDelete={handleDelete} />
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border py-4 px-6 mt-6">
        <div className="max-w-[1600px] mx-auto flex flex-col md:flex-row md:items-center md:justify-between gap-2 text-xs">
          <span className="font-mono text-muted-foreground" data-testid="footer-disclaimer">
            Análise técnica assistida por IA. Decisão final, gestão de risco e execução são responsabilidade exclusiva do operador.
          </span>
          <span className="font-mono text-muted-foreground/70">PULSE · v1.0 · feed okx/binance em tempo real</span>
        </div>
      </footer>
    </div>
  );
}
