import React from "react";
import { ArrowUpRight, ArrowDownRight, Trash } from "@phosphor-icons/react";

const fmt = (n, d = 4) => {
  if (n === null || n === undefined) return "—";
  return Number(n).toLocaleString(undefined, { maximumFractionDigits: d });
};

const timeAgo = (iso) => {
  if (!iso) return "—";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s atrás`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m atrás`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h atrás`;
  return `${Math.floor(diff / 86400)}d atrás`;
};

export const HistoryList = ({ signals = [], onSelect, onDelete }) => {
  if (!signals.length) {
    return (
      <div data-testid="history-empty" className="border border-border rounded-sm p-6 bg-surface/60">
        <span className="overline">histórico</span>
        <p className="mt-2 text-sm text-muted-foreground">Nenhuma varredura ainda. Os sinais gerados aparecerão aqui.</p>
      </div>
    );
  }

  return (
    <div data-testid="history-list" className="border border-border rounded-sm bg-surface/60">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <span className="overline">histórico de sinais</span>
        <span className="overline text-muted-foreground/60">{signals.length} registro{signals.length === 1 ? "" : "s"}</span>
      </div>
      <div className="divide-y divide-border/60">
        {signals.map((s) => {
          const isLong = s.direction === "LONG";
          const Icon = isLong ? ArrowUpRight : ArrowDownRight;
          const color = isLong ? "text-long" : "text-short";
          return (
            <div
              key={s.id}
              data-testid={`history-row-${s.symbol}`}
              className="grid grid-cols-12 gap-2 px-4 py-3 items-center hover:bg-white/[0.03] cursor-pointer transition-colors"
              onClick={() => onSelect && onSelect(s)}
            >
              <div className="col-span-3 flex items-center gap-2">
                <Icon size={14} weight="bold" className={color} />
                <span className="font-heading text-sm">{s.symbol}</span>
                <span className="overline text-muted-foreground/60">{s.exchange}</span>
              </div>
              <div className="col-span-2 font-mono text-xs text-zinc-300">{fmt(s.entry, 6)}</div>
              <div className="col-span-2 font-mono text-xs text-short">{fmt(s.stop_loss, 6)}</div>
              <div className="col-span-2 font-mono text-xs text-long">{fmt(s.take_profit, 6)}</div>
              <div className="col-span-1 font-mono text-xs text-zinc-400">{s.score}</div>
              <div className="col-span-1 font-mono text-[10px] text-muted-foreground">{timeAgo(s.created_at)}</div>
              <div className="col-span-1 flex justify-end">
                <button
                  data-testid={`delete-${s.id}`}
                  onClick={(e) => { e.stopPropagation(); onDelete && onDelete(s); }}
                  className="text-muted-foreground hover:text-short transition-colors p-1"
                  aria-label="excluir"
                >
                  <Trash size={14} />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default HistoryList;
