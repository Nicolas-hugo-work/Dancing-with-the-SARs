export type AlertSeverity = "low" | "medium" | "high" | "extreme";

export type Alert = {
  id: string;
  title: string;
  description: string;
  severity: AlertSeverity;
  districtId: number;
  districtLabel: string;
  category: string;
  /**
   * Minutos transcurridos desde la emisión de la alerta.
   * Un valor positivo representa un evento ya registrado.
   */
  timeOffset: number;
  protocol?: string[];
};

export const ALERTS: readonly Alert[] = [
  {
    id: "alert-extreme-d15",
    title: "Riesgo inminente de desborde",
    description:
      "El nivel del río Rocha supera el umbral crítico tras las lluvias de las últimas horas. La zona baja del Distrito 15 presenta anegamiento activo y requiere intervención inmediata.",
    severity: "extreme",
    districtId: 15,
    districtLabel: "Distrito 15 · Zona Sur",
    category: "Hidrológica",
    timeOffset: 4,
    protocol: [
      "1. Activar unidades de rescate SAR",
      "2. Evacuación preventiva de la zona baja",
      "3. Despliegue de maquinaria pesada",
    ],
  },
  {
    id: "alert-high-d04",
    title: "Saturación hídrica en laderas",
    description:
      "La humedad del suelo supera el 82 % en sectores de pendiente pronunciada. Se recomienda monitoreo continuo de grietas y taludes.",
    severity: "high",
    districtId: 4,
    districtLabel: "Distrito 4 · Muyurina",
    category: "Remoción en masa",
    timeOffset: 18,
  },
  {
    id: "alert-medium-d09",
    title: "Ascenso del nivel freático",
    description:
      "Los sensores registran un incremento sostenido del nivel freático en la zona de Temporal. Mantener vigilancia sobre sótanos y drenajes.",
    severity: "medium",
    districtId: 9,
    districtLabel: "Distrito 9 · Temporal",
    category: "Hidrología",
    timeOffset: 42,
  },
  {
    id: "alert-low-d07",
    title: "Material particulado moderado",
    description:
      "La calidad del aire se mantiene en rango aceptable, con un leve incremento de partículas en horas de mayor tráfico.",
    severity: "low",
    districtId: 7,
    districtLabel: "Distrito 7 · Villa Busch",
    category: "Calidad del aire",
    timeOffset: 75,
  },
];

export function formatAlertTime(timeOffset: number): string {
  if (timeOffset === 0) {
    return "Ahora";
  }

  const minutes = Math.abs(timeOffset);

  if (minutes < 60) {
    return timeOffset > 0 ? `Hace ${minutes} min` : `En ${minutes} min`;
  }

  const hours = Math.floor(minutes / 60);
  return timeOffset > 0 ? `Hace ${hours} h` : `En ${hours} h`;
}
