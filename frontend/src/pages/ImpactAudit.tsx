import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Crt } from "@/components/Crt";
import { TopBar } from "@/components/TopBar";
import { Loading, Failed } from "@/components/ui";
import { useRun } from "@/lib/useRun";
import { traceToRoot } from "@/lib/run";
import { PatternNote } from "@/components/PatternNote";
import type { HarmPattern, SimEvent, SimulationRun } from "@/types/simulation";

interface Finding {
  id: string;
  title: string;
  body: string;
  severity: "high" | "moderate";
  n: number;
  leafKind: SimEvent["kind"];
  pattern: HarmPattern;
  cohorts: { label: string; rate: number; n: number }[];
  note: string;
}

type DetailView = "summary" | "people" | "cause";

const STEP: Record<string, (event: SimEvent) => string> = {
  EFFORT_INCREASED: () =>
    "The walk to the next available stop becomes longer.",
  SERVICE_ABANDONED: () =>
    "The usual bus journey is no longer practical.",
  DURATION_INCREASED: () =>
    "The replacement journey takes longer.",
  PATH_UNAVAILABLE: () =>
    "No suitable public transport route remains.",
  FRICTION_ADDED: () =>
    "The new route adds another difficult step to the journey.",
  THRESHOLD_EXCEEDED: (event) =>
    "The walk rises to " + (event.after as { walk_distance_m: number }).walk_distance_m + " m, beyond this resident’s stated limit.",
  ESSENTIAL_ACCESS_LOST: () =>
    "Their weekly polyclinic journey is no longer reachable.",
  DEPENDENCY_ABSORBED: () =>
    "A family member takes over the journey.",
  OBLIGATION_MISSED: () =>
    "That family member now misses their own work shift.",
};

function buildFindings(run: SimulationRun): Finding[] {
  const severe = run.outcomes.filter((outcome) => outcome.severity === "high");
  const second = severe.filter((outcome) => outcome.second_order);
  const direct = severe.filter((outcome) => !outcome.second_order);
  const moderate = run.outcomes.filter((outcome) => outcome.severity === "moderate");
  const ages = run.metrics.subgroup.age_band;
  const carers = run.metrics.subgroup.is_caregiver;
  const ratio = carers.True.severe_harm_rate / Math.max(carers.False.severe_harm_rate, 0.0001);

  return [
    {
      id: "access",
      pattern: "threshold_cliff",
      title: "Polyclinic journey becomes unreachable",
      severity: "high",
      n: direct.length,
      body: "The longer walk pushes an essential journey beyond what some residents can manage.",
      leafKind: "ESSENTIAL_ACCESS_LOST",
      cohorts: (["75+", "65-74", "55-64", "35-54", "18-34"] as const)
        .filter((band) => ages[band])
        .map((band) => ({ label: "Age " + band, rate: ages[band].severe_harm_rate, n: ages[band].n })),
      note: "Older residents are affected most because mobility limits and clinic dependence overlap.",
    },
    {
      id: "carers",
      pattern: "dependency_cascade",
      title: "Family caregivers miss work",
      severity: "high",
      n: second.length,
      body: "They help someone reach the clinic, then miss an obligation of their own.",
      leafKind: "OBLIGATION_MISSED",
      cohorts: [
        { label: "Family caregiver", rate: carers.True.severe_harm_rate, n: carers.True.n },
        { label: "Not a caregiver", rate: carers.False.severe_harm_rate, n: carers.False.n },
      ],
      note: "Caregivers are " + ratio.toFixed(1) + "× more likely to face severe impact. Their own bus stop did not close—the effect reaches them through someone they support.",
    },
    {
      id: "walk",
      pattern: "threshold_cliff",
      title: "Longer walk, journey still possible",
      severity: "moderate",
      n: moderate.length,
      body: "These residents travel further but can still complete the journey.",
      leafKind: "THRESHOLD_EXCEEDED",
      cohorts: [],
      note: "This is inconvenience rather than lost access, so it is reported separately.",
    },
  ];
}

export function ImpactAudit() {
  const { run, error } = useRun();
  const navigate = useNavigate();
  const [selected, setSelected] = useState("access");
  const [view, setView] = useState<DetailView>("summary");
  const findings = useMemo(() => (run ? buildFindings(run) : []), [run]);
  const active = findings.find((finding) => finding.id === selected) ?? findings[0];

  const trace = useMemo(() => {
    if (!run || !active) return [];
    const leaf = run.events.find((event) => event.kind === active.leafKind);
    return leaf ? traceToRoot(run.events, leaf.event_id) : [];
  }, [run, active]);

  if (error) return <Crt><TopBar /><Failed message={error} /></Crt>;
  if (!run || !active) return <Crt><TopBar /><Loading what="the impact audit" /></Crt>;

  const maxRate = Math.max(...active.cohorts.map((cohort) => cohort.rate), 0.0001);
  const detailViews: DetailView[] = active.cohorts.length
    ? ["summary", "people", "cause"]
    : ["summary", "cause"];
  const chooseFinding = (id: string) => {
    setSelected(id);
    setView("summary");
  };

  return (
    <Crt>
      <TopBar meta={"RUN " + run.run_id.toUpperCase()} />

      <main className="impact-page">
        <header className="impact-header">
          <div>
            <span className="page-kicker">Step 3 · Impact</span>
            <h1>{run.metrics.overall.severe_harm_count} residents face severe transport barriers</h1>
          </div>
          <div className="impact-header__summary">
            <span>
              <strong>{Math.abs(run.metrics.overall.avg_journey_time_delta).toFixed(1)} min</strong>
              {run.metrics.overall.avg_journey_time_delta < 0 ? "faster overall" : "slower overall"}
            </span>
            <span><strong>{run.metrics.overall.walk_distance_p90} m</strong>90th-percentile walk</span>
          </div>
          <button type="button" className="btn" onClick={() => navigate("/interventions")}>
            COMPARE SAFER OPTIONS
          </button>
        </header>

        <div className="impact-workspace">
          <nav className="impact-findings" aria-label="Impact findings ranked by severity and reach">
            <div className="impact-findings__heading">
              <h2>Priority findings</h2>
              <p>Ranked by severity, then residents affected</p>
            </div>
            {findings.map((finding, index) => {
              const on = finding.id === selected;
              return (
                <button
                  type="button"
                  key={finding.id}
                  className={`impact-finding-card severity-${finding.severity}${on ? " active" : ""}`}
                  onClick={() => chooseFinding(finding.id)}
                  aria-pressed={on}
                >
                  <span className="impact-finding-card__rank">{index + 1}</span>
                  <div>
                    <span className="impact-finding-card__severity">
                      {finding.severity === "high" ? "Severe" : "Moderate"} · {finding.n} residents
                    </span>
                    <strong>{finding.title}</strong>
                  </div>
                  <i aria-hidden="true">→</i>
                </button>
              );
            })}
          </nav>

          <section className="impact-detail" aria-labelledby="impact-detail-title">
            <div className="impact-detail__head">
              <div>
                <span className={`impact-severity-badge severity-${active.severity}`}>
                  {active.severity === "high" ? "Severe impact" : "Moderate impact"}
                </span>
                <h2 id="impact-detail-title">{active.title}</h2>
              </div>
              <div className="segmented" aria-label="Finding details">
                {detailViews.map((name) => (
                  <button
                    type="button"
                    key={name}
                    aria-pressed={view === name}
                    onClick={() => setView(name)}
                  >
                    {name === "summary" ? "Summary" : name === "people" ? "Affected groups" : "Why it happens"}
                  </button>
                ))}
              </div>
            </div>

            <div className="impact-detail__body">
              {view === "summary" && (
                <div className="impact-summary-grid">
                  <section className={`impact-count-card severity-${active.severity}`}>
                    <span>Affected residents</span>
                    <strong>{active.n}</strong>
                    <small>{active.severity === "high" ? "Severe barrier" : "Journey still possible"}</small>
                  </section>
                  <div className="impact-summary-copy">
                    <section>
                      <span>What changed</span>
                      <p>{active.body}</p>
                    </section>
                    <section>
                      <span>Why it matters</span>
                      <p>{active.note}</p>
                    </section>
                  </div>
                </div>
              )}

              {view === "people" && (
                <div className="impact-cohorts">
                  <h3>Impact rate by group</h3>
                  {active.cohorts.map((cohort) => (
                    <div key={cohort.label}>
                      <span>{cohort.label}</span>
                      <div><i style={{ width: (cohort.rate / maxRate) * 100 + "%" }} /></div>
                      <strong>{(cohort.rate * 100).toFixed(1)}%</strong>
                      <small>{cohort.n.toLocaleString()} residents</small>
                    </div>
                  ))}
                </div>
              )}

              {view === "cause" && (
                <div className="impact-cause-grid">
                  <div className="impact-trace">
                    <h3>How the impact unfolds</h3>
                    <ol>
                      {trace.map((event, index) => (
                        <li key={event.event_id}>
                          <span>{index + 1}</span>
                          <p>{STEP[event.kind]?.(event) ?? event.kind}</p>
                        </li>
                      ))}
                    </ol>
                  </div>
                  <aside className="impact-pattern-card" aria-label="Impact pattern explanation">
                    <PatternNote run={run} pattern={active.pattern} bare />
                  </aside>
                </div>
              )}
            </div>
          </section>
        </div>
      </main>
    </Crt>
  );
}
