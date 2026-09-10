import { stepKicker } from "@/lib/workflow";
import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Crt } from "@/components/Crt";
import { TopBar } from "@/components/TopBar";
import { Loading, Failed } from "@/components/ui";
import { PatternNote } from "@/components/PatternNote";
import { useRun } from "@/lib/useRun";
import type { Intervention } from "@/types/simulation";

type ValidIntervention = Intervention & { metrics: NonNullable<Intervention["metrics"]> };

const ACTION_COPY: Record<Intervention["kind"], string> = {
  retain_stop_peak: "Keep both stops open during the busiest travel periods.",
  add_shuttle_feeder: "Add a short feeder service for the affected corridor.",
  reroute_feeder: "Move the feeder service closer to residents who lose a stop.",
  targeted_support: "Provide assisted travel for clinic-dependent residents.",
  phase_rollout: "Close one stop first and review the effect before continuing.",
};

export function InterventionLab() {
  const { run, error } = useRun();
  const navigate = useNavigate();
  const valid = (run?.interventions ?? []).filter(
    (item): item is ValidIntervention => item.valid && item.metrics !== null,
  );
  const rejected = (run?.interventions ?? []).filter((item) => !item.valid);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  if (error) return <Crt><TopBar /><Failed message={error} /></Crt>;
  if (!run || valid.length === 0) return <Crt><TopBar /><Loading what="the options" /></Crt>;

  const base = run.metrics.overall;
  const ranked = [...valid].sort((left, right) => {
    const harmDifference = left.metrics.severe_harm_count - right.metrics.severe_harm_count;
    if (harmDifference !== 0) return harmDifference;
    return left.estimated_cost_index - right.estimated_cost_index;
  });
  const best = ranked[0];
  const selected = ranked.find((item) => item.intervention_id === selectedId) ?? best;
  const prevented = Math.max(0, base.severe_harm_count - selected.metrics.severe_harm_count);
  const baseCarers = run.outcomes.filter((outcome) => outcome.second_order).length;
  const selectedCarers = selected.carers_harmed ?? 0;
  const carersPrevented = baseCarers - selectedCarers;
  const costChange = Math.round((selected.estimated_cost_index - 1) * 100);
  const essentialTrips = selected.metrics.essential_trip_completion === null
    ? null
    : Math.round(selected.metrics.essential_trip_completion * 100);

  const continueToConsultation = () => {
    window.sessionStorage.setItem("civictwin-selected-option", selected.intervention_id);
    navigate("/consultation");
  };

  return (
    <Crt>
      <TopBar meta={valid.length + " OPTIONS · SAME POPULATION"} />

      <main className="options-page">
        <header className="options-header">
          <div>
            <span className="page-kicker">{stepKicker(useLocation().pathname)}</span>
            <h1>Choose a safer transport option</h1>
          </div>
          <div className="options-header__baseline">
            <span>Current proposal</span>
            <strong>{base.severe_harm_count} severe impacts</strong>
          </div>
          <button type="button" className="btn" onClick={continueToConsultation}>
            CONTINUE TO CONSULTATION
          </button>
        </header>

        <div className="options-workspace">
          <aside className="options-list" aria-label="Policy options">
            <div className="options-list__heading">
              <h2>Tested options</h2>
              <p>Ranked by severe impacts prevented</p>
            </div>
            {ranked.map((item) => {
              const active = item.intervention_id === selected.intervention_id;
              const isBest = item.intervention_id === best.intervention_id;
              const itemPrevented = Math.max(0, base.severe_harm_count - item.metrics.severe_harm_count);
              const itemCost = Math.round((item.estimated_cost_index - 1) * 100);
              return (
                <button
                  type="button"
                  key={item.intervention_id}
                  aria-pressed={active}
                  className={"option-card" + (active ? " active" : "")}
                  onClick={() => setSelectedId(item.intervention_id)}
                >
                  <div className="option-card__topline">
                    <span className={isBest ? "success" : itemPrevented > 0 ? "option-card__positive" : "option-card__neutral"}>
                      {isBest ? "Best harm reduction" : itemPrevented > 0 ? itemPrevented + " fewer severe impacts" : "No severe impact reduction"}
                    </span>
                    <i aria-hidden="true">→</i>
                  </div>
                  <strong>{item.name}</strong>
                  <div className="option-card__metrics">
                    <span><b>{item.metrics.severe_harm_count}</b> severe remain</span>
                    <span><b>{itemCost > 0 ? "+" : ""}{itemCost}%</b> cost</span>
                  </div>
                </button>
              );
            })}

            {rejected.length > 0 && (
              <details className="options-rejected">
                <summary>{rejected.length} option rejected by constraints</summary>
                {rejected.map((item) => (
                  <div key={item.intervention_id}>
                    <strong>{item.name}</strong>
                    <span>{item.validation_errors[0]}</span>
                  </div>
                ))}
              </details>
            )}
          </aside>

          <section className="option-detail" aria-labelledby="selected-option-title">
            <div className="option-detail__head">
              <div>
                <span className={selected.intervention_id === best.intervention_id ? "success" : ""}>
                  {selected.intervention_id === best.intervention_id ? "Best harm reduction" : "Selected option"}
                </span>
                <h2 id="selected-option-title">{selected.name}</h2>
                <p>{ACTION_COPY[selected.kind]}</p>
              </div>
            </div>

            <div className="option-outcome">
              <section className={"option-primary-result" + (prevented > 0 ? " improved" : " unchanged")}>
                <span>Severe impacts prevented</span>
                <strong>{prevented}</strong>
                <small>{base.severe_harm_count} → {selected.metrics.severe_harm_count} residents</small>
              </section>
              <div className="option-supporting-results">
                <section>
                  <span>Essential trips completed</span>
                  <strong>{essentialTrips === null ? "n/a" : essentialTrips + "%"}</strong>
                </section>
                <section className={carersPrevented > 0 ? "improved" : carersPrevented < 0 ? "worse" : ""}>
                  <span>Family carers</span>
                  <strong>{carersPrevented > 0 ? carersPrevented + " fewer" : carersPrevented < 0 ? Math.abs(carersPrevented) + " more" : "No change"}</strong>
                </section>
                <section className={costChange > 0 ? "tradeoff" : costChange < 0 ? "improved" : ""}>
                  <span>Operating cost</span>
                  <strong>{costChange > 0 ? "+" : ""}{costChange}%</strong>
                </section>
              </div>
            </div>

            <div className="option-explanation">
              <div>
                <span>What changes</span>
                <p>{selected.rationale}</p>
              </div>
              <div>
                <span>Trade-off</span>
                <p>
                  {(selected.newly_harmed_elsewhere ?? 0) > 0
                    ? (selected.newly_harmed_elsewhere ?? 0) + ((selected.newly_harmed_elsewhere ?? 0) === 1 ? " resident is" : " residents are") + " newly affected elsewhere."
                    : costChange > 0
                      ? "This reduces harm with a " + costChange + "% operating cost increase."
                      : "This reduces harm without increasing the operating cost."}
                </p>
              </div>
            </div>

            <details className="option-all-metrics">
              <summary>View all comparison metrics</summary>
              <table>
                <thead><tr><th>Measure</th><th>Current</th><th>This option</th></tr></thead>
                <tbody>
                  <tr><td>Average journey</td><td>{base.avg_journey_time_delta.toFixed(1)} min</td><td>{selected.metrics.avg_journey_time_delta.toFixed(1)} min</td></tr>
                  <tr><td>90th-percentile walk</td><td>{base.walk_distance_p90} m</td><td>{selected.metrics.walk_distance_p90} m</td></tr>
                  <tr><td>Severe impact</td><td>{base.severe_harm_count}</td><td>{selected.metrics.severe_harm_count}</td></tr>
                  <tr><td>Newly affected elsewhere</td><td>—</td><td>{selected.newly_harmed_elsewhere ?? 0}</td></tr>
                </tbody>
              </table>
              {(selected.newly_harmed_elsewhere ?? 0) > 0 && (
                <PatternNote run={run} pattern="capacity_displacement" />
              )}
            </details>
          </section>
        </div>
      </main>
    </Crt>
  );
}
