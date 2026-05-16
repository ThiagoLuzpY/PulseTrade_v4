import React from "react";
import { ArrowUpRight, ArrowDownRight, Sparkle, CircleNotch } from "@phosphor-icons/react";

export const CandidatesBar = ({ candidates, selectedIdx, onSelect, enrichingIdx }) => {
  if (!candidates || candidates.length === 0) return null;

  return (
    <div
      data-testid="candidates-bar"
      className="flex items-center gap-2 overflow-x-auto pb-1 -mx-1 px-1 scroll-smooth snap-x"
    >
      <span className="overline text-muted-foreground/70 whitespace-nowrap pr-2 hidden sm:inline">
        oportunidades
      </span>
      {candidates.map((c, idx) => {
        const isSelected = idx === selectedIdx;
        const isLong = c.direction === "LONG";
        const Icon = isLong ? ArrowUpRight : ArrowDownRight;
        const dirColor = isLong ? "text-long" : "text-short";
        const dirBg = isLong ? "border-long/40" : "border-short/40";
        const isEnriching = enrichingIdx === idx;

        return (
          <button
            key={c.id}
            data-testid={`candidate-chip-${idx}`}
            onClick={() => onSelect(idx)}
            className={`group flex-none snap-start rounded-sm border px-3 py-2 flex items-center gap-2 transition-all duration-150
              ${isSelected
                ? `bg-white/[0.06] border-electric/60 ring-1 ring-electric/40`
                : `bg-black/40 ${dirBg} hover:bg-white/[0.04] hover:border-white/30`
              }`}
          >
            <span className={`font-mono text-xs font-bold ${isSelected ? "text-electric" : "text-muted-foreground"}`}>
              {idx + 1}º
            </span>
            <Icon size={14} weight="bold" className={dirColor} />
            <span className="font-heading text-sm tracking-tight whitespace-nowrap">{c.symbol}</span>
            <span className={`font-mono text-[10px] uppercase tracking-wider ${dirColor}`}>{c.direction}</span>
            <span className="font-mono text-xs text-zinc-400">{Math.round(c.score)}</span>
            {isEnriching ? (
              <CircleNotch size={12} weight="bold" className="animate-spin text-electric" />
            ) : c.ai_enriched ? (
              <Sparkle size={12} weight="duotone" className="text-long" />
            ) : (
              <span className="text-[10px] text-muted-foreground/60 hidden md:inline">tap p/ análise IA</span>
            )}
          </button>
        );
      })}
    </div>
  );
};

export default CandidatesBar;
