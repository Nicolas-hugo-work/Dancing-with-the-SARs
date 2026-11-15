"use client";

import { useEffect, useRef } from "react";
import { Compass, LocateFixed, Minus, Plus } from "lucide-react";
import { latLngBounds } from "leaflet";
import {
  MapContainer,
  Polygon,
  TileLayer,
  Tooltip,
  useMap,
} from "react-leaflet";

import { CITY_CENTER, type MapSector } from "@/data/districts";

type MapComponentProps = {
  sectors: readonly MapSector[];
  selectedSector: MapSector;
  extremeSectorIds: readonly number[];
  onSelectDistrict: (districtId: number) => void;
};

const CELESTE = "#4DB8D6";
const EXTREME_RED = "#DC2626";

function MapFocus({ sector }: { sector: MapSector }) {
  const map = useMap();
  const previousSectorId = useRef(sector.id);

  useEffect(() => {
    // La vista inicial es el encuadre limpio de Cochabamba.
    // El zoom suave se reserva para una selección real del usuario.
    if (previousSectorId.current === sector.id) {
      return;
    }

    previousSectorId.current = sector.id;
    const isWide = window.matchMedia("(min-width: 768px)").matches;
    const hasAlertsPanel = window.matchMedia("(min-width: 1024px)").matches;

    map.flyToBounds(latLngBounds(sector.polygon), {
      paddingTopLeft: isWide ? [360, 136] : [28, 128],
      paddingBottomRight: hasAlertsPanel
        ? [360, 104]
        : isWide
          ? [48, 104]
          : [28, 104],
      maxZoom: 15,
      duration: 0.9,
    });
  }, [sector, map]);

  return null;
}

function MapControls() {
  const map = useMap();

  return (
    <div className="absolute right-4 top-28 z-[1000] hidden flex-col items-center gap-2 sm:flex md:top-32 lg:right-[21.5rem]">
      <div className="flex flex-col overflow-hidden rounded-xl border border-[#184C32]/15 bg-[#F2E4DD]/90 shadow-xl shadow-[#184C32]/20 backdrop-blur-md">
        <button
          type="button"
          aria-label="Acercar mapa"
          title="Acercar"
          onClick={() => map.zoomIn()}
          className="group grid h-9 w-9 place-items-center text-[#184C32] transition-all duration-300 hover:bg-celeste-500/10"
        >
          <Plus
            className="h-4 w-4 transition-all duration-300 group-hover:text-celeste-500"
            strokeWidth={2}
            aria-hidden="true"
          />
        </button>
        <span aria-hidden="true" className="mx-2 h-px bg-[#184C32]/15" />
        <button
          type="button"
          aria-label="Alejar mapa"
          title="Alejar"
          onClick={() => map.zoomOut()}
          className="group grid h-9 w-9 place-items-center text-[#184C32] transition-all duration-300 hover:bg-celeste-500/10"
        >
          <Minus
            className="h-4 w-4 transition-all duration-300 group-hover:text-celeste-500"
            strokeWidth={2}
            aria-hidden="true"
          />
        </button>
      </div>

      <button
        type="button"
        aria-label="Centrar mapa en Cochabamba"
        title="Centrar en Cochabamba"
        onClick={() => map.flyTo(CITY_CENTER, 13, { duration: 0.8 })}
        className="group grid h-9 w-9 place-items-center rounded-xl border border-[#184C32]/15 bg-[#F2E4DD]/90 text-[#184C32] shadow-xl shadow-[#184C32]/20 backdrop-blur-md transition-all duration-300 hover:bg-celeste-500/10"
      >
        <LocateFixed
          className="h-[17px] w-[17px] transition-all duration-300 group-hover:text-celeste-500"
          strokeWidth={1.9}
          aria-hidden="true"
        />
      </button>

      <span className="grid h-9 w-9 place-items-center rounded-xl border border-[#184C32]/15 bg-[#F2E4DD]/90 text-[#184C32]/70 shadow-xl shadow-[#184C32]/20 backdrop-blur-md">
        <Compass
          className="h-[17px] w-[17px]"
          strokeWidth={1.7}
          aria-hidden="true"
        />
      </span>
    </div>
  );
}

export default function MapComponent({
  sectors,
  selectedSector,
  extremeSectorIds,
  onSelectDistrict,
}: MapComponentProps) {
  return (
    <div
      role="region"
      aria-label="Mapa interactivo de Cochabamba con sectores de prueba"
      className="absolute inset-0 z-0 overflow-hidden bg-[#F8F3EF]"
    >
      <MapContainer
        center={CITY_CENTER}
        zoom={13}
        minZoom={11}
        maxZoom={16}
        zoomControl={false}
        attributionControl={false}
        scrollWheelZoom
        worldCopyJump
        className="h-full w-full"
      >
        {/* Esri Light Gray Canvas: tiles públicos, sin API key. */}
        <TileLayer
          attribution='&copy; <a href="https://www.esri.com/">Esri</a> &mdash; Esri, DeLorme, NAVTEQ'
          url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
        />

        {sectors.map((sector) => {
          const isActive = sector.id === selectedSector.id;
          const isExtreme = extremeSectorIds.includes(sector.id);
          const strokeColor = isExtreme ? EXTREME_RED : CELESTE;

          return (
            <Polygon
              key={sector.id}
              positions={sector.polygon}
              pathOptions={{
                color: strokeColor,
                weight: isExtreme ? 3 : isActive ? 3 : 2,
                opacity: isExtreme ? 1 : isActive ? 1 : 0.78,
                fillColor: strokeColor,
                // Equivalente Leaflet de fill-red-600/60.
                fillOpacity: isExtreme ? 0.6 : isActive ? 0.16 : 0.05,
                dashArray: isExtreme ? undefined : isActive ? undefined : "6 5",
                className: isExtreme
                  ? "district-polygon district-polygon-extreme"
                  : "district-polygon",
              }}
              eventHandlers={{
                click: () => onSelectDistrict(sector.id),
              }}
            >
              <Tooltip sticky className="district-tooltip">
                {sector.label} · {sector.zone}
                {isExtreme ? " · Alerta extrema" : ""}
              </Tooltip>
            </Polygon>
          );
        })}

        <MapFocus sector={selectedSector} />
        <MapControls />
      </MapContainer>

      <div className="absolute bottom-24 right-4 z-[1000] hidden flex-col items-end gap-1.5 sm:flex lg:right-[21.5rem]">
        <span className="inline-flex items-center gap-2 rounded-lg border border-[#184C32]/15 bg-[#F2E4DD]/90 px-3 py-1.5 text-[9px] font-extrabold uppercase tracking-[0.16em] text-[#184C32] shadow-lg shadow-[#184C32]/20 backdrop-blur-md">
          <span className="h-1.5 w-1.5 rounded-full bg-[#184C32]" />
          17°23′S · 66°09′O
        </span>
        <span className="text-[8px] font-bold uppercase tracking-[0.1em] text-[#184C32]/55">
          © Esri · DeLorme · NAVTEQ
        </span>
      </div>
    </div>
  );
}
