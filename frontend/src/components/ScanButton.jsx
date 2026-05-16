import React from "react";
import { Crosshair, CircleNotch } from "@phosphor-icons/react";

export const ScanButton = ({ onClick, loading, disabled }) => {
  return (
    <div className="flex flex-col items-center gap-3 py-2">
      <button
        data-testid="scan-button"
        onClick={onClick}
        disabled={loading || disabled}
        className={`group tracing-beam relative inline-flex items-center justify-center gap-3 px-12 py-6 rounded-sm
          bg-black text-white font-heading font-bold text-xl tracking-tight uppercase
          transition-all duration-200
          hover:bg-zinc-900 active:scale-[0.98]
          disabled:opacity-60 disabled:cursor-not-allowed
          min-w-[320px]
          ${loading ? "animate-pulse-glow" : ""}`}
      >
        {loading ? (
          <>
            <CircleNotch size={22} weight="bold" className="animate-spin" />
            <span>varrendo mercado…</span>
          </>
        ) : (
          <>
            <Crosshair size={26} weight="duotone" className="text-long group-hover:text-electric transition-colors" />
            <span>VARRER MERCADO</span>
          </>
        )}
        {loading && (
          <div className="absolute inset-0 overflow-hidden pointer-events-none rounded-sm">
            <div className="absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-electric/30 to-transparent animate-scan-sweep" />
          </div>
        )}
      </button>
      <p className="overline text-muted-foreground/70" data-testid="scan-helper">
        {loading ? "analisando indicadores em tempo real" : "clique para iniciar a varredura"}
      </p>
    </div>
  );
};

export default ScanButton;
