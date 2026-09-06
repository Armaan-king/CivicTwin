import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Crt } from "@/components/Crt";
import { TopBar } from "@/components/TopBar";
import { Loading, Failed } from "@/components/ui";
import { CityMap, blockDetail } from "@/components/CityMap";
import { Boundary } from "@/components/Boundary";
import { useRun } from "@/lib/useRun";

const ROUND_LABEL = [
  "Before the change",
  "Walks lengthen, thresholds break",
  "Households absorb it",
  "Carers breach their own constraints",
];

const ROUND_NOTE = [
  "The estate as it stands. Two stops on the corridor are about to be removed.",
  "Residents routed onto a longer walk. Where it passes what they said they manage, an essential trip stops being reachable.",
  "A household member starts making the journey instead, along a CARES_FOR link.",
  "That person now misses their own shift. They have no mobility limitation and do not live near a removed stop.",
];

const DWELL_MS = 2200;

export function Simulation() {
  const { run, outcomes, error } = useRun();
  const navigate = useNavigate();

  const [round, setRound] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const timer = useRef<number | null>(null);

  // autoplay walks the cascade once, then stops and leaves it there
  useEffect(() => {
    if (!playing || !run) return;
    if (round >= 3) { setPlaying(false); return; }
    timer.current = window.setTimeout(() => setRound((r) => r + 1), DWELL_MS);
    return () => { if (timer.current) window.clearTimeout(timer.current); };
  }, [playing, round, run]);

  const landsAt = useMemo(() => {
    const m = new Map<string, number>();
    if (!run) return m;
    for (const e of run.events) {
      const cur = m.get(e.persona_id);
      if (cur === undefined || e.round < cur) m.set(e.persona_id, e.round);
    }
    return m;
  }, [run]);

  /** counters climb as the cascade advances, rather than sitting at the final number */
  const live = useMemo(() => {
    if (!run) return { severe: 0, moderate: 0, carers: 0 };
    let severe = 0, moderate = 0, carers = 0;
    for (const o of run.outcomes) {
      const at = landsAt.get(o.persona_id);
      if (at === undefined || at > round) continue;
      if (o.severity === "high") severe += 1;
      if (o.severity === "moderate") moderate += 1;
      if (o.second_order && round >= 3) carers += 1;
    }
    return { severe, moderate, carers };
  }, [run, landsAt, round]);

  const ties = useMemo(
    () => (run
      ? run.graph.edges
          .filter((e) => e.kind === "CARES_FOR" && outcomes.get(e.source)?.second_order)
          .map((e) => ({ source: e.source, target: e.target }))
      : []),
    [run, outcomes]
  );

  const detail = useMemo(
    () => (run && selected ? blockDetail(selected, run.geography, run.personas, outcomes) : null),
    [run, selected, outcomes]
  );

  if (error) return <Crt><TopBar /><Failed message={error} /></Crt>;
  if (!run) return <Crt><TopBar /><Loading what="the estate" /></Crt>;

  const replay = () => { setRound(0); setPlaying(true); };

  return (
    <Crt>
      <TopBar meta={`RUN ${run.run_id.toUpperCase()}`} />

      <div style={{ padding: "var(--s-5) var(--s-6) var(--s-3)", flexShrink: 0 }}>
        <h1 className="t1" style={{ fontSize: "var(--fs-28)", fontWeight: 500, letterSpacing: ".01em", margin: "0 0 var(--s-2)" }}>
          {ROUND_LABEL[round]}
        </h1>
        <p className="t2" style={{ fontSize: "var(--fs-16)", lineHeight: 1.7, margin: 0, maxWidth: "70ch" }}>
          {ROUND_NOTE[round]}
        </p>
      </div>

      <div className="grid-split"
        style={{
          flexGrow: 1, display: "grid",
          gridTemplateColumns: "minmax(0, 1fr) minmax(0, 340px)",
          gap: "var(--s-6)", padding: "0 var(--s-6) var(--s-4)", minHeight: 0,
        }}
      >
        <div style={{ position: "relative", minHeight: 0 }}>
          <Boundary label="The estate map">
          <CityMap
            geography={run.geography}
            personas={run.personas}
            outcomes={outcomes}
            events={run.events}
            round={round}
            selected={selected}
            onSelect={setSelected}
            ties={ties}
          />
          </Boundary>
        </div>

        <aside style={{ display: "flex", flexDirection: "column", gap: "var(--s-4)", overflowY: "auto" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--s-3)" }}>
            <Counter label="Lost an essential trip" value={live.severe} tone="alert" />
            <Counter label="Walking further" value={live.moderate} tone="gold" />
            <Counter label="Harmed through someone else" value={live.carers} tone="alert" muted={round < 3} />
          </div>

          {detail ? (
            <div style={{ borderTop: "1px solid var(--rule)", paddingTop: "var(--s-3)" }}>
              <div className="t3" style={{ fontSize: "var(--fs-12)" }}>{detail.block.subzone}</div>
              <div className="t1" style={{ fontSize: "var(--fs-20)", margin: "var(--s-1) 0 var(--s-2)" }}>
                {detail.residents.length} residents
              </div>
              <Line label="Lost an essential trip" value={detail.severe} tone={detail.severe ? "alert" : "t3"} />
              <Line label="Walking further" value={detail.moderate} tone={detail.moderate ? "gold" : "t3"} />
              <Line label="Carers living here" value={detail.carers} tone={detail.carers ? "alert" : "t3"} />
              <button
                onClick={() => setSelected(null)}
                style={{
                  marginTop: "var(--s-2)", background: "none", border: "none", padding: 0,
                  cursor: "pointer", fontFamily: "inherit", fontSize: "var(--fs-12)",
                  color: "var(--t3)", textDecoration: "underline", textUnderlineOffset: 3,
                }}
              >
                clear selection
              </button>
            </div>
          ) : (
            <p className="t3" style={{ fontSize: "var(--fs-14)", lineHeight: 1.7, margin: 0, borderTop: "1px solid var(--rule)", paddingTop: "var(--s-3)" }}>
              Click any block to see who lives there and what the policy did to them.
            </p>
          )}

          <div style={{ marginTop: "auto" }}>
            <button className="btn" onClick={() => navigate("/impact")}>OPEN IMPACT AUDIT</button>
          </div>
        </aside>
      </div>

      {/* transport: play, scrub, replay */}
      <div
        style={{
          display: "flex", alignItems: "center", gap: "var(--s-3)",
          padding: "var(--s-3) var(--s-6) var(--s-4)",
          borderTop: "1px solid var(--rule)", flexShrink: 0,
        }}
      >
        <button
          onClick={() => (round >= 3 ? replay() : setPlaying((p) => !p))}
          aria-label={round >= 3 ? "Replay" : playing ? "Pause" : "Play"}
          style={{
            width: 44, height: 44, flexShrink: 0, cursor: "pointer",
            background: "var(--gold)", color: "var(--ground)", border: "none",
            borderRadius: 0, display: "grid", placeItems: "center", fontFamily: "inherit",
          }}
        >
          <svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
            {round >= 3 ? (
              <path d="M8 2a6 6 0 1 0 6 6h-2a4 4 0 1 1-4-4v2l3.2-3L8 0z" />
            ) : playing ? (
              <><rect x="3" y="2" width="3.5" height="12" /><rect x="9.5" y="2" width="3.5" height="12" /></>
            ) : (
              <path d="M4 2l10 6-10 6z" />
            )}
          </svg>
        </button>

        <div style={{ display: "flex", gap: 4 }}>
          {[0, 1, 2, 3].map((r) => (
            <button
              key={r}
              onClick={() => { setPlaying(false); setRound(r); }}
              aria-pressed={round === r}
              aria-label={`Round ${r}: ${ROUND_LABEL[r]}`}
              style={{
                minWidth: 44, height: 44, cursor: "pointer", fontFamily: "inherit",
                fontSize: "var(--fs-14)", borderRadius: 0,
                border: `1px solid ${round === r ? "var(--gold)" : "var(--rule)"}`,
                background: round === r ? "rgba(242,176,36,.14)" : "transparent",
                color: round === r ? "var(--gold)" : "var(--t3)",
                fontWeight: round === r ? 600 : 400,
              }}
            >
              {r}
            </button>
          ))}
        </div>

        {/* progress through the cascade, not a time axis */}
        <div style={{ flexGrow: 1, height: 2, background: "var(--rule)", position: "relative" }}>
          <div
            style={{
              position: "absolute", inset: 0, transformOrigin: "left",
              transform: `scaleX(${round / 3})`, background: "var(--gold)",
              transition: `transform ${playing ? DWELL_MS : 240}ms linear`,
            }}
          />
        </div>

        <span className="t3" style={{ fontSize: "var(--fs-12)", flexShrink: 0 }}>
          propagation depth, not elapsed time
        </span>
      </div>
    </Crt>
  );
}

function Counter({
  label, value, tone, muted = false,
}: { label: string; value: number; tone: "alert" | "gold"; muted?: boolean }) {
  return (
    <div style={{ opacity: muted ? 0.35 : 1, transition: "opacity .4s ease" }}>
      <div
        className={tone}
        style={{ fontSize: "var(--fs-40)", fontWeight: 500, lineHeight: 1, fontVariantNumeric: "tabular-nums" }}
      >
        {value}
      </div>
      <div className="t3" style={{ fontSize: "var(--fs-14)", marginTop: 4 }}>{label}</div>
    </div>
  );
}

function Line({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 0" }}>
      <span className="t2" style={{ fontSize: "var(--fs-14)" }}>{label}</span>
      <span className={tone} style={{ fontSize: "var(--fs-14)" }}>{value}</span>
    </div>
  );
}
