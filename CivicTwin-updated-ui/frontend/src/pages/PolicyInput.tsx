import { useNavigate } from "react-router-dom";
import { Crt } from "@/components/Crt";
import { TopBar } from "@/components/TopBar";
import { Loading, Failed, Prose, Stat } from "@/components/ui";
import { useRun } from "@/lib/useRun";

export function PolicyInput() {
  const { run, error } = useRun();
  const navigate = useNavigate();

  if (error) return <Crt><TopBar /><Failed message={error} /></Crt>;
  if (!run) return <Crt><TopBar /><Loading what="the scenario" /></Crt>;

  const p = run.policy;

  return (
    <Crt>
      <TopBar meta={`SYNTHETIC N=${run.personas.length} SEED ${run.seed}`} />

      <div className="grid-split" style={{ flexGrow: 1, display: "grid", gridTemplateColumns: "1.05fr .95fr", minHeight: 0 }}>
        {/* ---- what you wrote ---- */}
        <section
          style={{
            padding: "var(--s-5) var(--s-5) var(--s-5) var(--s-6)", display: "flex", flexDirection: "column",
            gap: "var(--s-4)", borderRight: "1px solid var(--rule)", overflowY: "auto",
          }}
        >
          <div>
            <h1
              className="t1"
              style={{
                fontSize: "var(--fs-28)", fontWeight: 500, lineHeight: 1.12,
                letterSpacing: ".02em", margin: "0 0 13px",
              }}
            >
              SAY IT IN PLAIN ENGLISH
            </h1>
            <Prose style={{ fontSize: "var(--fs-16)", maxWidth: "54ch" }}>
              CivicTwin turns it into something it can simulate. You check that reading
              before anything runs.
            </Prose>
          </div>

          <div className="box" style={{ padding: "var(--s-3)", fontSize: "var(--fs-16)", lineHeight: 1.7, minHeight: 140 }}>
            <span className="t1">{p.text}</span>
            <span className="caret t1">_</span>
          </div>

          <div style={{ display: "flex", gap: "var(--s-2)", alignItems: "center", flexWrap: "wrap" }}>
            <button className="btn" onClick={() => navigate("/simulation")}>INTERPRET PROPOSAL</button>
            <button className="btn-ghost">ENTER FIELDS DIRECTLY</button>
          </div>

          <div
            style={{
              marginTop: "auto", borderTop: "1px solid var(--rule)", paddingTop: 20,
              display: "grid", gridTemplateColumns: "repeat(4,minmax(0,1fr))", gap: "var(--s-3)",
            }}
          >
            <Stat label="personas" value={run.personas.length.toLocaleString()} />
            <Stat label="study area" value={run.study_area} />
            <Stat label="seed" value={String(run.seed)} />
            <Stat label="rounds" value={`0-${run.rounds}`} />
          </div>
        </section>

        {/* ---- how it read you. reasoning, not JSON. ---- */}
        <section style={{ padding: "var(--s-5) var(--s-6) var(--s-5) var(--s-5)", display: "flex", flexDirection: "column", gap: "var(--s-3)", overflowY: "auto" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span className="t1" style={{ fontSize: "var(--fs-16)", fontWeight: 600 }}>
              How CivicTwin read this
            </span>
            <span
              className="gold"
              style={{ fontSize: "var(--fs-12)", border: "1px solid var(--rule-strong)", padding: "2px 8px" }}
            >
              SCHEMA VALID
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 15 }}>
            {p.reading.map((step) => (
              <div key={step.n} style={{ display: "flex", gap: 12 }}>
                <span
                  className={step.assumed ? "alert" : "gold"}
                  style={{ fontSize: "var(--fs-12)", flexShrink: 0, paddingTop: 2 }}
                >
                  {step.n}
                </span>
                <div>
                  <div className="t1" style={{ fontSize: "var(--fs-14)" }}>{step.claim}</div>
                  <div className="t3" style={{ fontSize: "var(--fs-12)", lineHeight: 1.5, marginTop: 3 }}>
                    {step.why}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* the machine-facing form stays one row away, not a wall of it */}
          <div className="box" style={{ display: "flex", alignItems: "center", gap: "var(--s-2)", padding: "11px 14px" }}>
            <span className="t3" style={{ fontSize: "var(--fs-12)" }}>Structured output</span>
            <span className="t3" style={{ fontSize: "var(--fs-12)" }}>
              PolicyChange · {p.modifications.remove_stops.length} stops removed · schema valid
            </span>
            <div style={{ flexGrow: 1 }} />
            <span className="gold" style={{ fontSize: "var(--fs-12)", cursor: "pointer" }}>View JSON</span>
          </div>

          <div>
            {p.resolved_entities.map((e, i) => (
              <div
                key={e.ref}
                style={{
                  display: "flex", justifyContent: "space-between", padding: "10px 0",
                  borderBottom: i < p.resolved_entities.length - 1 ? "1px solid var(--rule-dim)" : undefined,
                }}
              >
                <span className="t2" style={{ fontSize: "var(--fs-14)" }}>{e.label}</span>
                <span className="t3" style={{ fontSize: "var(--fs-12)" }}>{e.ref}</span>
              </div>
            ))}
          </div>

          <div className="box" style={{ padding: "14px 16px" }}>
            <div className="t1" style={{ fontSize: "var(--fs-14)", fontWeight: 600 }}>
              Check this reading before running
            </div>
            <div className="t2" style={{ fontSize: "var(--fs-14)", lineHeight: 1.55, marginTop: 4 }}>
              The interpretation is model-generated. Correct any field here, or enter them
              yourself. Nothing is simulated until you run it.
            </div>
          </div>

          <div style={{ marginTop: "auto", display: "flex", gap: "var(--s-2)", alignItems: "center" }}>
            <button className="btn" onClick={() => navigate("/simulation")}>RUN BASELINE SIMULATION</button>
            <span className="t3" style={{ fontSize: "var(--fs-12)" }}>
              {run.personas.length.toLocaleString()} personas
            </span>
          </div>
        </section>
      </div>
    </Crt>
  );
}
