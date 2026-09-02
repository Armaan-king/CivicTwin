import { useState } from "react";
import { PatternNote } from "@/components/PatternNote";
import { Crt } from "@/components/Crt";
import { TopBar } from "@/components/TopBar";
import { Loading, Failed, Note } from "@/components/ui";
import { useRun } from "@/lib/useRun";
import { api, NotAvailableOffline } from "@/lib/api";
import type { CalibrationRow } from "@/types/simulation";

const MIN_N = 30;      // L2: a flag needs both a big error and enough responses

export function Calibration() {
  const { run, error } = useRun();
  const [decision, setDecision] = useState<"pending" | "applied" | "rejected">("pending");
  const [decideError, setDecideError] = useState<string | null>(null);

  async function decide(approved: boolean) {
    setDecideError(null);
    try {
      await api.applyCalibration(run?.run_id ?? "latest", approved);
      setDecision(approved ? "applied" : "rejected");
    } catch (e) {
      setDecideError(e instanceof NotAvailableOffline
        ? "Not recorded: the calibration service is not running."
        : (e as Error).message);
    }
  }

  if (error) return <Crt><TopBar /><Failed message={error} /></Crt>;
  if (!run) return <Crt><TopBar /><Loading what="the consultation" /></Crt>;

  const c = run.consultation;
  const overall = c.calibration.find((r) => r.cohort_axis === "overall");
  const flagged = c.calibration.filter((r) => r.flagged);
  const commented = c.responses.filter((r) => r.comment);
  const headline = commented[0];
  const adj = c.proposed_adjustment;


  return (
    <Crt>
      <TopBar meta={`${c.response_count} RESPONSES · SEEDED FOR DEMO`} />

      <div className="grid-split" style={{ flexGrow: 1, display: "grid", gridTemplateColumns: "1fr 424px", minHeight: 0 }}>
        <section style={{ padding: "var(--s-5) var(--s-5)", borderRight: "1px solid var(--rule)", display: "flex", flexDirection: "column", gap: "var(--s-4)", overflowY: "auto" }}>
          <div>
            <h2
              className="t1"
              style={{ fontSize: "var(--fs-28)", fontWeight: 500, lineHeight: 1.2, letterSpacing: ".015em", margin: "0 0 10px" }}
            >
              {overall && Math.abs(overall.signed_error) < 10
                ? "THE OVERALL NUMBER LOOKED FINE. IT WAS NOT."
                : "PREDICTED VERSUS OBSERVED"}
            </h2>
            <p className="t2" style={{ fontSize: "var(--fs-16)", lineHeight: 1.55, margin: 0, maxWidth: "74ch" }}>
              {overall && (
                <>
                  {Math.abs(overall.signed_error).toFixed(1)} points off overall.{" "}
                  {flagged.length > 0 ? (
                    <>
                      {Math.abs(flagged[0].signed_error).toFixed(1)} points off among{" "}
                      {flagged[0].cohort_value}, where the walk actually changed.
                    </>
                  ) : (
                    <>No cohort cleared the flag threshold in this run.</>
                  )}
                </>
              )}
            </p>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <div style={{ ...gridRow, padding: "0 12px 8px", margin: "0 -12px", borderBottom: "1px solid var(--rule-strong)" }}>
              <span className="t3" style={hdr}>COHORT</span>
              <span className="t3" style={hdr}>PREDICTED VERSUS OBSERVED</span>
              <span className="t3" style={{ ...hdr, textAlign: "right" }}>ERROR</span>
              <span className="t3" style={{ ...hdr, textAlign: "right" }}>N</span>
            </div>
            {c.calibration.map((r) => <Row key={r.cohort_value + r.cohort_axis} r={r} />)}
            <p className="t3" style={{ fontSize: "var(--fs-12)", textAlign: "right", margin: "2px 0 0" }}>
              a flag needs an error above 10 points and at least {MIN_N} responses
            </p>
          </div>

          {flagged.length > 0 && (
            <Note tone="alert">
              <p className="t1" style={{ fontSize: "var(--fs-14)", lineHeight: 1.6, margin: 0 }}>
                The model assumed a longer walk is a longer walk. Residents on{" "}
                {c.discovered_constraint.location} told us it is not: the covered walkway ends
                partway, and there is a slope. Support there is {Math.abs(flagged[0].signed_error).toFixed(1)}
                {" "}points below what the model expected.
              </p>
            </Note>
          )}

          <PatternNote run={run} pattern="participation_gap" />

          <div style={{ marginTop: "auto", borderTop: "1px solid var(--rule)", paddingTop: 16 }}>
            <div className="box" style={{ display: "flex", alignItems: "center", gap: 16, padding: "14px 17px", flexWrap: "wrap" }}>
              <span className="t2" style={{ fontSize: "var(--fs-14)" }}>{adj.parameter}</span>
              <span className="t3" style={{ fontSize: "var(--fs-16)" }}>{adj.from.toFixed(2)}</span>
              <span className="t3" style={{ fontSize: "var(--fs-14)" }}>&gt;&gt;</span>
              <span className="gold" style={{ fontSize: "var(--fs-20)", fontWeight: 600 }}>{adj.to.toFixed(2)}</span>
              <div style={{ flexGrow: 1 }} />
              {decision === "pending" ? (
                <>
                  <button className="btn-ghost" style={{ padding: "9px 40px 9px 16px" }} onClick={() => decide(false)}>
                    REJECT
                  </button>
                  <button className="btn" style={{ padding: "9px 44px 9px 16px" }} onClick={() => decide(true)}>
                    APPLY AND RECORD
                  </button>
                </>
              ) : (
                <span className={decision === "applied" ? "gold" : "t3"} style={{ fontSize: "var(--fs-14)" }}>
                  {decision === "applied" ? "Applied and recorded in calibration history." : "Rejected. The record keeps that too."}
                </span>
              )}
            </div>
            {decideError && (
              <p className="alert" style={{ fontSize: "var(--fs-12)", margin: "10px 0 0", lineHeight: 1.55 }}>
                {decideError}
              </p>
            )}
            <p className="t3" style={{ fontSize: "var(--fs-12)", margin: "10px 0 0", lineHeight: 1.55 }}>
              Nothing is applied automatically. The proposal and your decision both go into
              calibration history.
            </p>
          </div>
        </section>

        {/* ---- PCS, the comment, the themes ---- */}
        <aside style={{ display: "flex", flexDirection: "column", overflowY: "auto" }}>
          <div style={{ padding: "var(--s-3)", borderBottom: "1px solid var(--rule)" }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 11 }}>
              <span className="t1" style={{ fontSize: "var(--fs-40)", fontWeight: 500, lineHeight: 0.9 }}>
                {c.pcs.score}
              </span>
              <span className="t3" style={{ fontSize: "var(--fs-14)" }}>public confidence, of 100</span>
            </div>
            {/* the score never ships without its components. K4. */}
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--s-1)", marginTop: 16 }}>
              {Object.entries(c.pcs.components).map(([k, v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between" }}>
                  <span className="t2" style={{ fontSize: "var(--fs-14)" }}>
                    {k.replaceAll("_", " ").replace(/^./, (m) => m.toUpperCase())}
                  </span>
                  <span className="t1" style={{ fontSize: "var(--fs-14)" }}>{v}</span>
                </div>
              ))}
            </div>
            <p className="t3" style={{ fontSize: "var(--fs-12)", lineHeight: 1.5, margin: "13px 0 0", borderTop: "1px solid var(--rule-dim)", paddingTop: 11 }}>
              {c.response_count} responses, self-selected. Not a representative sample of{" "}
              {run.study_area} residents, and not weighted to be one.
            </p>
          </div>

          {headline && (
            <div style={{ padding: "var(--s-3)", borderBottom: "1px solid var(--rule)" }}>
              <p className="t1" style={{ fontSize: "var(--fs-14)", lineHeight: 1.65, margin: 0, paddingLeft: 13, borderLeft: "1px solid var(--rule-strong)" }}>
                “{headline.comment}”
              </p>
              <div className="t3" style={{ fontSize: "var(--fs-12)", marginTop: 10 }}>
                resident · {headline.cohort.home_subzone} · age {headline.cohort.age_band}
                {headline.is_seeded ? " · seeded for demo" : ""}
              </div>

              <div className="box" style={{ marginTop: 14, padding: "12px 14px", fontSize: "var(--fs-12)", lineHeight: 1.8 }}>
                <span className="gold">DISCOVERED CONSTRAINT</span>
                <br />
                <span className="t2">
                  type: {c.discovered_constraint.type}
                  <br />
                  location: {c.discovered_constraint.location}
                  <br />
                  affects: {c.discovered_constraint.affects.join(", ")}
                  <br />
                  source: {c.discovered_constraint.source}
                </span>
              </div>
              <p className="t3" style={{ fontSize: "var(--fs-12)", lineHeight: 1.55, margin: "11px 0 0" }}>
                {c.discovered_constraint.note}
              </p>
              <button className="btn-ghost" style={{ marginTop: 12, width: "100%", justifyContent: "flex-start" }}>
                RE-SIMULATE WITH THIS CONSTRAINT
              </button>
            </div>
          )}
        </aside>
      </div>
    </Crt>
  );
}

function Row({ r }: { r: CalibrationRow }) {
  const tooFew = r.n < MIN_N;
  return (
    <div
      style={{
        ...gridRow, padding: "9px 12px", margin: "0 -12px",
        background: r.flagged ? "rgba(239,78,54,.10)" : undefined,
        opacity: tooFew ? 0.55 : 1,
      }}
    >
      <span className="t1" style={{ fontSize: "var(--fs-14)" }}>{r.cohort_value}</span>
      <div style={{ position: "relative", height: 20, border: "1px solid var(--rule-strong)" }}>
        <div style={{ position: "absolute", inset: 0, width: `${r.predicted_support}%`, background: "var(--rule-strong)" }} />
        <div
          style={{
            position: "absolute", left: 0, top: 4, bottom: 4, width: "100%",
            transformOrigin: "left",
            transform: `scaleX(${(r.observed_support / 100).toFixed(4)})`,
            background: r.flagged ? "var(--alert)" : "var(--fig-quiet)",
            transition: "transform .6s cubic-bezier(.16,1,.3,1)",
          }}
        />
      </div>
      <span
        className={r.flagged ? "alert" : "t2"}
        style={{ fontSize: r.flagged ? "var(--fs-20)" : "var(--fs-14)", textAlign: "right", fontWeight: 600 }}
      >
        {r.signed_error > 0 ? "+" : ""}{r.signed_error.toFixed(1)}
      </span>
      <span className={tooFew ? "alert" : "t3"} style={{ fontSize: "var(--fs-12)", textAlign: "right" }}>
        {r.n}
      </span>
    </div>
  );
}

const gridRow = {
  display: "grid",
  gridTemplateColumns: "150px 1fr 86px 58px",
  alignItems: "center",
  gap: "var(--s-3)",
};

const hdr = { fontSize: "var(--fs-12)" };
