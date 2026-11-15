import type { LatLngTuple } from "leaflet";

export const CITY_CENTER: LatLngTuple = [-17.3895, -66.1568];

export type District = {
  id: number;
  code: string;
  label: string;
  zone: string;
};

export type MapSector = District & {
  polygon: LatLngTuple[];
};

/**
 * Lista completa del panel lateral.
 * Los datos territoriales reales se conectarán más adelante.
 */
export const DISTRICTS: readonly District[] = [
  { id: 1, code: "D01", label: "Distrito 1", zone: "Cercado" },
  { id: 2, code: "D02", label: "Distrito 2", zone: "Cala Cala" },
  { id: 3, code: "D03", label: "Distrito 3", zone: "Queru Queru" },
  { id: 4, code: "D04", label: "Distrito 4", zone: "Muyurina" },
  { id: 5, code: "D05", label: "Distrito 5", zone: "Tupuraya" },
  { id: 6, code: "D06", label: "Distrito 6", zone: "Aeropuerto" },
  { id: 7, code: "D07", label: "Distrito 7", zone: "Villa Busch" },
  { id: 8, code: "D08", label: "Distrito 8", zone: "Allalay" },
  { id: 9, code: "D09", label: "Distrito 9", zone: "Temporal" },
  { id: 10, code: "D10", label: "Distrito 10", zone: "Alto Obrajes" },
  { id: 11, code: "D11", label: "Distrito 11", zone: "Coña Coña" },
  { id: 12, code: "D12", label: "Distrito 12", zone: "Villa Coronilla" },
  { id: 13, code: "D13", label: "Distrito 13", zone: "Ceres" },
  { id: 14, code: "D14", label: "Distrito 14", zone: "Valle Hermoso" },
  { id: 15, code: "D15", label: "Distrito 15", zone: "Zona Sur" },
];

/**
 * Solo tres polígonos de prueba para mantener el mapa interactivo.
 * No representan límites oficiales.
 */
export const MOCK_SECTORS: readonly MapSector[] = [
  {
    id: 1,
    code: "S01",
    label: "Sector Centro",
    zone: "Polígono mock",
    polygon: [
      [-17.3775, -66.169],
      [-17.373, -66.153],
      [-17.3815, -66.143],
      [-17.395, -66.147],
      [-17.4005, -66.1615],
      [-17.39, -66.172],
    ],
  },
  {
    id: 2,
    code: "S02",
    label: "Sector Norte",
    zone: "Polígono mock",
    polygon: [
      [-17.356, -66.169],
      [-17.3525, -66.151],
      [-17.364, -66.1415],
      [-17.376, -66.1475],
      [-17.3775, -66.167],
      [-17.367, -66.176],
    ],
  },
  {
    id: 3,
    code: "S03",
    label: "Sector Sur",
    zone: "Polígono mock",
    polygon: [
      [-17.396, -66.174],
      [-17.3985, -66.158],
      [-17.3945, -66.1455],
      [-17.411, -66.14],
      [-17.4235, -66.152],
      [-17.4195, -66.169],
    ],
  },
];

/**
 * Relaciona los 15 distritos del panel con los 3 sectores mock del mapa.
 * Es un puente temporal hasta cargar los polígonos reales.
 */
export function getSectorForDistrict(districtId: number): MapSector {
  const index = (Math.max(1, districtId) - 1) % MOCK_SECTORS.length;
  return MOCK_SECTORS[index] ?? MOCK_SECTORS[0];
}
