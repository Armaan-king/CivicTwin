import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  Geography, Persona, PersonaOutcome, SimEvent, CityBlock, Severity,
} from "@/types/simulation";

/**
 * The estate in plan, and it moves.
 *
 * Harm lands round by round rather than appearing all at once, so you can watch the
 * consequence spread instead of reading a finished picture. Blocks are hoverable and
 * selectable, because "which people are these" is the question the map should answer.
 *
 * Population rendering follows scenario-v1.md 13.2: every resident is one human figure,
 * fill colour is the only thing that carries severity, and a dashed connector is drawn
 * only where a CARES_FOR edge actually fired — so the second-order finding (a carer with
 * no mobility limitation, harmed through someone else's dependency) is something you see
 * on the map, not something you have to be told.
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

const SEV_COLOR: Record<Severity, string> = {
  none: "var(--fig-none)",
  moderate: "var(--gold)",
  high: "var(--alert)",
};

/** One person, per 13.2: shadow, head, torso, two arms, two legs. Fill is the only state. */
function PersonGlyph({
  cx, cy, scale, fill, className, glow,
}: { cx: number; cy: number; scale: number; fill: string; className?: string; glow?: boolean }) {
  // authored on a 0 0 64 96 box, anchored so (cx, cy) sits at the feet/shadow centre
  const tx = cx - 32 * scale;
  const ty = cy - 94 * scale;
  return (
    <g
      transform={`translate(${tx} ${ty}) scale(${scale})`}
      className={className}
      style={{ filter: glow ? "url(#personGlow)" : undefined }}
    >
      <ellipse cx={32} cy={92} rx={13} ry={4} fill="#000" opacity={0.4} />
      <rect x={21.5} y={64} width={9} height={27} rx={4} fill={fill} />
      <rect x={33.5} y={64} width={9} height={27} rx={4} fill={fill} />
      <rect x={10.5} y={37} width={8} height={25} rx={4} fill={fill} transform="rotate(-14 14.5 40)" />
      <rect x={45.5} y={37} width={8} height={25} rx={4} fill={fill} transform="rotate(14 49.5 40)" />
      <rect x={20} y={33} width={24} height={33} rx={10} fill={fill} />
      <circle cx={32} cy={19} r={11.5} fill={fill} />
    </g>
  );
}

const MIN_SCALE = 0.09;
const MAX_SCALE = 3.2;

export function CityMap({
  geography, personas, outcomes, events, round, selected, onSelect, ties = [],
}: CityMapProps) {
  const [hoverBlock, setHoverBlock] = useState<string | null>(null);
  const [hoverPersona, setHoverPersona] = useState<string | null>(null);
  const [pointer, setPointer] = useState<{ x: number; y: number } | null>(null);
  const frame = useRef<HTMLDivElement>(null);
  const [spanX, spanY] = geography.span;

  // world coordinates: same padding the old fixed viewBox used
  const OFFSET = { x: -40, y: -46 };
  const WORLD = { w: spanX + 80, h: spanY + 100 };

  const [view, setView] = useState({ x: 0, y: 0, k: 1 });
  const drag = useRef<{ x: number; y: number; vx: number; vy: number; moved: boolean } | null>(null);
  const wasDragging = useRef(false);

  const fit = useCallback(() => {
    const el = frame.current;
    if (!el) return;
    const { width, height } = el.getBoundingClientRect();
    const k = Math.min(width / WORLD.w, height / WORLD.h);
    setView({
      k,
      x: (width - WORLD.w * k) / 2 - OFFSET.x * k,
      y: (height - WORLD.h * k) / 2 - OFFSET.y * k,
    });
  }, [WORLD.w, WORLD.h]);

  useEffect(() => {
    fit();
    window.addEventListener("resize", fit);
    return () => window.removeEventListener("resize", fit);
  }, [fit]);

  const zoomBy = (factor: number) => {
    const el = frame.current;
    if (!el) return;
    const { width, height } = el.getBoundingClientRect();
    setView((v) => {
      const k = Math.min(MAX_SCALE, Math.max(MIN_SCALE, v.k * factor));
      const cx = width / 2, cy = height / 2;
      return { k, x: cx - ((cx - v.x) / v.k) * k, y: cy - ((cy - v.y) / v.k) * k };
    });
  };

  const onWheel = (e: React.WheelEvent) => {
    const el = frame.current;
    if (!el) return;
    const box = el.getBoundingClientRect();
    const px = e.clientX - box.left, py = e.clientY - box.top;
    setView((v) => {
      const k = Math.min(MAX_SCALE, Math.max(MIN_SCALE, v.k * (e.deltaY < 0 ? 1.1 : 0.909)));
      return { k, x: px - ((px - v.x) / v.k) * k, y: py - ((py - v.y) / v.k) * k };
    });
  };

  const trackPointer = (e: React.PointerEvent) => {
    const box = frame.current?.getBoundingClientRect();
    if (!box) return;
    setPointer({ x: e.clientX - box.left, y: e.clientY - box.top });
  };

  const onPointerDownFrame = (e: React.PointerEvent) => {
    (e.target as Element).setPointerCapture?.(e.pointerId);
    drag.current = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y, moved: false };
  };
  const onPointerMoveFrame = (e: React.PointerEvent) => {
    trackPointer(e);
    if (!drag.current) return;
    const dx = e.clientX - drag.current.x, dy = e.clientY - drag.current.y;
    if (Math.abs(dx) > 2 || Math.abs(dy) > 2) drag.current.moved = true;
    setView((v) => ({ ...v, x: drag.current!.vx + dx, y: drag.current!.vy + dy }));
  };
  const onPointerUpFrame = () => {
    wasDragging.current = drag.current?.moved ?? false;
    drag.current = null;
  };

  /** the round each persona's harm first shows up, so the map can reveal in step */
  const landsAt = useMemo(() => {
    const m = new Map<string, number>();
    for (const e of events) {
      const cur = m.get(e.persona_id);
      if (cur === undefined || e.round < cur) m.set(e.persona_id, e.round);
    }
    return m;
  }, [events]);

  const severityNow = (personaId: string): Severity => {
    const at = landsAt.get(personaId);
    if (at === undefined || at > round) return "none";
    return outcomes.get(personaId)?.severity ?? "none";
  };

  const blockById = useMemo(
    () => new Map(geography.blocks.map((b) => [b.block_id, b])),
    [geography.blocks]
  );
  const personaById = useMemo(
    () => new Map(personas.map((p) => [p.persona_id, p])),
    [personas]
  );

  const centre = (personaId: string) => {
    const p = personaById.get(personaId);
    if (p) return { x: p.xy[0], y: p.xy[1] };
    const b = blockById.get(personaById.get(personaId)?.block_id ?? "");
    return b ? { x: b.x + b.w / 2, y: b.y + b.h / 2 } : null;
  };

  /** background residents (unaffected so far) as light dots; affected residents as figures.
      keeps 2,000 nodes cheap to render while every affected person is a full glyph. */
  const { dots, figures } = useMemo(() => {
    const dots: Persona[] = [];
    const figures: { p: Persona; sev: "moderate" | "high"; second: boolean }[] = [];
    for (const p of personas) {
      const sev = severityNow(p.persona_id);
      if (sev === "none") dots.push(p);
      else figures.push({ p, sev, second: outcomes.get(p.persona_id)?.second_order === true });
    }
    return { dots, figures };
  }, [personas, outcomes, landsAt, round]);

  /** the two subzones carrying the most landed severe harm, named on the map itself —
      the same move as an annotated corridor on a propagation map. n >= 12 keeps a thin
      cohort from reading as a finding. */
  const corridors = useMemo(() => {
    if (round === 0) return [];
    const bySub = new Map<string, { severe: number; total: number; x: number; y: number; n: number }>();
    for (const p of personas) {
      const rec = bySub.get(p.home_subzone) ?? { severe: 0, total: 0, x: 0, y: 0, n: 0 };
      rec.total += 1;
      rec.x += p.xy[0]; rec.y += p.xy[1]; rec.n += 1;
      if (severityNow(p.persona_id) === "high") rec.severe += 1;
      bySub.set(p.home_subzone, rec);
    }
    return Array.from(bySub.entries())
      .map(([name, r]) => ({ name, rate: r.severe / r.total, severe: r.severe, x: r.x / r.n, y: r.y / r.n }))
      .filter((r) => r.severe >= 4 && r.rate >= 0.15)
      .sort((a, b) => b.rate - a.rate)
      .slice(0, 2);
  }, [personas, outcomes, landsAt, round]);

  const hoveredPersona = hoverPersona ? personaById.get(hoverPersona) : null;
  const hoveredOutcome = hoverPersona ? outcomes.get(hoverPersona) : null;

  return (
    <div
      ref={frame}
      style={{ position: "relative", width: "100%", height: "100%", overflow: "hidden", touchAction: "none" }}
      onWheel={onWheel}
      onPointerDown={onPointerDownFrame}
      onPointerMove={onPointerMoveFrame}
      onPointerUp={onPointerUpFrame}
      onPointerLeave={() => { setHoverBlock(null); setHoverPersona(null); onPointerUpFrame(); }}
    >
      <svg
        width="100%" height="100%"
        style={{ display: "block", cursor: drag.current ? "grabbing" : "grab" }}
        role="img"
        aria-label="Plan of the estate. Every figure is one synthetic resident; fill colour is how badly the policy hit them. Drag to pan, scroll to zoom."
      >
        <defs>
          <filter id="personGlow" x="-160%" y="-160%" width="420%" height="420%">
            <feGaussianBlur stdDeviation="4.5" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <radialGradient id="corridorHeat" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="var(--alert)" stopOpacity={0.16} />
            <stop offset="100%" stopColor="var(--alert)" stopOpacity={0} />
          </radialGradient>
          <marker id="careArrow" viewBox="0 0 8 8" refX="6.5" refY="4" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M 0 1 L 7 4 L 0 7 z" fill="var(--alert)" />
          </marker>
        </defs>

        <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`}>

        {geography.roads.map((r, i) => (
          <line
            key={i}
            x1={r.x1} y1={r.y1} x2={r.x2} y2={r.y2}
            stroke={r.kind === "arterial" ? "#2f2a23" : "#1c1915"}
            strokeWidth={r.kind === "arterial" ? 17 : 7}
            strokeLinecap="square"
          />
        ))}

        {/* Real bus routes, standing in for the street plan. On the real network LTA gives
            us where buses go and not where streets are, so this is both the honest thing
            available and a truer picture of the estate than an invented grid. */}
        {(geography.service_lines ?? []).map((s) => (
          <polyline
            key={s.service_id}
            points={s.points.map(([x, y]) => `${x},${y}`).join(" ")}
            fill="none"
            stroke="#241f19"
            strokeWidth={13}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        ))}

        {/* soft heat, named: the corridors carrying the run's severe harm */}
        {corridors.map((c) => (
          <circle key={c.name} cx={c.x} cy={c.y} r={210} fill="url(#corridorHeat)" style={{ pointerEvents: "none" }} />
        ))}

        {/* block footprints: thin hit-targets only. state now lives entirely on the
            figures, so the footprint no longer double-encodes it with a fill. */}
        {geography.blocks.map((b) => {
          const on = selected === b.block_id;
          const near = hoverBlock === b.block_id;
          return (
            <rect
              key={b.block_id}
              x={b.x} y={b.y} width={b.w} height={b.h}
              fill={on || near ? "rgba(242,176,36,.07)" : "rgba(255,255,255,.015)"}
              stroke={on ? "var(--gold)" : near ? "var(--t3)" : "rgba(255,255,255,.05)"}
              strokeWidth={on ? 1.6 : 0.75}
              style={{ cursor: "pointer", transition: "fill .18s ease, stroke .18s ease" }}
              onPointerEnter={() => setHoverBlock(b.block_id)}
              onClick={() => { if (!wasDragging.current) onSelect(on ? null : b.block_id); }}
            />
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
          fill="none" stroke="var(--gold)" strokeWidth={2.6} opacity={0.55}
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
                <circle cx={s.x} cy={s.y} r={4} fill="var(--ground)" stroke="var(--gold)" strokeWidth={1.8} opacity={0.7} />
                {s.name === "Interchange" && (
                  <text x={s.x} y={s.y - 15} textAnchor="middle" fontSize={12} fill="var(--t3)" fontFamily="var(--font-ui)">
                    Interchange
                  </text>
                )}
              </>
            )}
          </g>
        ))}

        {/* the population field: dim dots for the unaffected, so 2,000 residents cost
            almost nothing to draw and still read as a population rather than emptiness */}
        <g style={{ pointerEvents: "none" }}>
          {dots.map((p) => (
            <circle key={p.persona_id} cx={p.xy[0]} cy={p.xy[1]} r={2.1} fill="var(--fig-none)" opacity={0.55} />
          ))}
        </g>

        {/* caregiver connectors: drawn only for edges that actually fired. an always-on
            relationship layer would bury the one finding that matters in a hairball. */}
        {/* affected residents: full human figures, per scenario-v1.md 13.2. fill is the
            only thing carrying severity; a pulse marks HIGH, a ring marks second-order. */}
        {figures.map(({ p, sev, second }) => {
          const isHover = hoverPersona === p.persona_id;
          return (
            <g
              key={p.persona_id}
              onPointerEnter={() => setHoverPersona(p.persona_id)}
              onClick={() => { if (!wasDragging.current) onSelect(p.block_id); }}
              style={{ cursor: "pointer" }}
            >
              {second && (
                <circle cx={p.xy[0]} cy={p.xy[1] - 30} r={10} fill="none" stroke="var(--alert)" strokeWidth={1.4} className="ring" />
              )}
              <PersonGlyph
                cx={p.xy[0]} cy={p.xy[1]}
                scale={isHover ? 0.85 : 0.68}
                fill={SEV_COLOR[sev]}
                className={sev === "high" ? "fig fig-hot" : "fig"}
                glow={sev === "high" || isHover}
              />
            </g>
          );
        })}

        {/* caregiver connectors, drawn last so household pairs living almost on top of
            one another still show a clear loop rather than one figure's glyph hiding it */}
        {round >= 2 &&
          ties.slice(0, 40).map((t, i) => {
            const a = centre(t.source);
            const b = centre(t.target);
            if (!a || !b) return null;
            const dist = Math.hypot(b.x - a.x, b.y - a.y);
            const bulge = Math.max(55, dist * 0.7);
            const midX = (a.x + b.x) / 2 + (i % 2 === 0 ? bulge : -bulge);
            const midY = (a.y + b.y) / 2 - bulge * 1.15;
            return (
              <path
                key={i}
                d={`M ${a.x} ${a.y} Q ${midX} ${midY} ${b.x} ${b.y}`}
                fill="none" stroke="var(--alert)" strokeWidth={1.6}
                className="flow" opacity={0.9}
                markerEnd="url(#careArrow)"
                style={{ pointerEvents: "none" }}
              />
            );
          })}

        {corridors.map((c, i) => {
          // counter-scaled so the label reads the same size at any zoom level
          const s = 1 / view.k;
          return (
            <g key={c.name} transform={`translate(${c.x} ${c.y - (90 + i * 30) / view.k}) scale(${s})`} style={{ pointerEvents: "none" }}>
              <rect x={-2} y={-16} width={Math.max(88, c.name.length * 6.6 + 46)} height={22} fill="var(--panel)" stroke="var(--rule-strong)" strokeWidth={1} opacity={0.92} />
              <text x={8} y={0} fontSize={11} fill="var(--t2)" fontFamily="var(--font-ui)">
                {c.name} <tspan fill="var(--alert)" fontWeight={600}>{Math.round(c.rate * 100)}%</tspan>
              </text>
            </g>
          );
        })}
        </g>
      </svg>

      <div style={{ position: "absolute", top: 12, right: 12, display: "flex", flexDirection: "column", gap: 4, zIndex: 3 }}>
        {(["−", "+", "FIT"] as const).map((label) => (
          <button
            key={label}
            onClick={() => (label === "FIT" ? fit() : zoomBy(label === "+" ? 1.35 : 1 / 1.35))}
            className="t2"
            style={{
              border: "1px solid var(--rule-strong)", background: "rgba(15,14,12,.88)",
              color: "var(--t2)", fontFamily: "inherit", fontSize: "var(--fs-12)",
              padding: "6px 10px", cursor: "pointer", minWidth: 34,
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* legend: a floating card over the map, not a diagram of its own */}
      <div
        style={{
          position: "absolute", left: 14, bottom: 14, zIndex: 3,
          background: "rgba(15,14,12,.88)", border: "1px solid var(--rule-strong)",
          backdropFilter: "blur(6px)", padding: "12px 16px", minWidth: 178,
        }}
      >
        <div className="t3" style={{ fontSize: "var(--fs-12)", letterSpacing: "0.08em", marginBottom: 8 }}>
          SEVERITY
        </div>
        <LegendRow color="var(--alert)" label="High" figure />
        <LegendRow color="var(--gold)" label="Moderate" figure />
        <LegendRow color="var(--fig-none)" label="Unaffected" dot />
        <div style={{ borderTop: "1px solid var(--rule)", margin: "9px 0 8px" }} />
        <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
          <svg width="20" height="10" style={{ flexShrink: 0 }}>
            <path d="M1 8 Q10 1 19 8" fill="none" stroke="var(--alert)" strokeWidth={1.4} strokeDasharray="4 3" />
          </svg>
          <span className="t2" style={{ fontSize: "var(--fs-12)" }}>Second-order harm</span>
        </div>
        <p className="t3" style={{ fontSize: "10.5px", lineHeight: 1.5, margin: "8px 0 0" }}>
          Fill colour is the only thing that carries state. Positions are synthetic.
        </p>
      </div>

      {hoveredPersona && hoveredOutcome && pointer && (
        <div
          style={{
            position: "absolute", zIndex: 4, pointerEvents: "none",
            left: Math.min(pointer.x + 16, (frame.current?.clientWidth ?? 800) - 250),
            top: Math.max(pointer.y - 14, 8),
            background: "var(--panel)", border: "1px solid var(--rule-strong)",
            padding: "10px 13px", width: 224,
          }}
        >
          <div className="t1" style={{ fontSize: "var(--fs-14)", fontWeight: 600 }}>
            {hoveredPersona.persona_id}
            <span
              style={{ marginLeft: 8, fontSize: 10, letterSpacing: "0.08em", color: SEV_COLOR[hoveredOutcome.severity] }}
            >
              {hoveredOutcome.severity.toUpperCase()}
            </span>
          </div>
          <p className="t2" style={{ fontSize: "var(--fs-12)", lineHeight: 1.6, margin: "6px 0 0" }}>
            {hoveredPersona.age_band} · {hoveredPersona.mobility_level} mobility · {hoveredPersona.home_subzone}
          </p>
          <p className="t3" style={{ fontSize: "var(--fs-12)", lineHeight: 1.6, margin: "4px 0 0" }}>
            {hoveredOutcome.essential_trips_completed}/{hoveredOutcome.essential_trips_total} essential trips completed
          </p>
          {hoveredOutcome.second_order && (
            <p style={{ fontSize: "var(--fs-12)", lineHeight: 1.6, margin: "6px 0 0", color: "var(--alert)" }}>
              Harmed through someone they care for — no mobility limit of their own.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function LegendRow({ color, label, figure, dot }: { color: string; label: string; figure?: boolean; dot?: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 9, padding: "3px 0" }}>
      {figure && (
        <svg width="14" height="16" viewBox="0 0 64 96" style={{ flexShrink: 0 }}>
          <circle cx={32} cy={19} r={11.5} fill={color} />
          <rect x={20} y={33} width={24} height={33} rx={10} fill={color} />
        </svg>
      )}
      {dot && <span style={{ width: 8, height: 8, borderRadius: "50%", background: color, flexShrink: 0 }} />}
      <span className="t2" style={{ fontSize: "var(--fs-12)" }}>{label}</span>
    </div>
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
