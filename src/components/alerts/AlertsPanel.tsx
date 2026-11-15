"use client";

import { useMemo } from "react";
import {
  BellRing,
  CloudRain,
  Clock3,
  ListChecks,
  MapPin,
  ShieldCheck,
  TriangleAlert,
  X,
  type LucideIcon,
} from "lucide-react";

import {
  formatAlertTime,
  type Alert,
  type AlertSeverity,
} from "@/data/alerts";

type AlertsPanelProps = {
  alerts: readonly Alert[];
  open: boolean;
  onClose: () => void;
};

type SeverityStyle = {
  label: string;
  badge: string;
  iconWrap: string;
  iconClass: string;
  icon: LucideIcon;
};

const SEVERITY_ORDER: Record<AlertSeverity, number> = {
  extreme: 0,
  high: 1,
  medium: 2,
  low: 3,
};

const SEVERITY_STYLES: Record<AlertSeverity, SeverityStyle> = {
  extreme: {
    label: "Extremo",
    badge: "border-red-500/50 bg-red-500/10 text-red-700",
    iconWrap: "border-red-500/30 bg-red-500/10",
    iconClass: "animate-pulse text-red-500",
    icon: TriangleAlert,
  },
  high: {
    label: "Alto",
    badge: "border-[#D36E3C]/50 bg-[#D36E3C]/10 text-[#974424]",
    iconWrap: "border-[#D36E3C]/30 bg-[#D36E3C]/10",
    iconClass: "text-[#D36E3C]",
    icon: TriangleAlert,
  },
  medium: {
    label: "Medio",
    badge: "border-amber-500/40 bg-amber-500/10 text-amber-800",
    iconWrap: "border-amber-500/30 bg-amber-500/10",
    iconClass: "text-amber-600",
    icon: CloudRain,
  },
  low: {
    label: "Bajo",
    badge: "border-[#184C32]/20 bg-[#184C32]/5 text-[#184C32]",
    iconWrap: "border-[#184C32]/20 bg-[#184C32]/5",
    iconClass: "text-[#184C32]",
    icon: ShieldCheck,
  },
};

export default function AlertsPanel({
  alerts,
  open,
  onClose,
}: AlertsPanelProps) {
  const sortedAlerts = useMemo(
    () =>
      [...alerts].sort(
        (first, second) =>
          SEVERITY_ORDER[first.severity] - SEVERITY_ORDER[second.severity],
      ),
    [alerts],
  );

  const extremeCount = sortedAlerts.filter(
    (alert) => alert.severity === "extreme",
  ).length;

  return (
    <>
      {open && (
        <button
          type="button"
          aria-label="Cerrar panel de alertas"
          onClick={onClose}
          className="fixed inset-0 z-30 cursor-default bg-[#0F3021]/25 backdrop-blur-[2px] lg:hidden"
        />
      )}

      <aside
        aria-label="Panel de alertas y protocolo de emergencia"
        className={`fixed inset-x-4 top-28 bottom-24 z-40 ${
          open ? "flex" : "hidden"
        } max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl border border-[#184C32]/15 bg-[#EFE7E2]/90 p-5 shadow-2xl shadow-[#184C32]/20 backdrop-blur-md lg:inset-x-auto lg:right-4 lg:top-32 lg:bottom-24 lg:flex lg:w-80 lg:max-w-none`}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="flex items-center gap-2 text-[9px] font-extrabold uppercase tracking-[0.22em] text-[#184C32]/60">
              <span aria-hidden="true" className="h-1.5 w-1.5 bg-[#184C32]" />
              Centro de alertas
            </p>
            <h2 className="mt-2.5 font-display text-[27px] leading-none text-[#184C32]">
              Alertas
            </h2>
            <p className="mt-2 text-[10px] font-bold uppercase tracking-[0.12em] text-[#184C32]/60">
              {alerts.length} eventos activos
            </p>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              aria-label="Cerrar panel de alertas"
              onClick={onClose}
              className="grid h-10 w-10 place-items-center rounded-xl border border-[#184C32]/20 text-[#184C32] transition-all duration-300 hover:border-celeste-500 hover:bg-celeste-500/10 hover:text-celeste-600 lg:hidden"
            >
              <X className="h-4 w-4" strokeWidth={2} aria-hidden="true" />
            </button>

            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-[#184C32] bg-[#184C32] text-[#F2E4DD]">
              <BellRing
                className="h-[18px] w-[18px]"
                strokeWidth={1.8}
                aria-hidden="true"
              />
            </span>
          </div>
        </div>

        {extremeCount > 0 && (
          <div className="mt-4 flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-950/10 px-3 py-2">
            <span
              aria-hidden="true"
              className="h-1.5 w-1.5 shrink-0 animate-pulse rounded-full bg-red-500"
            />
            <p className="text-[9px] font-extrabold uppercase tracking-[0.14em] text-red-700">
              {String(extremeCount).padStart(2, "0")}{" "}
              {extremeCount === 1 ? "alerta extrema" : "alertas extremas"} ·
              protocolo activo
            </p>
          </div>
        )}

        <ul
          aria-label="Listado de alertas"
          className="scrollbar-soft -mr-2 mt-4 min-h-0 flex-1 space-y-2.5 overflow-y-auto overscroll-contain pr-2"
        >
          {sortedAlerts.map((alert) => {
            const isExtreme = alert.severity === "extreme";
            const style = SEVERITY_STYLES[alert.severity];
            const Icon = style.icon;

            return (
              <li key={alert.id}>
                <article
                  data-alert-id={alert.id}
                  data-severity={alert.severity}
                  aria-label={`${style.label}: ${alert.title}`}
                  className={`rounded-xl border p-3.5 transition-all duration-300 ${
                    isExtreme
                      ? "border-red-500/50 border-l-4 border-l-red-500 bg-red-950/20 shadow-lg shadow-red-950/10"
                      : "border-[#184C32]/15 bg-[#F7F0EB]/85 hover:border-[#184C32]/30"
                  }`}
                >
                  <div className="flex items-start gap-2.5">
                    <span
                      className={`grid h-8 w-8 shrink-0 place-items-center rounded-lg border ${style.iconWrap}`}
                    >
                      <Icon
                        className={`h-4 w-4 ${style.iconClass}`}
                        strokeWidth={2}
                        aria-hidden="true"
                      />
                    </span>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-2">
                        <h3
                          className={`text-[11px] font-extrabold leading-snug ${
                            isExtreme ? "text-red-950" : "text-[#184C32]"
                          }`}
                        >
                          {alert.title}
                        </h3>
                        <span
                          className={`shrink-0 rounded-sm border px-1.5 py-0.5 text-[7px] font-extrabold uppercase tracking-[0.12em] ${style.badge}`}
                        >
                          {style.label}
                        </span>
                      </div>

                      <p
                        className={`mt-1 flex items-center gap-1 text-[8px] font-extrabold uppercase tracking-[0.12em] ${
                          isExtreme ? "text-red-800/80" : "text-[#184C32]/55"
                        }`}
                      >
                        <MapPin
                          className="h-2.5 w-2.5 shrink-0"
                          strokeWidth={2.2}
                          aria-hidden="true"
                        />
                        <span className="truncate">
                          {alert.districtLabel} · {alert.category}
                        </span>
                      </p>

                      <p
                        className={`mt-2 text-[10px] font-semibold leading-relaxed ${
                          isExtreme ? "text-red-950/80" : "text-[#184C32]/75"
                        }`}
                      >
                        {alert.description}
                      </p>
                    </div>
                  </div>

                  {isExtreme &&
                    alert.protocol &&
                    alert.protocol.length > 0 && (
                      <div className="mt-3 border-t border-red-500/25 pt-3">
                        <p className="flex items-center gap-1.5 text-[8px] font-extrabold uppercase tracking-[0.18em] text-red-700">
                          <ListChecks
                            className="h-3 w-3"
                            strokeWidth={2.2}
                            aria-hidden="true"
                          />
                          Protocolo de acción
                        </p>
                        <ol className="mt-2 space-y-1.5">
                          {alert.protocol.map((step) => (
                            <li
                              key={step}
                              className="border-l-2 border-red-500/40 pl-2.5 text-[10px] font-semibold leading-relaxed text-red-950/85"
                            >
                              {step}
                            </li>
                          ))}
                        </ol>
                      </div>
                    )}

                  <p
                    className={`mt-2.5 flex items-center gap-1 text-[8px] font-bold uppercase tracking-[0.1em] ${
                      isExtreme ? "text-red-800/70" : "text-[#184C32]/45"
                    }`}
                  >
                    <Clock3
                      className="h-2.5 w-2.5"
                      strokeWidth={2.2}
                      aria-hidden="true"
                    />
                    {formatAlertTime(alert.timeOffset)}
                  </p>
                </article>
              </li>
            );
          })}
        </ul>

        <p className="mt-3 shrink-0 border-t border-[#184C32]/10 pt-3 text-center text-[7px] font-bold uppercase tracking-[0.14em] text-[#184C32]/45">
          Protocolo de emergencia · GAMC / SAR
        </p>
      </aside>
    </>
  );
}
