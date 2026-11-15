"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

import AlertsPanel from "@/components/alerts/AlertsPanel";
import Sidebar from "@/components/layout/Sidebar";
import TimelineBar from "@/components/layout/TimelineBar";
import TopNavbar from "@/components/layout/TopNavbar";
import { ALERTS } from "@/data/alerts";
import {
  DISTRICTS,
  MOCK_SECTORS,
  getSectorForDistrict,
} from "@/data/districts";

const MapComponent = dynamic(() => import("@/components/map/MapComponent"), {
  ssr: false,
  loading: () => (
    <div
      aria-hidden="true"
      className="absolute inset-0 z-0 bg-[#F8F3EF]"
    />
  ),
});

const TIMELINE_YEARS = [2024, 2025, 2026] as const;

const EXTREME_SECTOR_IDS = [
  ...new Set(
    ALERTS.filter((alert) => alert.severity === "extreme").map(
      (alert) => getSectorForDistrict(alert.districtId).id,
    ),
  ),
];

export default function DashboardPage() {
  const [selectedDistrictId, setSelectedDistrictId] = useState(1);
  const [alertsOpen, setAlertsOpen] = useState(false);
  const selectedDistrict =
    DISTRICTS.find((district) => district.id === selectedDistrictId) ??
    DISTRICTS[0];
  const selectedSector = getSectorForDistrict(selectedDistrict.id);

  return (
    <div className="relative h-screen overflow-hidden bg-[#F8F3EF] text-[#184C32]">
      <MapComponent
        sectors={MOCK_SECTORS}
        selectedSector={selectedSector}
        extremeSectorIds={EXTREME_SECTOR_IDS}
        onSelectDistrict={setSelectedDistrictId}
      />

      <TopNavbar
        city="Cochabamba"
        userName="QUBIX"
        alertCount={ALERTS.length}
        onAlertsClick={() => setAlertsOpen((isOpen) => !isOpen)}
      />

      <Sidebar
        city="Cochabamba"
        districts={DISTRICTS}
        selectedDistrict={selectedDistrictId}
        onSelectDistrict={setSelectedDistrictId}
      />

      <AlertsPanel
        alerts={ALERTS}
        open={alertsOpen}
        onClose={() => setAlertsOpen(false)}
      />

      <TimelineBar years={TIMELINE_YEARS} activeYear={2026} />
    </div>
  );
}
