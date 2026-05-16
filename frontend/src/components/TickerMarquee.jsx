import React, { useEffect, useState } from "react";
import Marquee from "react-fast-marquee";
import { api } from "@/lib/api";
import { TrendUp, TrendDown } from "@phosphor-icons/react";

export const TickerMarquee = ({ exchange = "binance", market_type = "futures" }) => {
  const [items, setItems] = useState([]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await api.movers(exchange, market_type, 14);
        if (cancelled) return;
        const all = [...(data.gainers || []), ...(data.losers || [])];
        // de-dupe by symbol
        const map = new Map();
        all.forEach((x) => map.set(x.symbol, x));
        setItems(Array.from(map.values()));
      } catch (e) {
        // silent fail; show empty marquee
      }
    };
    load();
    const id = setInterval(load, 20000);
    return () => { cancelled = true; clearInterval(id); };
  }, [exchange, market_type]);

  if (items.length === 0) {
    return (
      <div data-testid="ticker-marquee-loading" className="h-9 border-y border-border/60 bg-black/60 flex items-center px-4">
        <span className="overline text-muted-foreground/60">conectando ao feed…</span>
      </div>
    );
  }

  return (
    <div data-testid="ticker-marquee" className="h-9 border-y border-border/60 bg-black/60 backdrop-blur-sm overflow-hidden">
      <Marquee speed={40} gradient={false} pauseOnHover>
        {items.map((t) => {
          const up = t.change_pct >= 0;
          return (
            <span key={t.symbol} className="inline-flex items-center gap-2 px-4 py-2 font-mono text-xs">
              <span className="text-zinc-300">{t.symbol}</span>
              <span className="text-zinc-500">{Number(t.last_price).toLocaleString(undefined, { maximumFractionDigits: 6 })}</span>
              <span className={`inline-flex items-center gap-1 ${up ? "text-long" : "text-short"}`}>
                {up ? <TrendUp size={12} weight="bold" /> : <TrendDown size={12} weight="bold" />}
                {up ? "+" : ""}{Number(t.change_pct).toFixed(2)}%
              </span>
              <span className="text-zinc-700">·</span>
            </span>
          );
        })}
      </Marquee>
    </div>
  );
};

export default TickerMarquee;
