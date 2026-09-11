import { useState } from "react";
import { Link } from "react-router-dom";
import { Crt } from "@/components/Crt";
import { TopBar } from "@/components/TopBar";
import { Loading, Failed, PageKicker } from "@/components/ui";
import { useRun } from "@/lib/useRun";
import { api, NotAvailableOffline } from "@/lib/api";
import { TRANSPORT } from "@/lib/config";
import type { Intervention } from "@/types/simulation";
import { serviceLabel } from "@/lib/naming";

type ValidIntervention = Intervention & { metrics: NonNullable<Intervention["metrics"]> };

const ACTION_COPY: Record<Intervention["kind"], string> = {
  retain_stop_peak: "Keep both stops open during peak travel periods.",
  add_shuttle_feeder: "Add a short feeder service along the affected corridor.",
  reroute_feeder: "Move the feeder service closer to residents who lose a stop.",
  targeted_support: "Provide assisted travel for clinic-dependent residents.",
  phase_rollout: "Close one stop first and review the effect before continuing.",
};

const SUPPORT_LABELS = ["Strongly oppose", "Oppose", "Unsure", "Support", "Strongly support"];
const FAIRNESS_LABELS = ["Not fair", "Slightly fair", "Unsure", "Mostly fair", "Completely fair"];

/** Citizen feedback stays in the CivicTwin workflow, but uses plain public-facing copy. */
export function Consultation() {
  const { run, error } = useRun();
  const [support, setSupport] = useState<number | null>(null);
  const [fairness, setFairness] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const [sent, setSent] = useState(false);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (support === null || fairness === null) return;
    setSending(true);
    setSendError(null);
    try {
      await api.submitFeedback("c1", {
        support: support as 1 | 2 | 3 | 4 | 5,
        perceived_fairness: fairness,
        clarity_of_explanation: 4,
        confidence_in_delivery: 3,
        expected_personal_impact: 0,
        comment: comment.trim() || null,
        cohort: {},
      });
      setSent(true);
    } catch (caught) {
      setSendError(caught instanceof NotAvailableOffline
        ? "Preview only — this response was not recorded. Connect the live service to accept feedback."
        : (caught as Error).message);
    } finally {
      setSending(false);
    }
  }

  if (error) return <Crt><TopBar /><Failed message={error} /></Crt>;
  if (!run) return <Crt><TopBar /><Loading what="the proposal" /></Crt>;

  const valid = run.interventions.filter(
    (item): item is ValidIntervention => item.valid && item.metrics !== null,
  );
  const ranked = [...valid].sort((left, right) => {
    const harmDifference = left.metrics.severe_harm_count - right.metrics.severe_harm_count;
    return harmDifference !== 0
      ? harmDifference
      : left.estimated_cost_index - right.estimated_cost_index;
  });
  const selectedId = window.sessionStorage.getItem("civictwin-selected-option");
  const chosen = ranked.find((item) => item.intervention_id === selectedId) ?? ranked[0];

  if (!chosen) return <Crt><TopBar /><Failed message="No consultation option is available." /></Crt>;

  const baseSevere = run.metrics.overall.severe_harm_count;
  const remainingSevere = chosen.metrics.severe_harm_count;
  const prevented = Math.max(0, baseSevere - remainingSevere);
  const costChange = Math.round((chosen.estimated_cost_index - 1) * 100);

  return (
    <Crt>
      <TopBar meta="PUBLIC FEEDBACK" />

      <main className="consultation-page">
        <header className="consultation-header">
          <div>
            <PageKicker />
            <h1>Have your say on {serviceLabel(run)}</h1>
          </div>
          {TRANSPORT === "fixture" && (
            <span className="consultation-preview">Preview · responses are not saved</span>
          )}
        </header>

        <div className="consultation-workspace">
          <section className="consultation-brief" aria-labelledby="consultation-option-title">
            <div className="consultation-brief__intro">
              <span>Option selected for consultation</span>
              <h2 id="consultation-option-title">{chosen.name}</h2>
              <p>{ACTION_COPY[chosen.kind]}</p>
            </div>

            <div className="consultation-change">
              <span>Service change</span>
              <strong>Two Ave 3 stops close</strong>
              <p>{serviceLabel(run)} runs express through this section.</p>
            </div>

            <div className="consultation-results" aria-label="Expected results">
              <div className="improved">
                <strong>{prevented}</strong>
                <span>severe impacts avoided</span>
              </div>
              <div className={remainingSevere > 0 ? "attention" : "improved"}>
                <strong>{remainingSevere}</strong>
                <span>residents still severely affected</span>
              </div>
              <div>
                <strong>{costChange > 0 ? "+" : ""}{costChange}%</strong>
                <span>estimated operating cost</span>
              </div>
            </div>

            <details className="consultation-method">
              <summary>About these estimates</summary>
              <p>
                Results use synthetic residents, not survey responses. Public feedback helps
                identify what the simulation missed.
              </p>
            </details>
          </section>

          <section className="consultation-response" aria-labelledby="consultation-response-title">
            <div className="consultation-response__head">
              <div>
                <span>Your response</span>
                <h2 id="consultation-response-title">What do you think?</h2>
              </div>
              <small>2 choices · 1 optional note</small>
            </div>

            {sent ? (
              <div className="consultation-success" role="status">
                <span aria-hidden="true">✓</span>
                <h3>Feedback recorded</h3>
                <p>Thank you. Your response will be included in the consultation summary.</p>
                <Link className="btn" to="/calibration">VIEW CONSULTATION RESULTS</Link>
              </div>
            ) : (
              <form className="consultation-form" onSubmit={submit}>
                <Scale
                  label="Do you support this option?"
                  labels={SUPPORT_LABELS}
                  value={support}
                  onChange={setSupport}
                />
                <Scale
                  label="Does this option feel fair?"
                  labels={FAIRNESS_LABELS}
                  value={fairness}
                  onChange={setFairness}
                />

                <label className="consultation-comment">
                  <span>What have we missed? <i>Optional</i></span>
                  <textarea
                    value={comment}
                    onChange={(event) => setComment(event.target.value)}
                    placeholder="For example: an uncovered walkway or a regular trip this change affects."
                    rows={3}
                  />
                </label>

                <div className="consultation-submit">
                  <button
                    className="btn"
                    type="submit"
                    disabled={support === null || fairness === null || sending}
                  >
                    {sending ? "SENDING…" : "SUBMIT FEEDBACK"}
                  </button>
                  <span>No name or account required.</span>
                </div>

                {sendError && (
                  <div className="consultation-submit-error" role="alert">
                    <strong>Feedback not sent</strong>
                    <span>{sendError}</span>
                    {TRANSPORT === "fixture" && <Link to="/calibration">View the demo results →</Link>}
                  </div>
                )}
              </form>
            )}
          </section>
        </div>
      </main>
    </Crt>
  );
}

function Scale({
  label, labels, value, onChange,
}: {
  label: string;
  labels: string[];
  value: number | null;
  onChange: (value: number) => void;
}) {
  return (
    <fieldset className="consultation-scale">
      <legend>{label}</legend>
      <div>
        {labels.map((option, index) => {
          const rating = index + 1;
          return (
            <button
              type="button"
              key={option}
              className={value === rating ? "active" : ""}
              onClick={() => onChange(rating)}
              aria-pressed={value === rating}
            >
              <b>{rating}</b>
              <span>{option}</span>
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
