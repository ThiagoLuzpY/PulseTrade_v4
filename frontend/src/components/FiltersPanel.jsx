import React from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Lightning, ChartLineUp, Calendar } from "@phosphor-icons/react";

const Field = ({ label, icon: Icon, children, testId }) => (
  <label className="flex flex-col gap-1.5" data-testid={`field-${testId}`}>
    <span className="overline flex items-center gap-1.5">
      {Icon ? <Icon size={11} weight="bold" /> : null}
      {label}
    </span>
    {children}
  </label>
);

export const FiltersPanel = ({ filters, setFilters, disabled }) => {
  const update = (key) => (val) => {
    const next = { ...filters, [key]: val };
    // Binance Spot only (Binance Futures is geo-blocked from server region)
    if (next.exchange === "binance") next.market_type = "spot";
    setFilters(next);
  };

  return (
    <div data-testid="filters-panel" className="grid grid-cols-2 md:grid-cols-4 gap-4 p-5 border border-border bg-surface/60 rounded-sm">
      <Field label="Exchange" testId="exchange">
        <Select value={filters.exchange} onValueChange={update("exchange")} disabled={disabled}>
          <SelectTrigger data-testid="select-exchange" className="rounded-sm bg-black/40 border-border h-10 font-mono text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="rounded-sm">
            <SelectItem value="okx" data-testid="opt-okx">OKX · Spot + Perpétuos</SelectItem>
            <SelectItem value="binance" data-testid="opt-binance">Binance · Spot</SelectItem>
          </SelectContent>
        </Select>
      </Field>

      <Field label="Mercado" icon={ChartLineUp} testId="market_type">
        <Select value={filters.market_type} onValueChange={update("market_type")} disabled={disabled || filters.exchange === "binance"}>
          <SelectTrigger data-testid="select-market-type" className="rounded-sm bg-black/40 border-border h-10 font-mono text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="rounded-sm">
            <SelectItem value="futures" data-testid="opt-futures" disabled={filters.exchange === "binance"}>
              Futuros Perpétuos
            </SelectItem>
            <SelectItem value="spot" data-testid="opt-spot">Spot</SelectItem>
          </SelectContent>
        </Select>
      </Field>

      <Field label="Prazo da Operação" icon={Calendar} testId="timeframe">
        <Select value={filters.timeframe} onValueChange={update("timeframe")} disabled={disabled}>
          <SelectTrigger data-testid="select-timeframe" className="rounded-sm bg-black/40 border-border h-10 font-mono text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="rounded-sm">
            <SelectItem value="scalp" data-testid="opt-scalp">Scalp · 5m → minutos</SelectItem>
            <SelectItem value="short" data-testid="opt-short">Curto · 1h → horas/dia</SelectItem>
            <SelectItem value="long" data-testid="opt-long">Longo · 4h → dias/semanas</SelectItem>
          </SelectContent>
        </Select>
      </Field>

      <Field label="Entrada em (min)" icon={Lightning} testId="minutes">
        <Select value={String(filters.minutes_to_entry)} onValueChange={(v) => update("minutes_to_entry")(Number(v))} disabled={disabled}>
          <SelectTrigger data-testid="select-minutes" className="rounded-sm bg-black/40 border-border h-10 font-mono text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="rounded-sm">
            {[3, 5, 10, 15, 30].map((m) => (
              <SelectItem key={m} value={String(m)} data-testid={`opt-min-${m}`}>{m} minutos</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </Field>
    </div>
  );
};

export default FiltersPanel;
