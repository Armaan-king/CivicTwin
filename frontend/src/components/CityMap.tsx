import { useEffect, useMemo, useRef, useState } from "react";
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
  removedStopIds?: string[];
}

interface MapView {
  x: number;
  y: number;
  w: number;
  h: number;
}

export function CityMap({
  geography, personas, outcomes, events, round, selected, onSelect, ties = [],
  removedStopIds = [],
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
  const removedStops = useMemo(() => new Set(removedStopIds), [removedStopIds]);
  const visibleStops = useMemo(
    () => geography.stops.filter((stop) =>
      removedStops.has(stop.stop_id) ||
      geography.route.some(([x, y]) => Math.hypot(stop.x - x, stop.y - y) < 42)
    ),
    [geography.route, geography.stops, removedStops]
  );
  const focusBounds = useMemo(() => {
    const points = [...geography.route, [geography.polyclinic.x, geography.polyclinic.y] as [number, number]];
    const xs = points.map(([x]) => x);
    const ys = points.map(([, y]) => y);
    const pad = 90;
    const minX = Math.max(0, Math.min(...xs) - pad);
    const minY = Math.max(0, Math.min(...ys) - pad);
    const maxX = Math.min(spanX, Math.max(...xs) + pad);
    const maxY = Math.min(spanY, Math.max(...ys) + pad);
    return { x: minX, y: minY, w: maxX - minX, h: maxY - minY };
  }, [geography.polyclinic.x, geography.polyclinic.y, geography.route, spanX, spanY]);

  const closureBounds = useMemo(() => {
    const stops = geography.stops.filter((stop) => removedStops.has(stop.stop_id));
    if (!stops.length) return focusBounds;
    const xs = stops.map((stop) => stop.x);
    const ys = stops.map((stop) => stop.y);
    const centreX = (Math.min(...xs) + Math.max(...xs)) / 2;
    const centreY = (Math.min(...ys) + Math.max(...ys)) / 2;
    const w = Math.min(spanX, Math.max(1050, Math.max(...xs) - Math.min(...xs) + 760));
    const h = Math.min(spanY, Math.max(650, Math.max(...ys) - Math.min(...ys) + 520));
    return {
      x: Math.max(0, Math.min(spanX - w, centreX - w / 2)),
      y: Math.max(0, Math.min(spanY - h, centreY - h / 2)),
      w,
      h,
    };
  }, [focusBounds, geography.stops, removedStops, spanX, spanY]);

  const [view, setView] = useState<MapView>(focusBounds);
  const [dragging, setDragging] = useState(false);
  const drag = useRef<{ id: number; x: number; y: number; view: MapView } | null>(null);
  const moved = useRef(false);

  useEffect(() => setView(focusBounds), [focusBounds]);

  const clampView = (next: MapView): MapView => ({
    ...next,
    x: Math.max(0, Math.min(spanX - next.w, next.x)),
    y: Math.max(0, Math.min(spanY - next.h, next.y)),
  });

  const zoomBy = (factor: number, anchorX = 0.5, anchorY = 0.5) => {
    setView((current) => {
      const minScale = 0.24;
      const maxScale = Math.min(spanX / focusBounds.w, spanY / focusBounds.h);
      const scale = Math.max(minScale, Math.min(maxScale, (current.w / focusBounds.w) * factor));
      const w = focusBounds.w * scale;
      const h = focusBounds.h * scale;
      return clampView({
        x: current.x + (current.w - w) * anchorX,
        y: current.y + (current.h - h) * anchorY,
        w,
        h,
      });
    });
  };

  const centre = (personaId: string) => {
    const b = blockById.get(personaById.get(personaId)?.block_id ?? "");
    return b ? { x: b.x + b.w / 2, y: b.y + b.h / 2 } : null;
  };

  return (
    <div className={"city-map" + (dragging ? " is-dragging" : "")}>
      <svg
        viewBox={`${view.x} ${view.y} ${view.w} ${view.h}`}
        preserveAspectRatio="xMidYMid meet"
        tabIndex={0}
        onPointerDown={(event) => {
          if (event.button !== 0) return;
          moved.current = false;
          drag.current = { id: event.pointerId, x: event.clientX, y: event.clientY, view };
          event.currentTarget.setPointerCapture(event.pointerId);
          setDragging(true);
        }}
        onPointerMove={(event) => {
          const active = drag.current;
          if (!active || active.id !== event.pointerId) return;
          const dx = event.clientX - active.x;
          const dy = event.clientY - active.y;
          if (Math.abs(dx) + Math.abs(dy) > 4) moved.current = true;
          const rect = event.currentTarget.getBoundingClientRect();
          setView(clampView({
            ...active.view,
            x: active.view.x - (dx / rect.width) * active.view.w,
            y: active.view.y - (dy / rect.height) * active.view.h,
          }));
        }}
        onPointerUp={(event) => {
          if (drag.current?.id === event.pointerId) {
            drag.current = null;
            event.currentTarget.releasePointerCapture(event.pointerId);
            setDragging(false);
          }
        }}
        onPointerCancel={() => {
          drag.current = null;
          setDragging(false);
        }}
        onPointerLeave={() => setHover(null)}
        onClickCapture={(event) => {
          if (!moved.current) return;
          event.stopPropagation();
          moved.current = false;
        }}
        onWheel={(event) => {
          event.preventDefault();
          const rect = event.currentTarget.getBoundingClientRect();
          zoomBy(
            event.deltaY > 0 ? 1.18 : 0.84,
            (event.clientX - rect.left) / rect.width,
            (event.clientY - rect.top) / rect.height,
          );
        }}
        onKeyDown={(event) => {
          if (event.key === "+" || event.key === "=") {
            event.preventDefault();
            zoomBy(0.8);
          } else if (event.key === "-") {
            event.preventDefault();
            zoomBy(1.25);
          } else if (event.key === "0") {
            event.preventDefault();
            setView(focusBounds);
          } else if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) {
            event.preventDefault();
            setView((current) => clampView({
              ...current,
              x: current.x + (event.key === "ArrowLeft" ? -current.w * 0.08 : event.key === "ArrowRight" ? current.w * 0.08 : 0),
              y: current.y + (event.key === "ArrowUp" ? -current.h * 0.08 : event.key === "ArrowDown" ? current.h * 0.08 : 0),
            }));
          }
        }}
        role="application"
        aria-label="Interactive map of the Service 265 corridor in Ang Mo Kio. Drag to move, scroll or use the controls to zoom, and select a block for resident details."
      >
      {geography.roads.map((r, i) => (
        <line
          key={i}
          x1={r.x1} y1={r.y1} x2={r.x2} y2={r.y2}
          stroke={r.kind === "arterial" ? "var(--map-road)" : "var(--map-road-quiet)"}
          strokeWidth={r.kind === "arterial" ? 24 : 10}
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
          stroke="var(--map-route)"
          strokeWidth={17}
          strokeLinejoin="round"
          strokeLinecap="round"
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
              fill={hot ? "color-mix(in srgb, var(--danger) 22%, var(--map-block))" : mid ? "var(--map-mid)" : "var(--map-block)"}
              stroke={on ? "var(--gold)" : hot ? "var(--alert)" : near ? "var(--t3)" : mid ? "var(--map-mid-stroke)" : "var(--map-block-stroke)"}
              strokeWidth={on ? 4 : hot ? 2.6 : 1.5}
              style={{ transition: "fill .45s ease, stroke .18s ease" }}
            />
            {hot && (
              <g style={{ pointerEvents: "none" }}>
                <circle
                  cx={b.x + b.w / 2}
                  cy={b.y + b.h / 2}
                  r={17}
                  fill="var(--alert)"
                  stroke="var(--panel)"
                  strokeWidth={3}
                />
                <text
                  x={b.x + b.w / 2}
                  y={b.y + b.h / 2 + 5}
                  textAnchor="middle"
                  fontSize={14}
                  fontWeight={700}
                  fill="#fff"
                  fontFamily="var(--font-ui)"
                >
                  {rec!.severe}
                </text>
              </g>
            )}
          </g>
        );
      })}

      <g style={{ pointerEvents: "none" }}>
        <rect
          x={geography.polyclinic.x - 21} y={geography.polyclinic.y - 21}
          width={42} height={42} rx={4} fill="var(--panel)" stroke="var(--t2)" strokeWidth={3}
        />
        <path
          d={`M ${geography.polyclinic.x} ${geography.polyclinic.y - 12} v 24 M ${geography.polyclinic.x - 12} ${geography.polyclinic.y} h 24`}
          stroke="var(--t2)" strokeWidth={3.6}
        />
        <text
          x={geography.polyclinic.x} y={geography.polyclinic.y + 48}
          textAnchor="middle" fontSize={17} fontWeight={650} fill="var(--t2)" fontFamily="var(--font-ui)"
        >
          Polyclinic
        </text>
      </g>

      <polyline
        points={geography.route.map(([x, y]) => `${x},${y}`).join(" ")}
        fill="none" stroke="var(--gold)" strokeWidth={5}
        style={{ pointerEvents: "none" }}
      />

      {visibleStops.map((s) => {
        const removed = s.removed || removedStops.has(s.stop_id);
        return (
        <g key={s.stop_id} style={{ pointerEvents: "none" }}>
          {removed && round >= 1 ? (
            <>
              <circle cx={s.x} cy={s.y} r={23} fill="var(--panel)" stroke="var(--alert)" strokeWidth={4} />
              <path d={`M ${s.x - 11} ${s.y - 11} l 22 22 M ${s.x + 11} ${s.y - 11} l -22 22`} stroke="var(--alert)" strokeWidth={4} />
              <text x={s.x} y={s.y - 36} textAnchor="middle" fontSize={19} fill="var(--alert)" fontWeight={700} fontFamily="var(--font-ui)">
                STOP CLOSED
              </text>
            </>
          ) : (
            <>
              <circle cx={s.x} cy={s.y} r={7} fill="var(--ground)" stroke="var(--gold)" strokeWidth={2.8} />
              {s.name === "Interchange" && (
                <text x={s.x} y={s.y - 20} textAnchor="middle" fontSize={15} fill="var(--t3)" fontWeight={600} fontFamily="var(--font-ui)">
                  Interchange
                </text>
              )}
            </>
          )}
        </g>
        );
      })}

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

      <div className="city-map__tools" role="group" aria-label="Map controls">
        <button type="button" onClick={() => zoomBy(1.25)} aria-label="Zoom out" title="Zoom out">−</button>
        <button type="button" onClick={() => zoomBy(0.8)} aria-label="Zoom in" title="Zoom in">+</button>
        <button type="button" className="city-map__text-button" onClick={() => setView(closureBounds)}>Focus closures</button>
        <button type="button" className="city-map__text-button" onClick={() => setView(focusBounds)}>Full route</button>
      </div>
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
