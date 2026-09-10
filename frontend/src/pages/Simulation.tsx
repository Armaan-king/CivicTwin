import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Crt } from "@/components/Crt";
import { TopBar } from "@/components/TopBar";
import { Loading, Failed } from "@/components/ui";
import { CityMap, blockDetail } from "@/components/CityMap";
import { Boundary } from "@/components/Boundary";
import { useRun } from "@/lib/useRun";
import { stageLabels, stageNotes, townName, corridorCaption, serviceLabel } from "@/lib/naming";

const DWELL_MS = 3300;

export function Simulation() {
  const { run, outcomes, error } = useRun();
  // Derived from this run's own policy: a Bedok closure must not be captioned
  // "Ang Mo Kio", which is what these strings did when they were literals.
  const ROUND_LABEL = useMemo(() => stageLabels(run), [run]);
  const ROUND_NOTE = useMemo(() => stageNotes(run), [run]);
  const navigate = useNavigate();
  const [round, setRound] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (!playing || !run) return;
    if (round >= 3) {
      setPlaying(false);
      return;
    }
    timer.current = window.setTimeout(() => setRound((value) => value + 1), DWELL_MS);
    return () => {
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [playing, round, run]);

  const targets = useMemo(() => {
    if (!run || round === 0) return { severe: 0, moderate: 0, carers: 0 };
    const landed = run.events.filter((event) => event.round <= round);
    const severeIds = new Set(
      landed
        .filter((event) => event.kind === "ESSENTIAL_ACCESS_LOST" || event.kind === "OBLIGATION_MISSED")
        .map((event) => event.persona_id),
    );
    const landedIds = new Set(landed.map((event) => event.persona_id));
    const moderate = run.outcomes.filter(
      (outcome) => outcome.severity === "moderate" && landedIds.has(outcome.persona_id),
    ).length;
    const carers = new Set(
      landed.filter((event) => event.kind === "OBLIGATION_MISSED").map((event) => event.persona_id),
    ).size;
    return { severe: severeIds.size, moderate, carers };
  }, [round, run]);

  const ties = useMemo(
    () => (run
      ? run.graph.edges
          .filter((edge) => edge.kind === "CARES_FOR" && outcomes.get(edge.source)?.second_order)
          .map((edge) => ({ source: edge.source, target: edge.target }))
      : []),
    [run, outcomes],
  );

  const detail = useMemo(
    () => (run && selected ? blockDetail(selected, run.geography, run.personas, outcomes) : null),
    [run, selected, outcomes],
  );

  if (error) return <Crt><TopBar /><Failed message={error} /></Crt>;
  if (!run) return <Crt><TopBar /><Loading what="the estate" /></Crt>;

  const replay = () => {
    setRound(0);
    setPlaying(true);
    setSelected(null);
  };
  const chooseRound = (value: number) => {
    setPlaying(false);
    setRound(value);
  };

  return (
    <Crt>
      <TopBar meta={"RUN " + run.run_id.toUpperCase()} />

      <main className="simulation-page">
        <header className="simulation-header">
          <div className="simulation-story">
            <span className="page-kicker">Stage {round + 1} of 4</span>
            <h1>{ROUND_LABEL[round]}</h1>
            <p>{ROUND_NOTE[round]}</p>
          </div>

          <div className="simulation-controls" aria-label="Simulation progress">
            <button
              type="button"
              className="simulation-play"
              onClick={() => (round >= 3 ? replay() : setPlaying((value) => !value))}
              aria-label={round >= 3 ? "Replay simulation" : playing ? "Pause simulation" : "Play simulation"}
            >
              <svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                {round >= 3 ? (
                  <path d="M8 2a6 6 0 1 0 6 6h-2a4 4 0 1 1-4-4v2l3.2-3L8 0z" />
                ) : playing ? (
                  <><rect x="3" y="2" width="3.5" height="12" /><rect x="9.5" y="2" width="3.5" height="12" /></>
                ) : (
                  <path d="M4 2l10 6-10 6z" />
                )}
              </svg>
            </button>

            <div className="simulation-rounds">
              <div>
                {[0, 1, 2, 3].map((value) => (
                  <button
                    type="button"
                    key={value}
                    onClick={() => chooseRound(value)}
                    aria-pressed={round === value}
                    aria-label={"Stage " + (value + 1) + ": " + ROUND_LABEL[value]}
                  >
                    {value + 1}
                  </button>
                ))}
              </div>
              <span aria-hidden="true">
                <i style={{ width: (round / 3) * 100 + "%" }} />
              </span>
            </div>

            <button type="button" className="btn simulation-next" onClick={() => navigate("/impact")}>
              REVIEW IMPACT
            </button>
          </div>
        </header>

        <section className="simulation-map-panel" aria-label="Simulation map and results">
          <div className="simulation-map-location">
            <strong>{townName(run)}</strong>
            <span>{corridorCaption(run)}</span>
          </div>
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
              removedStopIds={run.policy.modifications.remove_stops}
              mapLabel={`Interactive map of the ${serviceLabel(run)} corridor in ${townName(run)}.`}
            />
          </Boundary>

          <aside className="simulation-stats" aria-label="Current impact totals">
            <Counter label="Essential trips lost" value={targets.severe} tone="danger" />
            <Counter label="Residents walking further" value={targets.moderate} tone="warning" />
            <Counter label="Family carers affected" value={targets.carers} tone="danger" muted={round < 3} />
          </aside>

          {detail ? (
            <aside className="simulation-block-detail">
              <div>
                <span>{detail.block.subzone}</span>
                <strong>{detail.residents.length} residents</strong>
              </div>
              <p>{detail.severe} severe · {detail.moderate} moderate · {detail.carers} carers</p>
              <button type="button" onClick={() => setSelected(null)}>Close</button>
            </aside>
          ) : (
            <div className="simulation-map-hint">Drag to move · Scroll to zoom · Select a block</div>
          )}
        </section>
      </main>
    </Crt>
  );
}

function useStepCount(target: number) {
  const [display, setDisplay] = useState(target === 0 ? 0 : target);
  const current = useRef(display);

  useEffect(() => {
    if (target === 0 || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      current.current = target;
      setDisplay(target);
      return;
    }
    const direction = target > current.current ? 1 : -1;
    const distance = Math.abs(target - current.current);
    if (!distance) return;
    const interval = Math.max(34, Math.min(100, 1500 / distance));
    const timer = window.setInterval(() => {
      const next = current.current + direction;
      current.current = next;
      setDisplay(next);
      if (next === target) window.clearInterval(timer);
    }, interval);
    return () => window.clearInterval(timer);
  }, [target]);

  return display;
}

function Counter({
  label,
  value,
  tone,
  muted = false,
}: {
  label: string;
  value: number;
  tone: "danger" | "warning";
  muted?: boolean;
}) {
  const display = useStepCount(value);
  return (
    <div className={"simulation-counter " + tone + (muted ? " muted" : "")}>
      <strong>{display}</strong>
      <span>{label}</span>
    </div>
  );
}
