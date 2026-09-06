import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Boundary } from "@/components/Boundary";
import { Hero } from "@/pages/Hero";
import { PolicyInput } from "@/pages/PolicyInput";
import { Simulation } from "@/pages/Simulation";
import { ImpactAudit } from "@/pages/ImpactAudit";
import { InterventionLab } from "@/pages/InterventionLab";
import { Calibration } from "@/pages/Calibration";
import { Consultation } from "@/pages/Consultation";
import { SystemMap } from "@/pages/SystemMap";
import { Voices } from "@/pages/Voices";

export function App() {
  const { pathname } = useLocation();
  return (
    <Boundary key={pathname} label="This screen">
    <Routes>
      <Route path="/" element={<Hero />} />
      <Route path="/policy" element={<PolicyInput />} />
      <Route path="/simulation" element={<Simulation />} />
      <Route path="/impact" element={<ImpactAudit />} />
      <Route path="/interventions" element={<InterventionLab />} />
      <Route path="/calibration" element={<Calibration />} />
      <Route path="/consultation" element={<Consultation />} />
      <Route path="/voices" element={<Voices />} />
      <Route path="/system" element={<SystemMap />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </Boundary>
  );
}
