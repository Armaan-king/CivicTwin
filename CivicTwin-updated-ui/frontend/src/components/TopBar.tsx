import { Link, NavLink } from "react-router-dom";
import { transportLabel } from "@/lib/config";

const STEPS = [
  { to: "/policy", label: "Policy" },
  { to: "/simulation", label: "Simulation" },
  { to: "/impact", label: "Impact" },
  { to: "/voices", label: "Voices" },
  { to: "/interventions", label: "Interventions" },
  { to: "/calibration", label: "Calibration" },
  { to: "/system", label: "System" },
];

export function TopBar({ meta }: { meta?: string }) {
  return (
    <header
      style={{
        display: "flex", alignItems: "center", gap: 18, padding: "0 22px",
        height: 50, borderBottom: "1px solid var(--rule)", flexShrink: 0,
      }}
    >
      <Link
        to="/"
        aria-label="CivicTwin home"
        className="gold"
        style={{
          fontWeight: 600, fontSize: "var(--fs-14)", letterSpacing: ".16em",
          textDecoration: "none",
        }}
      >
        CIVICTWIN
      </Link>
      <span style={{ width: 1, height: 16, background: "var(--rule)" }} />
      <nav style={{ display: "flex", gap: 2 }}>
        {STEPS.map((s) => (
          <NavLink
            key={s.to}
            to={s.to}
            style={({ isActive }) => ({
              padding: "5px 12px",
              fontSize: "var(--fs-14)",
              textDecoration: "none",
              color: isActive ? "var(--ground)" : "var(--t3)",
              background: isActive ? "var(--gold)" : "transparent",
              fontWeight: isActive ? 600 : 400,
            })}
          >
            {s.label}
          </NavLink>
        ))}
      </nav>
      <div style={{ flexGrow: 1 }} />
      {/* synthetic provenance is never hidden. AGENTS.md section 16. */}
      <span className="t3" style={{ fontSize: "var(--fs-12)" }}>
        {meta ?? "SYNTHETIC"}
      </span>
      <span
        className="t3"
        style={{ fontSize: "var(--fs-12)", border: "1px solid var(--rule)", padding: "2px 7px" }}
        title="Where this screen's data came from"
      >
        {transportLabel()}
      </span>
    </header>
  );
}
