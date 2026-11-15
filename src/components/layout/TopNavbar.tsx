"use client";

import { Bell, ChevronDown, MapPin, UserRound } from "lucide-react";

type TopNavbarProps = {
  city: string;
  userName: string;
  alertCount?: number;
  onAlertsClick?: () => void;
};

export default function TopNavbar({
  city,
  userName,
  alertCount = 0,
  onAlertsClick,
}: TopNavbarProps) {
  return (
    <header className="panel-texture panel-texture-mountains fixed left-4 right-4 top-4 z-50 h-20 rounded-2xl border border-[#184C32]/15 bg-[#F2E4DD]/90 shadow-2xl shadow-[#184C32]/20 backdrop-blur-md md:h-24">
      <div className="relative z-10 flex h-full items-center justify-between gap-1 px-2 sm:gap-3 sm:px-5">
        {/* Marca */}
        <div className="flex min-w-0 shrink items-center">
          <img
            src="/logo-cropped.png"
            alt="PachaMetrics"
            title="PachaMetrics"
            className="h-14 w-auto max-w-full object-contain sm:h-16 md:h-[4.5rem]"
          />
        </div>

        {/* Selector de ciudad */}
        <button
          type="button"
          aria-label={`Ciudad seleccionada: ${city}`}
          title="Selector de ciudad"
          className="group hidden shrink-0 items-center gap-1.5 rounded-lg border border-[#184C32]/20 bg-transparent px-2.5 py-2 text-[#184C32] transition-all duration-300 hover:border-celeste-500 hover:bg-celeste-500/10 hover:text-celeste-700 sm:gap-2 sm:px-3.5 md:absolute md:left-1/2 md:top-1/2 md:flex md:-translate-x-1/2 md:-translate-y-1/2"
        >
          <MapPin
            className="h-3.5 w-3.5 text-[#184C32] transition-all duration-300 group-hover:text-celeste-500"
            strokeWidth={2.1}
            aria-hidden="true"
          />
          <span className="text-[9px] font-extrabold uppercase tracking-[0.14em] sm:text-[10px] sm:tracking-[0.2em]">
            <span className="sm:hidden">CBBA</span>
            <span className="hidden sm:inline">{city}</span>
          </span>
          <ChevronDown
            className="hidden h-3.5 w-3.5 text-[#184C32]/60 transition-all duration-300 group-hover:translate-y-0.5 group-hover:text-celeste-500 sm:block"
            strokeWidth={2.1}
            aria-hidden="true"
          />
        </button>

        {/* Acciones */}
        <div className="flex shrink-0 items-center gap-1 sm:gap-2">
          <span className="mr-1 hidden items-center gap-2 rounded-lg border border-[#184C32]/20 px-3 py-1.5 xl:inline-flex">
            <span className="h-1.5 w-1.5 rounded-full bg-[#184C32]" />
            <span className="text-[8px] font-extrabold uppercase tracking-[0.18em] text-[#184C32]">
              Sistema activo
            </span>
          </span>

          <button
            type="button"
            aria-label="Abrir panel de alertas"
            title="Panel de alertas"
            onClick={onAlertsClick}
            className="group relative grid h-10 w-10 place-items-center rounded-lg border border-transparent text-[#184C32] transition-all duration-300 hover:border-celeste-500/30 hover:bg-celeste-500/10 sm:h-11 sm:w-11"
          >
            <Bell
              className="h-[18px] w-[18px] transition-all duration-300 group-hover:text-celeste-500 sm:h-5 sm:w-5"
              strokeWidth={1.9}
              aria-hidden="true"
            />
            {alertCount > 0 ? (
              <span className="absolute right-1.5 top-1.5 grid h-4 min-w-4 place-items-center rounded-full bg-[#D36E3C] px-1 text-[8px] font-extrabold tabular-nums text-[#F2E4DD]">
                {alertCount}
              </span>
            ) : (
              <span className="absolute right-2.5 top-2.5 h-1.5 w-1.5 rounded-full bg-[#D36E3C]" />
            )}
          </button>

          <span
            aria-hidden="true"
            className="hidden h-8 w-px bg-[#184C32]/20 sm:block"
          />

          <button
            type="button"
            aria-label={`Perfil de ${userName}`}
            title="Usuario"
            className="group hidden items-center gap-2 rounded-lg border border-transparent py-1 pl-1 pr-1 text-[#184C32] transition-all duration-300 hover:border-celeste-500/30 hover:bg-celeste-500/10 sm:flex sm:pr-2"
          >
            <span className="grid h-10 w-10 place-items-center rounded-lg border border-[#184C32]/20 bg-transparent text-[#184C32] transition-all duration-300 group-hover:border-celeste-500 group-hover:text-celeste-500">
              <UserRound
                className="h-4 w-4"
                strokeWidth={2}
                aria-hidden="true"
              />
            </span>
            <span className="hidden text-left lg:block">
              <span className="block text-[10px] font-extrabold leading-tight text-[#184C32]">
                {userName}
              </span>
              <span className="block text-[8px] font-bold uppercase tracking-[0.16em] text-[#184C32]/60">
                Equipo
              </span>
            </span>
          </button>

          <span
            aria-hidden="true"
            className="h-10 w-px bg-[#184C32]/20 md:h-12"
          />

          <img
            src="/logop.png"
            alt="PachaMetrics"
            title="PachaMetrics"
            className="h-16 w-auto shrink-0 object-contain md:h-20"
          />
        </div>
      </div>
    </header>
  );
}
