import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Crt } from "@/components/Crt";
import { TopBar } from "@/components/TopBar";
import { Heading, Loading, Failed, Note } from "@/components/ui";
import { useRun } from "@/lib/useRun";
import type { Intervention, SimulationRun } from "@/types/simulation";

interface Column {
  key: string;
  name: string;
  journey: number;
  severe: number;
  carers: number;
  completion: number | null;
  disparity: number;
  cost: number;
  newlyHarmed: number | null;
}

function columns(run: SimulationRun): Column[] {
  const base: Column = {
    key: "baseline", name: "Baseline",
    journey: run.metrics.overall.avg_journey_time_delta,
    severe: run.metrics.overall.severe_harm_count,
    carers: run.outcomes.filter((o) => o.second_order).length,
    completion: run.metrics.overall.essential_trip_completion,
    disparity: run.metrics.subgroup_disparity_pp,
    cost: run.metrics.operating_cost_index,
    newlyHarmed: null,
  };
  const alts = run.interventions
    .filter((i): i is Intervention & { metrics: NonNullable<Intervention["metrics"]> } => i.valid && !!i.metrics)
    .map((i) => ({
      key: i.intervention_id, name: i.name,
      journey: i.metrics.avg_journey_time_delta,
      severe: i.metrics.severe_harm_count,
      carers: i.carers_harmed ?? 0,
      completion: i.metrics.essential_trip_completion,
      disparity: i.subgroup_disparity_pp ?? 0,
      cost: i.estimated_cost_index,
      newlyHarmed: i.newly_harmed_elsewhere ?? 0,
    }));
  return [base, ...alts];
}

type RowSpec = {
  label: string;
  get: (c: Column) => string;
  /** lower is better for harm rows, so tone flips */
  tone: (c: Column, cols: Column[]) => "gold" | "alert" | "t2";
};

const ROWS: RowSpec[] = [
  {
    label: "Mean journey time", get: (c) => `${c.journey.toFixed(1)} min`,
    tone: (c) => (c.journey < 0 ? "gold" : "alert"),
  },
  {
    label: "Severe harm", get: (c) => String(c.severe),
    tone: (c, all) => (c.severe === Math.min(...all.map((x) => x.severe)) ? "gold"
      : c.severe > all[0].severe * 0.6 ? "alert" : "t2"),
  },
  {
    label: "Carers harmed", get: (c) => String(c.carers),
    tone: (c, all) => (c.carers === Math.min(...all.map((x) => x.carers)) ? "gold"
      : c.carers > all[0].carers * 0.6 ? "alert" : "t2"),
  },
  {
    label: "Essential trips completed",
    get: (c) => (c.completion === null ? "n/a" : `${(c.completion * 100).toFixed(1)}%`),
    tone: (c, all) => (c.completion !== null && c.completion === Math.max(...all.map((x) => x.completion ?? 0)) ? "gold" : "t2"),
  },
  {
    label: "Cohort disparity", get: (c) => `${c.disparity.toFixed(1)} pp`,
    tone: (c, all) => (c.disparity === Math.min(...all.map((x) => x.disparity)) ? "gold"
      : c.disparity > all[0].disparity * 0.6 ? "alert" : "t2"),
  },
  {
    label: "Operating cost", get: (c) => `${c.cost.toFixed(2)}x`,
    tone: (c) => (c.cost > 1.2 ? "alert" : c.cost <= 1.0 ? "gold" : "t2"),
  },
  {
    label: "Newly harmed elsewhere",
    get: (c) => (c.newlyHarmed === null ? "—" : String(c.newlyHarmed)),
    tone: (c) => ((c.newlyHarmed ?? 0) > 0 ? "alert" : "t2"),
  },
];

export function InterventionLab() {
  const { run, error } = useRun();
  const navigate = useNavigate();
  const [picked, setPicked] = useState<string | null>(null);

  if (error) return <Crt><TopBar /><Failed message={error} /></Crt>;
  if (!run) return <Crt><TopBar /><Loading what="the alternatives" /></Crt>;

  const cols = columns(run);
  const generated = run.interventions.length;
  const valid = run.interventions.filter((i) => i.valid).length;
  const tradeoff = run.interventions.find((i) => (i.newly_harmed_elsewhere ?? 0) > 0);

  return (
    <Crt>
      <TopBar meta={`${generated} GENERATED · ${valid} VALID · SAME SEED`} />

      <div className="grid-split" style={{ flexGrow: 1, display: "grid", gridTemplateColumns: "336px 1fr", minHeight: 0 }}>
        {/* ---- candidates, rejections included ---- */}
        <section style={{ borderRight: "1px solid var(--rule)", padding: "var(--s-4)", display: "flex", flexDirection: "column", overflowY: "auto" }}>
          <Heading style={{ marginBottom: 7 }}>CANDIDATES</Heading>
          <p className="t3" style={{ fontSize: "var(--fs-12)", lineHeight: 1.5, margin: "0 0 14px" }}>
            Chosen from five defined action types. The planner cannot invent a new one.
          </p>

          {run.interventions.map((i, idx) => (
            <div
              key={i.intervention_id}
              className={idx === 0 ? "box" : undefined}
              style={{
                padding: idx === 0 ? "13px 15px" : "13px 0",
                background: idx === 0 ? "rgba(242,176,36,.055)" : undefined,
                marginBottom: idx === 0 ? 9 : 0,
                borderTop: idx === 0 ? undefined : "1px solid var(--rule-dim)",
                opacity: i.valid ? 1 : 0.62,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8 }}>
                <span className={i.valid ? "t1" : "t2"} style={{ fontSize: "var(--fs-14)", fontWeight: 600 }}>
                  {i.name}
                </span>
                <span className={i.valid ? "gold" : "alert"} style={{ fontSize: "var(--fs-12)", flexShrink: 0 }}>
                  {i.valid ? "SIMULATED" : "REJECTED"}
                </span>
              </div>
              <div className="t3" style={{ fontSize: "var(--fs-12)", marginTop: 4 }}>{i.kind}</div>
              {i.valid ? (
                <div className="t2" style={{ fontSize: "var(--fs-14)", lineHeight: 1.5, marginTop: 7 }}>
                  {i.rationale}
                </div>
              ) : (
                <div className="alert" style={{ fontSize: "var(--fs-12)", lineHeight: 1.5, marginTop: 6 }}>
                  {i.validation_errors[0]}
                </div>
              )}
            </div>
          ))}

          <p className="t3" style={{ fontSize: "var(--fs-12)", lineHeight: 1.55, margin: "auto 0 0", borderTop: "1px solid var(--rule)", paddingTop: 13 }}>
            Rejections are shown, not hidden. {generated - valid} of {generated} failing is a
            result, not an error.
          </p>
        </section>

        {/* ---- comparison ---- */}
        <section style={{ padding: "var(--s-5) var(--s-5)", display: "flex", flexDirection: "column", gap: "var(--s-3)", overflowY: "auto" }}>
          <div>
            <h2
              className="t1"
              style={{ fontSize: "var(--fs-28)", fontWeight: 500, lineHeight: 1.15, letterSpacing: ".015em", margin: "0 0 9px" }}
            >
              WHAT EACH ONE TRADES AWAY
            </h2>
            <p className="t2" style={{ fontSize: "var(--fs-14)", lineHeight: 1.55, margin: 0, maxWidth: "78ch" }}>
              Same population, same seed, same metric definitions. No option wins every row,
              and CivicTwin does not pick for you.
            </p>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 640 }}>
              <thead>
                <tr>
                  <th className="t3" style={{ ...th, textAlign: "left", paddingLeft: 0 }}>METRIC</th>
                  {cols.map((c, i) => (
                    <th
                      key={c.key}
                      className={i === 1 ? "t1" : "t3"}
                      style={{ ...th, fontWeight: i === 1 ? 600 : 400, paddingRight: i === cols.length - 1 ? 0 : 16 }}
                    >
                      {c.name.toUpperCase()}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ROWS.map((r, ri) => (
                  <tr key={r.label}>
                    <td
                      className="t1"
                      style={{ ...td, textAlign: "left", fontWeight: 600, borderBottom: ri === ROWS.length - 1 ? "none" : td.borderBottom }}
                    >
                      {r.label}
                    </td>
                    {cols.map((c, ci) => (
                      <td
                        key={c.key}
                        className={r.tone(c, cols)}
                        style={{
                          ...td,
                          paddingRight: ci === cols.length - 1 ? 0 : 16,
                          background: ci === 1 ? "rgba(242,176,36,.055)" : undefined,
                          fontWeight: ci === 1 ? 600 : 400,
                          borderBottom: ri === ROWS.length - 1 ? "none" : td.borderBottom,
                        }}
                      >
                        {r.get(c)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {tradeoff && (
            <Note tone="alert">
              <div className="alert" style={{ fontSize: "var(--fs-16)", fontWeight: 600 }}>
                {tradeoff.name} moves the harm, it does not remove it
              </div>
              <div className="t2" style={{ fontSize: "var(--fs-14)", lineHeight: 1.55, marginTop: 5 }}>
                It is the cheapest option on the table at {tradeoff.estimated_cost_index.toFixed(2)}×
                and it creates {tradeoff.newly_harmed_elsewhere} newly harmed riders on a corridor
                the original policy never touched. A single utility score would have hidden that.
              </div>
            </Note>
          )}

          <div
            style={{
              marginTop: "auto", borderTop: "1px solid var(--rule)", paddingTop: 18,
              display: "flex", alignItems: "center", gap: "var(--s-3)", flexWrap: "wrap",
            }}
          >
            <button className="btn" onClick={() => { setPicked(cols[1]?.key ?? null); navigate("/consultation"); }}>
              SELECT FOR CONSULTATION
            </button>
            <span className="t3" style={{ fontSize: "var(--fs-14)", lineHeight: 1.55, maxWidth: "52ch" }}>
              Publishing needs your explicit approval. CivicTwin will not choose a candidate
              or publish one on its own.
              {picked ? " Selection recorded." : ""}
            </span>
          </div>
        </section>
      </div>
    </Crt>
  );
}

const th = {
  fontSize: "var(--fs-12)", fontWeight: 400, letterSpacing: ".12em",
  textAlign: "right" as const, padding: "0 16px 11px 0",
  borderBottom: "1px solid var(--rule-strong)",
};

const td = {
  fontSize: "var(--fs-14)", textAlign: "right" as const,
  padding: "13px 16px 13px 0", borderBottom: "1px solid var(--rule-faint)",
};
