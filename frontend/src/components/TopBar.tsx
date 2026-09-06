import { Link, useLocation } from "react-router-dom";

const STEPS = [
  { to: "/policy", label: "Policy" },
  { to: "/simulation", label: "Simulate" },
  { to: "/impact", label: "Impact" },
  // Who was harmed, then why. The deliberation is the answer to "why", so it belongs in
  // the flow between the finding and the remedy -- not as a utility link in the corner
  // that a demo never reaches.
  { to: "/voices", label: "Voices" },
  { to: "/interventions", label: "Options" },
  { to: "/consultation", label: "Consult" },
  { to: "/calibration", label: "Learn" },
];

export function TopBar({ meta }: { meta?: string }) {
  const { pathname } = useLocation();
  const current = STEPS.findIndex((step) => pathname.startsWith(step.to));

  return (
    <header className="app-topbar">
      <div className="app-topbar__main">
        <Link to="/" aria-label="CivicTwin home" className="app-topbar__brand">
          <svg viewBox="0 0 42 28" width="30" height="20" aria-hidden="true">
            <path d="M3 7h22c7 0 7 14 14 14M3 21h22c7 0 7-14 14-14" />
            <circle cx="3" cy="7" r="2.4" />
            <circle cx="3" cy="21" r="2.4" />
            <circle cx="39" cy="7" r="2.4" />
            <circle cx="39" cy="21" r="2.4" />
          </svg>
          <span>CivicTwin</span>
        </Link>
        <span className="app-topbar__meta">{meta ?? "SYNTHETIC"}</span>
        <span className="app-topbar__spacer" />
        <Link className={"app-topbar__utility" + (pathname === "/system" ? " active" : "")} to="/system">
          System
        </Link>
      </div>

      <nav className="workflow-progress" aria-label="Policy workflow">
        {STEPS.map((step, index) => {
          const state = index < current ? "complete" : index === current ? "current" : "upcoming";
          return (
            <Link
              key={step.to}
              to={step.to}
              className={"workflow-progress__step " + state}
              aria-current={state === "current" ? "step" : undefined}
            >
              <span className="workflow-progress__dot">{index < current ? "✓" : index + 1}</span>
              <span>{step.label}</span>
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
