import { stepKicker } from "@/lib/workflow";
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Crt } from "@/components/Crt";
import { TopBar } from "@/components/TopBar";
import { Loading, Failed } from "@/components/ui";
import { api, NotAvailableOffline } from "@/lib/api";
import { useRun } from "@/lib/useRun";
import { serviceLabel, serviceId, affectedRoad, townName } from "@/lib/naming";

type ReviewTab = "change" | "assumptions" | "locations";

export function PolicyInput() {
  const { run, error } = useRun();
  const navigate = useNavigate();
  // A revision carried back from the Learn step. Calibration finds what the model did not
  // know -- an uncovered walkway, a slope -- and the answer to that is usually a different
  // policy rather than a different coefficient. The constraint arrives as text the planner
  // edits, not as a change made on their behalf.
  const carried = (useLocation().state as { revision?: string } | null)?.revision ?? null;
  const [draft, setDraft] = useState<string | null>(carried);
  const [tab, setTab] = useState<ReviewTab>("change");
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  if (error) return <Crt><TopBar /><Failed message={error} /></Crt>;
  if (!run) return <Crt><TopBar /><Loading what="the scenario" /></Crt>;

  const policyText = draft ?? run.policy.text;
  const changed = policyText.trim() !== run.policy.text.trim();
  const assumptions = run.policy.reading.filter((step) => step.assumed);

  async function startSimulation() {
    setRunError(null);
    if (!changed) {
      window.sessionStorage.removeItem("civictwin-active-run");
      navigate("/simulation");
      return;
    }

    setRunning(true);
    try {
      const created = await api.startRun(policyText.trim());
      window.sessionStorage.setItem("civictwin-active-run", created.run_id);
      navigate("/simulation");
    } catch (caught) {
      setRunError(caught instanceof NotAvailableOffline
        ? "Start the backend to simulate an amended policy. You can reset to the prepared example and continue now."
        : (caught as Error).message);
    } finally {
      setRunning(false);
    }
  }

  return (
    <Crt>
      <TopBar meta={"SYNTHETIC · " + run.study_area} />

      <main className="policy-workspace">
        <header className="policy-workspace__header">
          <span className="page-kicker">{stepKicker(useLocation().pathname)}</span>
          <h1>Review the transport policy</h1>
          <p>Edit the proposal, confirm what CivicTwin will test, then run the simulation.</p>
        </header>

        <section className="policy-builder">
          <div className="policy-workspace__grid">
            <section className="policy-editor" aria-labelledby="policy-draft-label">
              <div className="policy-panel-label">
                <span>Your draft</span>
              </div>
              <div className="policy-step-heading">
                <span aria-hidden="true">1</span>
                <div>
                  <label id="policy-draft-label" htmlFor="policy-draft">Policy proposal</label>
                  <small>Edit the prepared scenario if needed.</small>
                </div>
              </div>
              <textarea
                id="policy-draft"
                value={policyText}
                onChange={(event) => setDraft(event.target.value)}
                aria-describedby={runError ? "policy-run-error" : "policy-draft-help"}
              />
              <div className="policy-editor__footer">
                <div className="policy-context" id="policy-draft-help">
                  {/* the loaded run's own service and road, not the one this page was
                      written against */}
                  <span>{serviceLabel(run)}</span>
                  <span>{affectedRoad(run) || townName(run)}</span>
                  {changed && <span className="warning">Edited</span>}
                </div>
                {changed && (
                  <button type="button" onClick={() => setDraft(null)}>Reset example</button>
                )}
              </div>
            </section>

            <div className="policy-flow-bridge" aria-hidden="true">
              <span>CivicTwin reads</span>
              <b>→</b>
            </div>

            <section className="policy-review" aria-labelledby="policy-review-title">
              <div className="policy-panel-label policy-panel-label--output">
                <span>CivicTwin interpretation</span>
                {changed ? <small>Re-read the draft</small> : null}
              </div>
              <div className="policy-step-heading">
                <span aria-hidden="true">2</span>
                <div>
                  <h2 id="policy-review-title">What CivicTwin understood</h2>
                  <small>Confirm this interpretation before simulation.</small>
                </div>
              </div>

              {changed ? (
                <div className="policy-review__pending" role="status">
                  <span>Interpretation pending</span>
                  <strong>Your draft has changed</strong>
                  <p>CivicTwin will interpret the amended policy before it starts the simulation.</p>
                </div>
              ) : (
                <>
                  <div className="segmented policy-review__tabs" aria-label="Policy interpretation sections">
                    {(["change", "assumptions", "locations"] as ReviewTab[]).map((name) => (
                      <button
                        type="button"
                        key={name}
                        aria-pressed={tab === name}
                        onClick={() => setTab(name)}
                      >
                        {name === "change" ? "Change" : name === "assumptions" ? "Assumptions" : "Locations"}
                      </button>
                    ))}
                  </div>

                  <div className="policy-review__content">
                    {tab === "change" && (
                      <dl className="policy-summary-list">
                        {/* The run's own service, not the one this page was written
                            against. A bare "265" survived an earlier sweep because that
                            searched for the string "Service 265" and this is the number
                            on its own, in a <dd> beside a <dt> that supplies the word. */}
                        <div><dt>Service</dt><dd>{serviceId(run) || "—"}</dd></div>
                        <div><dt>Change</dt><dd>Close {run.policy.modifications.remove_stops.length} stops and run express</dd></div>
                        <div><dt>Goal</dt><dd>{run.policy.objective}</dd></div>
                        <div><dt>Fleet</dt><dd>{run.policy.constraints.fleet_increase_allowed ? "Increase allowed" : "No additional vehicles"}</dd></div>
                      </dl>
                    )}

                    {tab === "assumptions" && (
                      <div className="policy-review__items">
                        {assumptions.map((step) => (
                          <article key={step.n}>
                            <span className="warning">Needs confirmation</span>
                            <strong>{step.claim}</strong>
                            <p>{step.why}</p>
                          </article>
                        ))}
                      </div>
                    )}

                    {tab === "locations" && (
                      <div className="policy-review__items">
                        {run.policy.resolved_entities.map((entity) => (
                          <article key={entity.kind + entity.id}>
                            <span>{entity.kind}</span>
                            <strong>{entity.label}</strong>
                            <p>ID {entity.id}</p>
                          </article>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              )}
            </section>
          </div>

          <footer className="policy-workspace__actions">
            <div className="policy-readiness">
              <i aria-hidden="true">✓</i>
              <span>
                <strong>{changed ? "Ready for live review" : "Ready to simulate"}</strong>
                <small>{changed ? "Your edit will be interpreted before the run starts." : "Compare today’s route with the proposed stop closures."}</small>
              </span>
            </div>
            {runError && <p id="policy-run-error" role="alert">{runError}</p>}
            <button
              type="button"
              className="btn"
              onClick={startSimulation}
              disabled={running || policyText.trim().length < 10}
              aria-busy={running}
            >
              {running ? "PREPARING SIMULATION" : changed ? "INTERPRET & SIMULATE" : "RUN SIMULATION"}
            </button>
          </footer>
        </section>
      </main>
    </Crt>
  );
}
