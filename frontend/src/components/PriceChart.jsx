import React, { useEffect, useRef } from "react";
import { createChart, CandlestickSeries } from "lightweight-charts";

export const PriceChart = ({ klines, symbol, direction, entry, stop_loss, take_profit }) => {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      layout: { background: { color: "transparent" }, textColor: "#A1A1AA", fontFamily: "JetBrains Mono" },
      localization: { locale: "en-US" },
      grid: { vertLines: { color: "#1f1f23" }, horzLines: { color: "#1f1f23" } },
      rightPriceScale: { borderColor: "#27272a" },
      timeScale: { borderColor: "#27272a", timeVisible: true, secondsVisible: false },
      crosshair: { mode: 1 },
      autoSize: true,
    });
    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#00C853",
      downColor: "#FF3B30",
      borderUpColor: "#00C853",
      borderDownColor: "#FF3B30",
      wickUpColor: "#00C853",
      wickDownColor: "#FF3B30",
    });
    chartRef.current = chart;
    seriesRef.current = series;
    return () => { chart.remove(); chartRef.current = null; seriesRef.current = null; };
  }, []);

  useEffect(() => {
    if (!seriesRef.current || !klines || klines.length === 0) return;
    const data = klines.map((k) => ({
      time: Math.floor(k.open_time / 1000),
      open: k.open, high: k.high, low: k.low, close: k.close,
    }));
    seriesRef.current.setData(data);

    // Add price lines for entry/SL/TP if provided
    try {
      // Clear previous price lines is not directly exposed; recreate by setting markers instead.
      seriesRef.current.setMarkers([]);
    } catch (e) { /* noop */ }
    const lines = [];
    if (entry) lines.push({ price: Number(entry), color: "#007AFF", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "ENTRY" });
    if (stop_loss) lines.push({ price: Number(stop_loss), color: "#FF3B30", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "SL" });
    if (take_profit) lines.push({ price: Number(take_profit), color: "#00C853", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "TP" });
    // remove previous price lines
    if (seriesRef.current._pulse_lines) {
      seriesRef.current._pulse_lines.forEach((pl) => { try { seriesRef.current.removePriceLine(pl); } catch (e) {} });
    }
    seriesRef.current._pulse_lines = lines.map((l) => seriesRef.current.createPriceLine(l));
    chartRef.current?.timeScale().fitContent();
  }, [klines, entry, stop_loss, take_profit]);

  return (
    <div data-testid="price-chart" className="border border-border rounded-sm bg-surface/60 overflow-hidden flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="size-1.5 rounded-full bg-long animate-pulse" />
          <span className="font-heading text-sm tracking-tight">{symbol || "—"}</span>
          <span className="overline">tempo real</span>
        </div>
        {direction && (
          <span className={`overline ${direction === "LONG" ? "text-long" : "text-short"}`}>{direction}</span>
        )}
      </div>
      <div ref={containerRef} className="flex-1 min-h-[320px]" />
    </div>
  );
};

export default PriceChart;
