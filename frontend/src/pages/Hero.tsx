import { Link } from "react-router-dom";
import { Crt } from "@/components/Crt";
import { Boundary, hasWebGL } from "@/components/Boundary";
import { Suspense, lazy } from "react";
// three.js is ~450 kB and only the hero needs it, so it never reaches the other routes
const PolicyNetwork = lazy(() =>
  import("@/components/PolicyNetwork").then((m) => ({ default: m.PolicyNetwork }))
);
import { useRun } from "@/lib/useRun";
import { secondOrderVictims } from "@/lib/run";

export function Hero() {
  const { run, outcomes, error } = useRun();

  const severe = run?.metrics.overall.severe_harm_count ?? null;
  const second = run ? secondOrderVictims(run).length : null;
  const delta = run?.metrics.overall.avg_journey_time_delta ?? null;

  return (
    <Crt>
      <div style={{ position: "absolute", inset: 0, zIndex: 0, display: "flex", alignItems: "flex-start", paddingTop: "14vh" }}>
        {run && hasWebGL() && (
          <Boundary label="The population field" fallback={null}>
          <Suspense fallback={null}>
          <PolicyNetwork
            personas={run.personas}
            outcomes={outcomes}
            edges={run.graph.edges}
            height={typeof window !== "undefined" ? Math.round(window.innerHeight * 0.92) : 860}
          />
          </Suspense>
          </Boundary>
        )}
      </div>

      <div
        style={{
          position: "relative", zIndex: 3, display: "flex", flexDirection: "column",
          padding: "38px 52px", minHeight: "100vh", boxSizing: "border-box",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 13 }}>
          <span className="gold" style={{ fontWeight: 600, fontSize: "var(--fs-14)", letterSpacing: ".16em" }}>
            CIVICTWIN
          </span>
          <span className="t3" style={{ fontSize: "var(--fs-12)" }}>POLICY STRESS TESTING</span>
        </div>

        <div style={{ marginTop: "auto", maxWidth: 920 }}>
          <h1
            className="display t1"
            style={{
              fontSize: "var(--fs-112)", lineHeight: 0.94, margin: "0 0 26px",
              letterSpacing: "-.035em",
            }}
          >
            AVERAGES
            <br />
            HIDE PEOPLE
            <span className="caret">_</span>
          </h1>

          <p className="t2" style={{ fontSize: "var(--fs-20)", lineHeight: 1.55, margin: "0 0 30px", maxWidth: "64ch" }}>
            Remove two bus stops and the city gets faster on average. CivicTwin finds the
            residents it quietly breaks, and the ones nobody counted.
          </p>

          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <Link to="/simulation" className="btn" style={{ textDecoration: "none" }}>
              RUN A POLICY
            </Link>
            <a href="#method" className="btn-ghost" style={{ textDecoration: "none" }}>
              SEE THE METHOD
            </a>
            <span className="t3" style={{ fontSize: "var(--fs-12)", marginLeft: "var(--s-1)" }}>
              drag to turn the population
            </span>
          </div>
        </div>

        <div style={{ marginTop: 40, borderTop: "1px solid var(--rule)", paddingTop: 18 }}>
          {error && (
            <p className="alert" style={{ fontSize: "var(--fs-16)", margin: 0 }}>
              {error}. The run fixture could not be read, so no figures are shown.
            </p>
          )}
          {!run && !error && (
            <p className="t3" style={{ fontSize: "var(--fs-16)", margin: 0 }}>
              Loading the run<span className="caret">_</span>
            </p>
          )}
          {run && (
            <p className="t2" style={{ fontSize: "var(--fs-16)", lineHeight: 1.65, margin: 0, maxWidth: "104ch" }}>
              A synthetic population of {run.personas.length.toLocaleString()}, built from
              Singapore open transport data. The policy moves the average journey by{" "}
              <span className="gold" style={{ fontWeight: 600 }}>
                {delta !== null ? `${delta > 0 ? "+" : ""}${delta.toFixed(1)} min` : "n/a"}
              </span>{" "}
              and severely harms{" "}
              <span className="alert" style={{ fontWeight: 600 }}>{severe} people</span>, of whom{" "}
              <span className="alert" style={{ fontWeight: 600 }}>{second}</span> are harmed only
              because of who they look after.
            </p>
          )}
        </div>
      </div>
    </Crt>
  );
}
