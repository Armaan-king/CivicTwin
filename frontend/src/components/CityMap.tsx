import { useMemo, useState } from "react";
import type { Geography, Persona, PersonaOutcome, SimEvent, CityBlock } from "@/types/simulation";

/**
 * The estate in plan, and it moves.
 *
 * Harm lands round by round rather than appearing all at once, so you can watch the
 * consequence spread instead of reading a finished picture. Blocks are hoverable and
 * selectable, because "which people are these" is the question the map should answer.
 */

export interface BlockDetail {
  block: CityBlock;
  residents: Persona[];
  severe: number;
  moderate: number;
  carers: number;
}

export interface CityMapProps {
  geography: Geography;
  personas: Persona[];
  outcomes: Map<string, PersonaOutcome>;
  events: SimEvent[];
  /** 0 shows the estate before the policy; 3 shows the full cascade */
  round: number;
  selected: string | null;
  onSelect: (blockId: string | null) => void;
  ties?: { source: string; target: string }[];
}

export function CityMap({
  geography, personas, outcomes, events, round, selected, onSelect, ties = [],
}: CityMapProps) {
  const [hover, setHover] = useState<string | null>(null);
  const [spanX, spanY] = geography.span;

  /** the round each persona's harm first shows up, so the map can reveal in step */
  const landsAt = useMemo(() => {
    const m = new Map<string, number>();
    for (const e of events) {
      const cur = m.get(e.persona_id);
      if (cur === undefined || e.round < cur) m.set(e.persona_id, e.round);
    }
    return m;
  }, [events]);

  /** severe count per block, but only counting harm that has landed by this round */
  const harmNow = useMemo(() => {
    const m = new Map<string, { severe: number; total: number }>();
    for (const p of personas) {
      const rec = m.get(p.block_id) ?? { severe: 0, total: 0 };
      rec.total += 1;
      const at = landsAt.get(p.persona_id);
      if (
        at !== undefined && at <= round &&
        outcomes.get(p.persona_id)?.severity === "high"
      ) {
        rec.severe += 1;
      }
      m.set(p.block_id, rec);
    }
    return m;
  }, [personas, outcomes, landsAt, round]);

  const blockById = useMemo(
    () => new Map(geography.blocks.map((b) => [b.block_id, b])),
    [geography.blocks]
  );
  const personaById = useMemo(
    () => new Map(personas.map((p) => [p.persona_id, p])),
    [personas]
  );

  const centre = (personaId: string) => {
    const b = blockById.get(personaById.get(personaId)?.block_id ?? "");
    return b ? { x: b.x + b.w / 2, y: b.y + b.h / 2 } : null;
  };

  return (
    <svg
      viewBox={`-40 -46 ${spanX + 80} ${spanY + 100}`}
      style={{ width: "100%", height: "100%", display: "block" }}
      onPointerLeave={() => setHover(null)}
      role="img"
      aria-label="Plan of the estate. Blocks darken to red as residents lose an essential trip, round by round."
    >
      <defs>
        <filter id="mapGlow" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="5" result="b" />
          <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>

      {geography.roads.map((r, i) => (
        <line
          key={i}
          x1={r.x1} y1={r.y1} x2={r.x2} y2={r.y2}
          stroke={r.kind === "arterial" ? "#2f2a23" : "#1c1915"}
          strokeWidth={r.kind === "arterial" ? 17 : 7}
          strokeLinecap="square"
        />
      ))}

      {geography.blocks.map((b) => {
        const rec = harmNow.get(b.block_id);
        const rate = rec && rec.total ? rec.severe / rec.total : 0;
        const hot = rate > 0.22;
        const mid = rate > 0.05;
        const on = selected === b.block_id;
        const near = hover === b.block_id;
        return (
          <g
            key={b.block_id}
            onPointerEnter={() => setHover(b.block_id)}
            onClick={() => onSelect(on ? null : b.block_id)}
            style={{ cursor: "pointer" }}
          >
            <rect
              x={b.x} y={b.y} width={b.w} height={b.h}
              fill={hot ? "rgba(239,78,54,.34)" : mid ? "rgba(242,176,36,.15)" : "#16130f"}
              stroke={on ? "var(--gold)" : hot ? "var(--alert)" : near ? "var(--t3)" : mid ? "rgba(242,176,36,.45)" : "#232019"}
              strokeWidth={on ? 2.4 : hot ? 1.5 : 1}
              filter={hot ? "url(#mapGlow)" : undefined}
              style={{ transition: "fill .45s ease, stroke .18s ease" }}
            />
            {hot &&
              Array.from({ length: Math.min(7, rec!.severe) }).map((_, i) => (
                <rect
                  key={i}
                  x={b.x + 5 + i * 7} y={b.y + b.h - 10}
                  width={3.6} height={6}
                  fill="var(--alert)"
                />
              ))}
          </g>
        );
      })}

      <g style={{ pointerEvents: "none" }}>
        <rect
          x={geography.polyclinic.x - 14} y={geography.polyclinic.y - 14}
          width={28} height={28} fill="#16130f" stroke="var(--t2)" strokeWidth={1.8}
        />
        <path
          d={`M ${geography.polyclinic.x} ${geography.polyclinic.y - 8} v 16 M ${geography.polyclinic.x - 8} ${geography.polyclinic.y} h 16`}
          stroke="var(--t2)" strokeWidth={2.4}
        />
        <text
          x={geography.polyclinic.x} y={geography.polyclinic.y + 34}
          textAnchor="middle" fontSize={13} fill="var(--t2)" fontFamily="var(--font-ui)"
        >
          Polyclinic
        </text>
      </g>

      <polyline
        points={geography.route.map(([x, y]) => `${x},${y}`).join(" ")}
        fill="none" stroke="var(--gold)" strokeWidth={2.6}
        style={{ pointerEvents: "none" }}
      />

      {geography.stops.map((s) => (
        <g key={s.stop_id} style={{ pointerEvents: "none" }}>
          {s.removed && round >= 1 ? (
            <>
              <rect x={s.x - 8} y={s.y - 8} width={16} height={16} fill="var(--ground)" stroke="var(--alert)" strokeWidth={2.2} />
              <path d={`M ${s.x - 8} ${s.y - 8} l 16 16 M ${s.x + 8} ${s.y - 8} l -16 16`} stroke="var(--alert)" strokeWidth={2.2} />
              <text x={s.x} y={s.y - 17} textAnchor="middle" fontSize={12} fill="var(--alert)" fontFamily="var(--font-ui)">
                {s.stop_id}
              </text>
            </>
          ) : (
            <>
              <circle cx={s.x} cy={s.y} r={5} fill="var(--ground)" stroke="var(--gold)" strokeWidth={2.2} />
              {s.name === "Interchange" && (
                <text x={s.x} y={s.y - 15} textAnchor="middle" fontSize={12} fill="var(--t3)" fontFamily="var(--font-ui)">
                  Interchange
                </text>
              )}
            </>
          )}
        </g>
      ))}

      {round >= 2 &&
        ties.slice(0, 18).map((t, i) => {
          const a = centre(t.source);
          const b = centre(t.target);
          if (!a || !b) return null;
          const midY = Math.min(a.y, b.y) - 46;
          return (
            <path
              key={i}
              d={`M ${a.x} ${a.y} Q ${(a.x + b.x) / 2} ${midY} ${b.x} ${b.y}`}
              fill="none" stroke="var(--alert)" strokeWidth={1.2}
              strokeDasharray="6 5" opacity={0.85}
              style={{ pointerEvents: "none" }}
            />
          );
        })}
    </svg>
  );
}

/** Everything the detail panel needs about one block. */
export function blockDetail(
  blockId: string,
  geography: Geography,
  personas: Persona[],
  outcomes: Map<string, PersonaOutcome>
): BlockDetail | null {
  const block = geography.blocks.find((b) => b.block_id === blockId);
  if (!block) return null;
  const residents = personas.filter((p) => p.block_id === blockId);
  return {
    block,
    residents,
    severe: residents.filter((p) => outcomes.get(p.persona_id)?.severity === "high").length,
    moderate: residents.filter((p) => outcomes.get(p.persona_id)?.severity === "moderate").length,
    carers: residents.filter((p) => p.is_caregiver).length,
  };
}
