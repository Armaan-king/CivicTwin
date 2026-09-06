import { useState } from "react";
import { Crt } from "@/components/Crt";
import { Loading, Failed } from "@/components/ui";
import { useRun } from "@/lib/useRun";
import { api, NotAvailableOffline } from "@/lib/api";

/**
 * The citizen surface. A different audience from the operator screens: plain language,
 * no metrics table, and the model described honestly as possibly wrong about you.
 * Phone width on purpose. Consultation happens on a phone.
 */
export function Consultation() {
  const { run, error } = useRun();
  const [support, setSupport] = useState<number | null>(4);
  const [fairness, setFairness] = useState<number | null>(null);
  const [sent, setSent] = useState(false);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  async function submit() {
    if (support === null) return;
    setSending(true); setSendError(null);
    try {
      await api.submitFeedback("c1", {
        support: support as 1 | 2 | 3 | 4 | 5,
        perceived_fairness: fairness ?? 3,
        clarity_of_explanation: 4,
        confidence_in_delivery: 3,
        expected_personal_impact: 0,
        comment: null,
        cohort: {},
      });
      setSent(true);
    } catch (e) {
      // never let a failed write look like a successful one (AGENTS.md 28)
      setSendError(e instanceof NotAvailableOffline
        ? "Not recorded: the consultation service is not running."
        : (e as Error).message);
    } finally {
      setSending(false);
    }
  }

  if (error) return <Crt><Failed message={error} /></Crt>;
  if (!run) return <Crt><Loading what="the proposal" /></Crt>;

  const severe = run.metrics.overall.severe_harm_count;
  const alts = run.interventions.filter((i) => i.valid);
  const chosen = alts[0];

  return (
    <div style={{ display: "flex", justifyContent: "center", minHeight: "100vh", background: "#080807" }}>
      <div style={{ width: 390, borderLeft: "1px solid var(--rule)", borderRight: "1px solid var(--rule)" }}>
        <Crt>
          <header
            style={{
              padding: "17px 20px 14px", borderBottom: "1px solid var(--rule)",
              display: "flex", alignItems: "center", gap: 10,
            }}
          >
            <span className="gold" style={{ fontWeight: 600, fontSize: "var(--fs-14)", letterSpacing: ".16em" }}>
              CIVICTWIN
            </span>
            <span className="t3" style={{ fontSize: "var(--fs-12)" }}>HAVE YOUR SAY</span>
          </header>

          <div style={{ padding: "22px 20px", borderBottom: "1px solid var(--rule-dim)" }}>
            <h1
              className="display t1"
              style={{ fontSize: "var(--fs-28)", lineHeight: 1.14, letterSpacing: "-.02em", margin: "0 0 14px" }}
            >
              TWO BUS STOPS ON AVE 3 MAY CLOSE
            </h1>
            <p className="t2" style={{ fontSize: "var(--fs-16)", lineHeight: 1.6, margin: 0 }}>
              Service 265 would run non-stop to the interchange. We want to know what that
              means for you before anything is decided.
            </p>
          </div>

          <div style={{ padding: "var(--s-3)", borderBottom: "1px solid var(--rule-dim)" }}>
            <div style={{ marginBottom: 13 }}>
              <div className="t1" style={{ fontSize: "var(--fs-14)", fontWeight: 600 }}>
                Most journeys get shorter
              </div>
              <div className="t2" style={{ fontSize: "var(--fs-14)", lineHeight: 1.5, marginTop: 3 }}>
                About {Math.abs(run.metrics.overall.avg_journey_time_delta).toFixed(0)} minutes
                faster on average to the interchange.
              </div>
            </div>
            <div>
              <div className="alert" style={{ fontSize: "var(--fs-14)", fontWeight: 600 }}>
                Some get much harder
              </div>
              <div className="t2" style={{ fontSize: "var(--fs-14)", lineHeight: 1.5, marginTop: 3 }}>
                If you use the Ave 3 stops, your walk could go from 380 m to about{" "}
                {run.metrics.overall.walk_distance_p90} m.
              </div>
            </div>
          </div>

          <div style={{ padding: "var(--s-3)", borderBottom: "1px solid var(--rule-dim)" }}>
            <p className="t2" style={{ fontSize: "var(--fs-14)", lineHeight: 1.6, margin: 0 }}>
              Our modelling points to {severe} residents being seriously affected, mostly older
              people with limited mobility and the family members who would end up driving them
              to appointments.
            </p>
            <div className="box" style={{ marginTop: 14, padding: "13px 14px" }}>
              <p className="t3" style={{ fontSize: "var(--fs-14)", lineHeight: 1.6, margin: 0 }}>
                This is a computer model of a made-up group of residents. It is not a survey of
                real people, and it may be wrong about you. That is why we are asking.
              </p>
            </div>
          </div>

          <div style={{ padding: "var(--s-3)", borderBottom: "1px solid var(--rule-dim)" }}>
            {alts.map((a, i) => (
              <div
                key={a.intervention_id}
                style={{
                  display: "flex", justifyContent: "space-between", alignItems: "baseline",
                  gap: 10, padding: i === 0 ? "0 0 10px" : "10px 0",
                  borderBottom: i < alts.length - 1 ? "1px solid var(--rule-faint)" : undefined,
                }}
              >
                <span className={a === chosen ? "t1" : "t2"} style={{ fontSize: "var(--fs-14)", fontWeight: a === chosen ? 600 : 400 }}>
                  {a.name}
                </span>
                <span className={a === chosen ? "gold" : "t3"} style={{ fontSize: "var(--fs-12)", flexShrink: 0 }}>
                  {a === chosen ? "CHOSEN" : (a.newly_harmed_elsewhere ?? 0) > 0
                    ? `HARMS ${a.newly_harmed_elsewhere} ELSEWHERE`
                    : `COSTS ${Math.round((a.estimated_cost_index - 1) * 100)}% MORE`}
                </span>
              </div>
            ))}
          </div>

          <div style={{ padding: 20 }}>
            {sent ? (
              <div className="box" style={{ padding: "18px 16px" }}>
                <div className="gold" style={{ fontSize: "var(--fs-16)", fontWeight: 600 }}>Thank you.</div>
                <p className="t2" style={{ fontSize: "var(--fs-14)", lineHeight: 1.6, margin: "6px 0 0" }}>
                  Your answer joins {run.consultation.response_count} others. If enough people
                  tell us the model missed something, it gets re-run rather than ignored.
                </p>
              </div>
            ) : (
              <>
                <Scale
                  label="Do you support this change?"
                  low="STRONGLY OPPOSE" high="STRONGLY SUPPORT"
                  value={support} onChange={setSupport}
                />
                <div style={{ height: 19 }} />
                <Scale
                  label="Does it feel fair?"
                  low="NOT AT ALL" high="COMPLETELY"
                  value={fairness} onChange={setFairness}
                />

                <label className="t1" style={{ fontSize: "var(--fs-14)", fontWeight: 600, display: "block", margin: "19px 0 9px" }}>
                  Is there something we have missed?
                </label>
                <textarea
                  placeholder="A slope, a gap in the covered walkway, a trip we have not thought about."
                  rows={3}
                  style={{
                    width: "100%", padding: 13, background: "transparent", color: "var(--t1)",
                    border: "1px solid var(--rule)", borderRadius: 0, resize: "vertical",
                    fontFamily: "inherit", fontSize: "var(--fs-14)", lineHeight: 1.55,
                  }}
                />
                <p className="t3" style={{ fontSize: "var(--fs-12)", margin: "7px 0 0" }}>
                  Optional, and the answer that most often changes the model.
                </p>

                <button
                  className="btn"
                  style={{ marginTop: 16, width: "100%", justifyContent: "flex-start" }}
                  onClick={submit}
                  disabled={support === null || sending}
                >
                  {sending ? "SENDING" : "SUBMIT"}
                </button>
                {sendError && (
                  <p className="alert" style={{ fontSize: "var(--fs-12)", margin: "var(--s-1) 0 0", lineHeight: 1.6 }}>
                    {sendError}
                  </p>
                )}
                <p className="t3" style={{ fontSize: "var(--fs-12)", margin: "10px 0 0", textAlign: "center" }}>
                  No account needed. We do not ask for your name.
                </p>
              </>
            )}
          </div>
        </Crt>
      </div>
    </div>
  );
}

function Scale({
  label, low, high, value, onChange,
}: {
  label: string; low: string; high: string;
  value: number | null; onChange: (v: number) => void;
}) {
  return (
    <div>
      <label className="t1" style={{ fontSize: "var(--fs-14)", fontWeight: 600, display: "block", marginBottom: 9 }}>
        {label}
      </label>
      <div style={{ display: "flex", gap: 6 }}>
        {[1, 2, 3, 4, 5].map((v) => {
          const on = value === v;
          return (
            <button
              key={v}
              onClick={() => onChange(v)}
              aria-pressed={on}
              aria-label={`${label} ${v} of 5`}
              style={{
                flexGrow: 1, minHeight: 44, cursor: "pointer", fontFamily: "inherit",
                fontSize: "var(--fs-14)", borderRadius: 0,
                border: `1px solid ${on ? "var(--gold)" : "var(--rule)"}`,
                background: on ? "var(--gold)" : "transparent",
                color: on ? "var(--ground)" : "var(--t2)",
                fontWeight: on ? 600 : 400,
              }}
            >
              {v}
            </button>
          );
        })}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6 }}>
        <span className="t3" style={{ fontSize: "var(--fs-12)" }}>{low}</span>
        <span className="t3" style={{ fontSize: "var(--fs-12)" }}>{high}</span>
      </div>
    </div>
  );
}
