import { Link } from "react-router-dom";
import { Crt } from "@/components/Crt";
import { Boundary, hasWebGL } from "@/components/Boundary";
import { Suspense, lazy, useEffect, useState } from "react";
// three.js is ~450 kB and only the hero needs it, so it never reaches the other routes
const PopulationField = lazy(() =>
  import("@/components/PopulationField").then((m) => ({ default: m.PopulationField }))
);
import { useRun } from "@/lib/useRun";
import { secondOrderVictims } from "@/lib/run";

export function Hero() {
  const { run, outcomes, error } = useRun();

  // The canvas needs a pixel height, and a window that changes size must not leave a
  // field sized for the old one. Reading it once at module scope also broke server-side
  // and first-paint sizing, which is why this is state rather than an inline expression.
  const [viewport, setViewport] = useState(
    typeof window !== "undefined" ? window.innerHeight : 860
  );
  useEffect(() => {
    const onResize = () => setViewport(window.innerHeight);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const severe = run?.metrics.overall.severe_harm_count ?? null;
  const second = run ? secondOrderVictims(run).length : null;
  const delta = run?.metrics.overall.avg_journey_time_delta ?? null;

  return (
    <Crt>
      {/* The visual is inset rather than pushed down. It used to sit 14vh from the top at
          92vh tall, which is 106% of the viewport: the bottom of the field was always
          below the fold, and on a short window most of it was. Filling the space and
          letting the canvas centre itself is both simpler and correct at any height. */}
      <div style={{ position: "absolute", inset: 0, zIndex: 0, display: "flex",
                    alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
        {run && hasWebGL() && (
          <Boundary label="The population" fallback={null}>
          <Suspense fallback={null}>
          <PopulationField
            personas={run.personas}
            outcomes={outcomes}
            height={viewport}
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
