import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Crt } from "@/components/Crt";
import { TopBar } from "@/components/TopBar";
import { Loading, Failed } from "@/components/ui";
import { useRun } from "@/lib/useRun";
import { traceToRoot } from "@/lib/run";
import type { SimEvent, SimulationRun } from "@/types/simulation";

/**
 * Two zones, not four.
 *
 * The previous version showed findings, cohort charts and a root-cause trace at once
 * across three columns plus a header band. Everything competed and nothing led. Now the
 * left column holds the findings and the right holds the evidence for whichever one is
 * selected, so the screen answers one question at a time.
 */

interface Finding {
  id: string;
  title: string;
  body: string;
  severity: "high" | "moderate";
  n: number;
  leafKind: SimEvent["kind"];
  cohorts: { label: string; rate: number; n: number }[];
  note: string;
}

const STEP: Record<string, (e: SimEvent) => string> = {
  ACCESSIBILITY_THRESHOLD_EXCEEDED: (e) =>
    `The walk to a usable stop rises to ${(e.after as { walk_distance_m: number }).walk_distance_m} m, past what this resident said they manage.`,
  ESSENTIAL_ACCESS_DEGRADED: () =>
    "Their weekly polyclinic trip stops being reachable. It is marked essential, so this counts as severe rather than inconvenient.",
  CAREGIVER_SUPPORT_TRIGGERED: () =>
    "Someone in their household takes over the journey, along a CARES_FOR link.",
  WORK_ARRIVAL_MISSED: () =>
    "That person now arrives after their own shift starts. They have no mobility limitation, and do not live near a removed stop.",
};

function buildFindings(run: SimulationRun): Finding[] {
  const severe = run.outcomes.filter((o) => o.severity === "high");
  const second = severe.filter((o) => o.second_order);
  const direct = severe.filter((o) => !o.second_order);
  const moderate = run.outcomes.filter((o) => o.severity === "moderate");
  const ages = run.metrics.subgroup.age_band;
  const carers = run.metrics.subgroup.is_caregiver;
  const ratio = carers.True.severe_harm_rate / Math.max(carers.False.severe_harm_rate, 1e-4);

  return [
    {
      id: "carers",
      title: "Carers absorbing the loss",
      severity: "high",
      n: second.length,
      body: "They drive a household member to the clinic, and miss their own shift.",
      leafKind: "WORK_ARRIVAL_MISSED",
      cohorts: [
        { label: "Is a carer", rate: carers.True.severe_harm_rate, n: carers.True.n },
        { label: "Not a carer", rate: carers.False.severe_harm_rate, n: carers.False.n },
      ],
      note: `Carers are ${ratio.toFixed(1)} times more likely to be severely harmed, and not one of them lost access themselves. This finding does not exist without the dependency graph.`,
    },
    {
      id: "access",
      title: "Polyclinic access lost",
      severity: "high",
      n: direct.length,
      body: "They can no longer reach the polyclinic inside their time budget.",
      leafKind: "ESSENTIAL_ACCESS_DEGRADED",
      cohorts: (["75+", "65-74", "55-64", "35-54", "18-34"] as const)
        .filter((b) => ages[b])
        .map((b) => ({ label: b, rate: ages[b].severe_harm_rate, n: ages[b].n })),
      note: "Harm climbs steeply with age, because clinic dependency and mobility limitation both do.",
    },
    {
      id: "walk",
      title: "Longer walk, trip still made",
      severity: "moderate",
      n: moderate.length,
      body: "They walk past their stated tolerance, but complete the journey.",
      leafKind: "ACCESSIBILITY_THRESHOLD_EXCEEDED",
      cohorts: [],
      note: "Inconvenience rather than exclusion. Reported separately so it is not mistaken for either.",
    },
  ];
}

export function ImpactAudit() {
  const { run, error } = useRun();
  const navigate = useNavigate();
  const [selected, setSelected] = useState("carers");

  const findings = useMemo(() => (run ? buildFindings(run) : []), [run]);
  const active = findings.find((f) => f.id === selected) ?? findings[0];

  const trace = useMemo(() => {
    if (!run || !active) return [];
    const leaf = run.events.find((e) => e.kind === active.leafKind);
    return leaf ? traceToRoot(run.events, leaf.event_id) : [];
  }, [run, active]);

  if (error) return <Crt><TopBar /><Failed message={error} /></Crt>;
  if (!run || !active) return <Crt><TopBar /><Loading what="the audit" /></Crt>;

  const m = run.metrics.overall;
  const second = run.outcomes.filter((o) => o.second_order).length;
  const maxRate = Math.max(...active.cohorts.map((c) => c.rate), 0.0001);

  return (
    <Crt>
      <TopBar meta={`RUN ${run.run_id.toUpperCase()}`} />

      <div style={{ padding: "var(--s-5) var(--s-6) var(--s-4)", flexShrink: 0 }}>
        <p className="t2" style={{ fontSize: "var(--fs-20)", lineHeight: 1.75, margin: 0, maxWidth: "64ch" }}>
          The policy moved the mean journey by{" "}
          <span className="gold" style={{ fontWeight: 600 }}>{m.avg_journey_time_delta.toFixed(1)} minutes</span>
          {" "}and severely harmed{" "}
          <span className="alert" style={{ fontWeight: 600 }}>{m.severe_harm_count} people</span>,{" "}
          <span className="alert" style={{ fontWeight: 600 }}>{second}</span> of them through
          someone else's dependency.
        </p>
      </div>

      <div className="grid-split"
        style={{
          flexGrow: 1, display: "grid",
          gridTemplateColumns: "minmax(0, 400px) minmax(0, 1fr)",
          gap: "var(--s-6)", padding: "0 var(--s-6) var(--s-5)", minHeight: 0,
        }}
      >
        <nav style={{ display: "flex", flexDirection: "column", gap: "var(--s-2)", overflowY: "auto" }}>
          {findings.map((f) => {
            const on = f.id === selected;
            return (
              <button
                key={f.id}
                onClick={() => setSelected(f.id)}
                aria-pressed={on}
                style={{
                  textAlign: "left", cursor: "pointer", fontFamily: "inherit",
                  borderRadius: 0, border: "none", background: "transparent",
                  padding: "var(--s-3) var(--s-3) var(--s-3) var(--s-2)",
                  borderLeft: `2px solid ${on ? "var(--gold)" : "transparent"}`,
                  transition: "border-color .18s ease, opacity .18s ease",
                  opacity: on ? 1 : 0.55,
                }}
              >
                <div style={{ display: "flex", alignItems: "baseline", gap: "var(--s-2)" }}>
                  <span
                    className={f.severity === "high" ? "alert" : "gold"}
                    style={{ fontSize: "var(--fs-40)", fontWeight: 500, lineHeight: 1 }}
                  >
                    {f.n}
                  </span>
                  <span className="t1" style={{ fontSize: "var(--fs-16)", fontWeight: 600 }}>
                    {f.title}
                  </span>
                </div>
                <p className="t2" style={{ fontSize: "var(--fs-14)", lineHeight: 1.6, margin: "var(--s-1) 0 0" }}>
                  {f.body}
                </p>
              </button>
            );
          })}
        </nav>

        <section style={{ display: "flex", flexDirection: "column", gap: "var(--s-5)", overflowY: "auto", paddingRight: "var(--s-2)" }}>
          {active.cohorts.length > 0 && (
            <div>
              <h2 className="t3" style={{ fontSize: "var(--fs-14)", fontWeight: 400, margin: "0 0 var(--s-3)" }}>
                Who carries it
              </h2>
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--s-3)" }}>
                {active.cohorts.map((c) => {
                  const hot = c.rate > maxRate * 0.45;
                  return (
                    <div
                      key={c.label}
                      style={{ display: "grid", gridTemplateColumns: "110px 1fr 150px", gap: "var(--s-2)", alignItems: "center" }}
                    >
                      <span className="t2" style={{ fontSize: "var(--fs-16)" }}>{c.label}</span>
                      <div style={{ height: 4, background: "var(--rule)" }}>
                        <div
                          style={{
                            height: "100%", width: "100%", transformOrigin: "left",
                            transform: `scaleX(${(c.rate / maxRate).toFixed(4)})`,
                            background: hot ? "var(--alert)" : "var(--fig-quiet)",
                            transition: "transform .6s cubic-bezier(.16,1,.3,1)",
                          }}
                        />
                      </div>
                      <span className={hot ? "alert" : "t2"} style={{ fontSize: "var(--fs-16)" }}>
                        {(c.rate * 100).toFixed(1)}%
                        <span className="t3" style={{ fontSize: "var(--fs-12)" }}> n {c.n.toLocaleString()}</span>
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <p className="t1" style={{ fontSize: "var(--fs-16)", lineHeight: 1.7, margin: 0, maxWidth: "60ch" }}>
            {active.note}
          </p>

          {trace.length > 0 && (
            <div>
              <h2 className="t3" style={{ fontSize: "var(--fs-14)", fontWeight: 400, margin: "0 0 var(--s-3)" }}>
                Why it happened
              </h2>
              <ol style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: "var(--s-3)" }}>
                {trace.map((e, i) => (
                  <li key={e.event_id} style={{ display: "grid", gridTemplateColumns: "30px 1fr", gap: "var(--s-2)" }}>
                    <span className="t3" style={{ fontSize: "var(--fs-14)", paddingTop: 3 }}>
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span className="t2" style={{ fontSize: "var(--fs-16)", lineHeight: 1.65, maxWidth: "56ch" }}>
                      {STEP[e.kind]?.(e) ?? e.kind}
                    </span>
                  </li>
                ))}
              </ol>
              <p className="t3" style={{ fontSize: "var(--fs-14)", lineHeight: 1.6, margin: "var(--s-3) 0 0", maxWidth: "56ch" }}>
                Each step is a recorded event carrying a cause id. Nothing here is written by a model.
              </p>
            </div>
          )}

          <div style={{ marginTop: "auto", paddingTop: "var(--s-3)" }}>
            <button className="btn" onClick={() => navigate("/interventions")}>
              FIND ALTERNATIVES
            </button>
          </div>
        </section>
      </div>
    </Crt>
  );
}
