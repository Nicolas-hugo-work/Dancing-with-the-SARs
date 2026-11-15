"use client";

import { useMemo, useState } from "react";
import {
  ArrowUpRight,
  Check,
  ChevronRight,
  Layers,
  Search,
} from "lucide-react";

import type { District } from "@/data/districts";

type SidebarProps = {
  city: string;
  districts: readonly District[];
  selectedDistrict: number;
  onSelectDistrict: (districtId: number) => void;
};

export default function Sidebar({
  city,
  districts,
  selectedDistrict,
  onSelectDistrict,
}: SidebarProps) {
  const [query, setQuery] = useState("");

  const filteredDistricts = useMemo(() => {
    const normalized = query.trim().toLowerCase();

    if (!normalized) {
      return districts;
    }

    return districts.filter(
      (district) =>
        district.label.toLowerCase().includes(normalized) ||
        district.zone.toLowerCase().includes(normalized) ||
        district.code.toLowerCase().includes(normalized),
    );
  }, [districts, query]);

  return (
    <aside
      aria-label={`Selección de distritos de ${city}`}
      className="panel-texture panel-texture-topography fixed bottom-24 left-4 top-28 z-40 flex w-80 max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl border border-[#184C32]/15 bg-[#EAE8DD]/90 p-6 shadow-2xl shadow-[#184C32]/20 backdrop-blur-md md:top-32"
    >
      <div className="relative z-10 flex min-h-0 flex-1 flex-col">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="flex items-center gap-2 text-[9px] font-extrabold uppercase tracking-[0.22em] text-[#184C32]/60">
              <span aria-hidden="true" className="h-1.5 w-1.5 bg-[#184C32]" />
              Observatorio territorial
            </p>
            <h2 className="mt-2.5 font-display text-[27px] leading-none text-[#184C32]">
              Distritos
            </h2>
            <p className="mt-2 text-[10px] font-bold uppercase tracking-[0.12em] text-[#184C32]/60">
              {city} · {districts.length} unidades
            </p>
          </div>

          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-[#184C32] bg-[#184C32] text-[#F2E4DD]">
            <Layers
              className="h-[18px] w-[18px]"
              strokeWidth={1.8}
              aria-hidden="true"
            />
          </span>
        </div>

        {/* Buscador */}
        <label className="group relative mt-5 block">
          <span className="sr-only">Buscar distrito</span>
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#184C32]/50 transition-all duration-300 group-focus-within:text-celeste-500"
            strokeWidth={1.9}
            aria-hidden="true"
          />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar distrito o zona"
            className="h-10 w-full rounded-lg border border-[#184C32]/20 bg-transparent pl-9 pr-3 text-xs font-bold text-[#184C32] outline-none transition-all duration-300 placeholder:font-semibold placeholder:text-[#184C32]/45 hover:border-[#184C32]/40 focus:border-celeste-500 focus:bg-celeste-500/5"
          />
        </label>

        <div className="mt-5 flex items-center justify-between px-0.5">
          <span className="text-[9px] font-extrabold uppercase tracking-[0.2em] text-[#184C32]/60">
            Listado
          </span>
          <span className="rounded-sm border border-[#184C32]/20 px-2 py-0.5 text-[9px] font-extrabold tabular-nums text-[#184C32]">
            {String(filteredDistricts.length).padStart(2, "0")} /{" "}
            {String(districts.length).padStart(2, "0")}
          </span>
        </div>

        {/* Lista de distritos */}
        <ul className="scrollbar-soft -mr-2 mt-2 min-h-0 flex-1 space-y-1 overflow-y-auto overscroll-contain pr-2">
          {filteredDistricts.map((district) => {
            const isActive = selectedDistrict === district.id;

            return (
              <li key={district.id}>
                <button
                  type="button"
                  onClick={() => onSelectDistrict(district.id)}
                  aria-pressed={isActive}
                  className={`group flex w-full items-center gap-3 border-l-4 px-2.5 py-2 text-left transition-all duration-300 ${
                    isActive
                      ? "border-celeste-500 bg-celeste-500/10 text-celeste-700"
                      : "border-transparent text-[#184C32] hover:border-celeste-500/50 hover:bg-celeste-500/5"
                  }`}
                >
                  <span
                    className={`grid h-8 w-8 shrink-0 place-items-center rounded-sm border text-[10px] font-extrabold tabular-nums transition-all duration-300 ${
                      isActive
                        ? "border-celeste-500 bg-celeste-500 text-[#0F3021]"
                        : "border-[#184C32]/20 bg-transparent text-[#184C32] group-hover:border-celeste-500 group-hover:text-celeste-600"
                    }`}
                  >
                    {district.code}
                  </span>

                  <span className="min-w-0 flex-1">
                    <span
                      className={`block truncate text-[12px] font-extrabold ${
                        isActive ? "text-celeste-700" : "text-[#184C32]"
                      }`}
                    >
                      {district.label}
                    </span>
                    <span
                      className={`mt-0.5 block truncate text-[9px] font-bold uppercase tracking-[0.12em] ${
                        isActive
                          ? "text-celeste-700/70"
                          : "text-[#184C32]/50"
                      }`}
                    >
                      {district.zone}
                    </span>
                  </span>

                  {isActive ? (
                    <Check
                      className="h-4 w-4 shrink-0 text-celeste-600"
                      strokeWidth={2.4}
                      aria-hidden="true"
                    />
                  ) : (
                    <ChevronRight
                      className="h-4 w-4 shrink-0 text-[#184C32]/30 transition-all duration-300 group-hover:translate-x-0.5 group-hover:text-celeste-500"
                      strokeWidth={1.9}
                      aria-hidden="true"
                    />
                  )}
                </button>
              </li>
            );
          })}
        </ul>

        {filteredDistricts.length === 0 && (
          <div className="mt-4 rounded-lg border border-dashed border-[#184C32]/30 bg-[#184C32]/5 px-4 py-5 text-center">
            <p className="text-[11px] font-extrabold text-[#184C32]">
              Sin resultados
            </p>
            <p className="mt-1 text-[10px] font-semibold text-[#184C32]/60">
              Prueba con “Distrito 3” o “D03”.
            </p>
          </div>
        )}

        <button
          type="button"
          className="mt-4 flex h-11 w-full shrink-0 items-center justify-between rounded-xl border border-[#184C32]/15 bg-[#4DB8D6] px-4 text-[#0F3021] shadow-lg shadow-[#184C32]/20 transition-all duration-300 hover:-translate-y-0.5 hover:bg-[#35A5C4] hover:shadow-xl hover:shadow-[#184C32]/25 active:translate-y-0 active:bg-[#2F96B3] active:shadow-md"
        >
          <span className="text-[10px] font-extrabold uppercase tracking-[0.16em]">
            Ver análisis
          </span>
          <ArrowUpRight
            className="h-4 w-4"
            strokeWidth={2}
            aria-hidden="true"
          />
        </button>
        <p className="mt-2 text-center text-[8px] font-bold uppercase tracking-[0.14em] text-[#184C32]/50">
          Selecciona un distrito para explorar su ficha
        </p>
        <p className="mt-1 text-center text-[7px] font-bold uppercase tracking-[0.12em] text-[#184C32]/40 sm:hidden">
          Mapa © Esri · DeLorme · NAVTEQ
        </p>
      </div>
    </aside>
  );
}
