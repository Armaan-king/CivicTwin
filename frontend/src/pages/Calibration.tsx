import { useLocation } from "react-router-dom";
import { stepKicker } from "@/lib/workflow";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Crt } from "@/components/Crt";
import { TopBar } from "@/components/TopBar";
import { Loading, Failed } from "@/components/ui";
import { PatternNote } from "@/components/PatternNote";
import { useRun } from "@/lib/useRun";
import { api, NotAvailableOffline } from "@/lib/api";
import type { CalibrationRow } from "@/types/simulation";

type CalibrationTab = "overview" | "groups" | "gaps";
type GroupFilter = "attention" | "all" | "small";

const MIN_N = 30;

function residentGroup(axis: string, value: string) {
  if (axis === "age_band") return "Ages " + value;
  if (axis === "mobility_level") {
    if (value === "none") return "No mobility limitation";
    if (value === "mild") return "Some mobility limitation";
    return value.charAt(0).toUpperCase() + value.slice(1) + " mobility limitation";
  }
  if (axis === "is_caregiver") return value === "True" ? "Family caregivers" : "Not a caregiver";
  if (axis === "overall") return "All respondents";
  return value;
}

function ratingPercent(value: number) {
  return Math.max(0, Math.min(100, ((value - 1) / 4) * 100));
}

function componentLabel(key: string) {
  if (key === "perceived_fairness") return "Fairness";
  if (key === "clarity_of_explanation") return "Clarity";
  if (key === "confidence_in_delivery") return "Delivery confidence";
  return key.charAt(0).toUpperCase() + key.slice(1).replaceAll("_", " ");
}

export function Calibration() {
  const { run, error } = useRun();
  const [tab, setTab] = useState<CalibrationTab>("overview");
  const [filter, setFilter] = useState<GroupFilter>("attention");
  const [decision, setDecision] = useState<"pending" | "applied" | "rejected">("pending");
  const navigate = useNavigate();

  // What the model did not know, written as a starting draft rather than applied for them.
  // The planner edits it; CivicTwin re-reads it like any other proposal.
  const constraint = run?.consultation?.discovered_constraint;
  const revisionDraft = constraint
    ? `${run?.policy?.text ?? ""}

Residents on ${constraint.location} report that ${
        (constraint.note ?? "").replace(/^The /, "the ").trim()
      } Account for the harder walk there.`
    : (run?.policy?.text ?? "");
  const [decideError, setDecideError] = useState<string | null>(null);

  async function decide(approved: boolean) {
    setDecideError(null);
    try {
      await api.applyCalibration(run?.run_id ?? "latest", approved);
      setDecision(approved ? "applied" : "rejected");
    } catch (caught) {
      setDecideError(caught instanceof NotAvailableOffline
        ? "Preview only — start the live service to record this decision."
        : (caught as Error).message);
    }
  }

  if (error) return <Crt><TopBar /><Failed message={error} /></Crt>;
  if (!run) return <Crt><TopBar /><Loading what="the consultation results" /></Crt>;

  const consultation = run.consultation;
  const overall = consultation.calibration.find((row) => row.cohort_axis === "overall");
  const flagged = consultation.calibration.filter((row) => row.flagged);
  const largest = [...consultation.calibration]
    .filter((row) => row.cohort_axis !== "overall" && row.n >= MIN_N)
    .sort((a, b) => Math.abs(b.signed_error) - Math.abs(a.signed_error))[0];
  const adjustment = consultation.proposed_adjustment;
  const rows = consultation.calibration.filter((row) =>
    filter === "all" ? row.cohort_axis !== "overall" : filter === "small" ? row.n < MIN_N : row.flagged,
  );

  return (
    <Crt>
      <TopBar meta={consultation.response_count + " RESPONSES · SEEDED DEMO"} />

      <main className="calibration-page">
        <header className="calibration-header">
          <div>
            <span className="page-kicker">{stepKicker(useLocation().pathname)}</span>
            <h1>Prediction vs public feedback</h1>
            <p>
              {largest
                ? `The model was close overall, but missed ${residentGroup(largest.cohort_axis, largest.cohort_value)}.`
                : "Review how the prediction compared with resident feedback."}
            </p>
          </div>
          <div className="segmented" aria-label="Calibration sections">
            {(["overview", "groups", "gaps"] as CalibrationTab[]).map((name) => (
              <button type="button" key={name} aria-pressed={tab === name} onClick={() => setTab(name)}>
                {name === "overview" ? "Overview" : name === "groups" ? "Resident groups" : "Response gaps"}
              </button>
            ))}
          </div>
        </header>

        <section className="calibration-metrics" aria-label="Calibration summary">
          <SummaryMetric
            value={(overall ? Math.abs(overall.signed_error).toFixed(1) : "—") + " pts"}
            label="Overall prediction error"
            tone="warning"
          />
          <SummaryMetric
            value={largest ? Math.abs(largest.signed_error).toFixed(1) + " pts" : "None"}
            label={largest ? "Largest gap · " + residentGroup(largest.cohort_axis, largest.cohort_value) : "No material gap"}
            tone={largest ? "danger" : "success"}
          />
          <SummaryMetric
            value={String(flagged.length)}
            label={flagged.length === 1 ? "Resident group needs review" : "Resident groups need review"}
            tone={flagged.length > 0 ? "danger" : "success"}
          />
        </section>

        <section className="calibration-workspace">
          {tab === "overview" && (
            <div className="calibration-overview">
              <section className="calibration-gap-card" aria-labelledby="largest-gap-title">
                <div className="calibration-card-head">
                  <div>
                    <span>Largest mismatch</span>
                    <h2 id="largest-gap-title">
                      {largest ? residentGroup(largest.cohort_axis, largest.cohort_value) : "No group outside tolerance"}
                    </h2>
                  </div>
                  {largest && <b>{Math.abs(largest.signed_error).toFixed(1)} point gap</b>}
                </div>

                {largest && (
                  <>
                    <div className="calibration-large-bars">
                      <ComparisonBar label="Predicted support" value={ratingPercent(largest.predicted_support)} tone="predicted" />
                      <ComparisonBar label="Reported support" value={ratingPercent(largest.observed_support)} tone="reported" />
                    </div>
                    <p className="calibration-gap-caption">
                      Based on {largest.n} responses · lower support than forecast
                    </p>
                  </>
                )}
              </section>

              <section className="calibration-learning-card">
                <span>What the model missed</span>
                <h2>Walking conditions</h2>
                <p>{consultation.discovered_constraint.note}</p>
                <div>
                  <span>Location</span>
                  <strong>{consultation.discovered_constraint.location}</strong>
                </div>
              </section>

              <section className="calibration-confidence-card" aria-labelledby="confidence-title">
                <div className="calibration-confidence-score" aria-label={`${consultation.pcs.score} out of 100`}>
                  <svg viewBox="0 0 120 120" aria-hidden="true">
                    <circle className="track" cx="60" cy="60" r="48" pathLength="100" />
                    <circle
                      className="value"
                      cx="60"
                      cy="60"
                      r="48"
                      pathLength="100"
                      strokeDasharray={`${consultation.pcs.score} 100`}
                    />
                  </svg>
                  <strong>{consultation.pcs.score}</strong>
                  <span>/ 100</span>
                </div>
                <div className="calibration-confidence-detail">
                  <span>Public confidence</span>
                  <h2 id="confidence-title">What residents rated</h2>
                  <div className="calibration-confidence-bars">
                    {Object.entries(consultation.pcs.components).map(([key, value]) => (
                      <div key={key}>
                        <span>{componentLabel(key)}</span>
                        <i><b style={{ width: value + "%" }} /></i>
                        <strong>{value}</strong>
                      </div>
                    ))}
                  </div>
                  <small>{consultation.response_count} self-selected responses · not a representative sample</small>
                </div>
              </section>

              <section className="calibration-update-card">
                <div className="calibration-card-head">
                  <div>
                    <span>Suggested correction</span>
                    <h2>Account for harder walks</h2>
                  </div>
                  <b>Human review</b>
                </div>
                <div className="calibration-adjustment__change">
                  <span>Walking-condition weight</span>
                  <strong>{adjustment.from.toFixed(2)} → {adjustment.to.toFixed(2)}</strong>
                </div>
                <p className="calibration-adjustment__note">
                  A coefficient is one answer. The other is a different policy — the walkway
                  is the constraint, and a planner can write for it.
                </p>
                {decision === "pending" ? (
                  <div className="calibration-adjustment__buttons">
                    <button type="button" className="btn-ghost" onClick={() => decide(false)}>KEEP CURRENT</button>
                    <button
                      type="button"
                      className="btn-ghost"
                      onClick={() => navigate("/policy", { state: { revision: revisionDraft } })}
                    >
                      REVISE POLICY
                    </button>
                    <button type="button" className="btn" onClick={() => decide(true)}>APPLY UPDATE</button>
                  </div>
                ) : (
                  <div className="calibration-adjustment__buttons">
                    <p className={decision === "applied" ? "success" : "t2"} role="status">
                      {decision === "applied" ? "Update applied and recorded." : "Current model kept."}
                    </p>
                    <button
                      type="button"
                      className="btn-ghost"
                      onClick={() => navigate("/policy", { state: { revision: revisionDraft } })}
                    >
                      REVISE POLICY
                    </button>
                  </div>
                )}
                {decideError && <p className="calibration-decision-error" role="alert">{decideError}</p>}
              </section>
            </div>
          )}

          {tab === "groups" && (
            <div className="calibration-groups">
              <div className="calibration-section-head">
                <div>
                  <h2>Prediction accuracy by group</h2>
                  <div className="calibration-legend">
                    <span><i className="predicted" /> Predicted</span>
                    <span><i className="reported" /> Reported</span>
                  </div>
                </div>
                <div className="segmented" aria-label="Filter resident groups">
                  {(["attention", "all", "small"] as GroupFilter[]).map((name) => (
                    <button type="button" key={name} aria-pressed={filter === name} onClick={() => setFilter(name)}>
                      {name === "attention" ? "Needs review" : name === "all" ? "All groups" : "Low response"}
                    </button>
                  ))}
                </div>
              </div>
              <div className="calibration-table">
                <div className="calibration-row header">
                  <span>Resident group</span><span>Support score</span><span>Gap</span><span>Responses</span>
                </div>
                {rows.map((row) => <CalibrationRowView key={row.cohort_axis + row.cohort_value} row={row} />)}
                {rows.length === 0 && <p className="calibration-empty">No groups match this view.</p>}
              </div>
            </div>
          )}

          {tab === "gaps" && (
            <div className="calibration-gaps">
              <div className="calibration-section-head">
                <div>
                  <h2>Residents the consultation may not hear</h2>
                  <p>Estimated participation among people the model expects to be harmed.</p>
                </div>
              </div>
              <div className="response-gap-list">
                {consultation.blind_spots.map((item) => {
                  const share = item.harmed > 0 ? item.expected_responses / item.harmed : 0;
                  return (
                    <div className="response-gap" key={item.cohort_axis + item.cohort_value}>
                      <strong>{residentGroup(item.cohort_axis, item.cohort_value)}</strong>
                      <div><i style={{ width: Math.min(100, share * 100) + "%" }} /></div>
                      <span><b>{Math.round(share * 100)}%</b> likely heard · {item.expected_responses} of {item.harmed}</span>
                    </div>
                  );
                })}
              </div>
              <details className="calibration-pattern">
                <summary>Why participation gaps matter</summary>
                <PatternNote run={run} pattern="participation_gap" />
              </details>
            </div>
          )}
        </section>
      </main>
    </Crt>
  );
}

function SummaryMetric({
  value,
  label,
  tone,
}: {
  value: string;
  label: string;
  tone: "success" | "warning" | "danger";
}) {
  return (
    <div className="metric-card">
      <div className={"metric-card__value " + tone}>{value}</div>
      <div className="metric-card__label">{label}</div>
    </div>
  );
}

function ComparisonBar({ label, value, tone }: { label: string; value: number; tone: "predicted" | "reported" }) {
  return (
    <div className="calibration-large-bar">
      <div><span>{label}</span><strong>{Math.round(value)}%</strong></div>
      <i><b className={tone} style={{ width: value + "%" }} /></i>
    </div>
  );
}

function CalibrationRowView({ row }: { row: CalibrationRow }) {
  const lowResponse = row.n < MIN_N;
  const predicted = ratingPercent(row.predicted_support);
  const reported = ratingPercent(row.observed_support);
  return (
    <div className={"calibration-row" + (row.flagged ? " flagged" : "") + (lowResponse ? " low-response" : "")}>
      <strong>{residentGroup(row.cohort_axis, row.cohort_value)}</strong>
      <div className="calibration-comparison" aria-label={`Predicted ${Math.round(predicted)} percent, reported ${Math.round(reported)} percent`}>
        <span style={{ width: predicted + "%" }} />
        <i style={{ width: reported + "%" }} />
      </div>
      <span className={row.flagged ? "danger" : "t2"}>
        {(row.signed_error > 0 ? "+" : "") + row.signed_error.toFixed(1)}
      </span>
      <span>{row.n}</span>
    </div>
  );
}
