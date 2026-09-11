import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Crt } from "@/components/Crt";
import { TopBar } from "@/components/TopBar";
import { useRun } from "@/lib/useRun";
import { api, type OrchGraph, type OrchResult } from "@/lib/api";
import {
  EDGES,
  GROUPS,
  STATE_COPY,
  buildNodes,
  pipelineEdges,
  pipelineGroups,
  pipelineNodes,
  type NodeState,
  type SysNode,
} from "@/lib/systemGraph";

/**
 * The system, as a canvas rather than a diagram.
 *
 * Two views over one canvas. ARCHITECTURE is what is built and what feeds what;
 * PIPELINE is what runs, in what order, and where a model gets a say. They are separate
 * because they are different questions, and a diagram answering both answers neither.
 * The pipeline comes from the server rather than from this file, so it cannot describe a
 * stage that does not run.
 *
 * A block diagram tells you the parts. What a reader actually wants to know is which parts
 * are real, what feeds what, and where the model is allowed to touch anything. So the map
 * is built around three questions it can answer at a glance: hover traces the path,
 * selection opens the file, and colour says built or not built and nothing else.
 *
 * Hand-rolled SVG rather than a graph library. The layout is authored, not solved, which is
 * the point: a force-directed version of twenty-four known nodes is less legible and adds a
 * dependency to arrive there.
 */

const CORE_HEIGHT = 650;
const MIN_SCALE = 0.35;
const MAX_SCALE = 2.2;

const EDGE_COLOR: Record<string, string> = {
  call: "var(--rule-strong)",
  data: "var(--rule)",
  stream: "var(--gold)",
};

function stateInk(state: NodeState): string {
  if (state === "live") return "var(--success)";
  if (state === "planned") return "var(--fig-quiet)";
  if (state === "stub" || state === "partial") return "var(--warning)";
  return "var(--t2)";
}

/** Orthogonal connector: out the right edge, along a channel, into the left edge. */
function connector(a: SysNode, b: SysNode): string {
  const x1 = a.x + a.w;
  const y1 = a.y + a.h / 2;
  const x2 = b.x;
  const y2 = b.y + b.h / 2;

  if (x2 >= x1) {
    const mid = x1 + Math.max(18, (x2 - x1) / 2);
    return `M ${x1} ${y1} H ${mid} V ${y2} H ${x2}`;
  }
  // a backward edge drops below both nodes rather than cutting through them
  const below = Math.max(a.y + a.h, b.y + b.h) + 26;
  return `M ${x1} ${y1} H ${x1 + 20} V ${below} H ${x2 - 20} V ${y2} H ${x2}`;
}

type View = "architecture" | "pipeline";

export function SystemMap() {
  const { run } = useRun();
  const [view_, setView_] = useState<View>("architecture");
  const [graph, setGraph] = useState<OrchGraph | null>(null);
  const [graphError, setGraphError] = useState<string | null>(null);
  const [result, setResult] = useState<OrchResult | null>(null);
  const [running, setRunning] = useState(false);

  // fetched once, on the first switch to the pipeline view: the architecture map does
  // not need it, and in fixture mode there is no server to ask
  useEffect(() => {
    if (view_ !== "pipeline" || graph || graphError) return;
    api.getOrchestrator().then(setGraph).catch((e: Error) => setGraphError(e.message));
  }, [view_, graph, graphError]);

  const runGraph = async () => {
    setRunning(true);
    try {
      setResult(await api.runOrchestrator());
    } catch (e) {
      setGraphError((e as Error).message);
    } finally {
      setRunning(false);
    }
  };

  // `wants` is the tab, `pipeline` is whether it can be drawn. Keeping them apart matters:
  // while the graph is loading, or when there is no server to ask, the canvas must be
  // empty rather than quietly still showing the architecture map under a message about
  // a different view.
  const wants = view_ === "pipeline";
  const pipeline = wants && graph != null;
  const ran = useMemo(
    () => (result ? new Map(result.nodes.map((n) => [n.name, n])) : null),
    [result]
  );
  const nodes = useMemo(
    () => (wants ? (graph ? pipelineNodes(graph, ran ?? undefined) : []) : buildNodes(run ?? null)),
    [wants, graph, ran, run]
  );
  const edges = useMemo(
    () => (wants ? (graph ? pipelineEdges(graph) : []) : EDGES),
    [wants, graph]
  );
  const groups = useMemo(
    () => (wants ? (graph ? pipelineGroups(graph) : []) : GROUPS),
    [wants, graph]
  );
  const byId = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);

  const [selected, setSelected] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [view, setView] = useState({ x: 0, y: 0, k: 1 });
  const frame = useRef<HTMLDivElement>(null);
  const drag = useRef<{ x: number; y: number; vx: number; vy: number } | null>(null);

  // the drawn extent, taken from the groups rather than from a constant -- the two views
  // are different sizes and a hardcoded world would frame one of them wrongly
  const world = useMemo(() => ({
    w: Math.max(0, ...groups.map((g) => g.x + g.w)) + 40,
    h: Math.max(0, ...groups.map((g) => g.y + g.h)) + 40,
  }), [groups]);

  const fit = useCallback((h: number) => {
    const el = frame.current;
    if (!el) return;
    const { width, height } = el.getBoundingClientRect();
    const k = Math.min(width / (world.w + 80), height / (h + 80), MAX_SCALE);
    setView({ k, x: (width - world.w * k) / 2, y: (height - h * k) / 2 - (h < world.h ? 34 * k : 0) });
  }, [world]);

  // in the pipeline view everything is core, so both buttons frame the same thing
  const fitCore = useCallback(() => fit(pipeline ? world.h : CORE_HEIGHT), [fit, pipeline, world.h]);
  const fitAll = useCallback(() => fit(world.h), [fit, world.h]);

  useEffect(() => {
    fitCore();
    const observer = new ResizeObserver(fitCore);
    if (frame.current) observer.observe(frame.current);
    return () => observer.disconnect();
  }, [fitCore]);

  const zoomBy = (factor: number) => {
    const el = frame.current;
    if (!el) return;
    const { width, height } = el.getBoundingClientRect();
    setView((v) => {
      const k = Math.min(MAX_SCALE, Math.max(MIN_SCALE, v.k * factor));
      const cx = width / 2;
      const cy = height / 2;
      return { k, x: cx - ((cx - v.x) / v.k) * k, y: cy - ((cy - v.y) / v.k) * k };
    });
  };

  const onWheel = (e: React.WheelEvent) => {
    const el = frame.current;
    if (!el) return;
    const box = el.getBoundingClientRect();
    const px = e.clientX - box.left;
    const py = e.clientY - box.top;
    setView((v) => {
      const k = Math.min(MAX_SCALE, Math.max(MIN_SCALE, v.k * (e.deltaY < 0 ? 1.08 : 0.926)));
      return { k, x: px - ((px - v.x) / v.k) * k, y: py - ((py - v.y) / v.k) * k };
    });
  };

  const onPointerDown = (e: React.PointerEvent) => {
    if ((e.target as Element).closest("[data-system-node]")) return;
    try {
      e.currentTarget.setPointerCapture(e.pointerId);
    } catch {
      return;
    }
    drag.current = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y };
  };
  const onPointerMove = (e: React.PointerEvent) => {
    const activeDrag = drag.current;
    if (!activeDrag) return;
    const clientX = e.clientX;
    const clientY = e.clientY;
    setView((v) => ({
      ...v,
      x: activeDrag.vx + (clientX - activeDrag.x),
      y: activeDrag.vy + (clientY - activeDrag.y),
    }));
  };
  const onPointerUp = () => {
    drag.current = null;
  };

  const focus = hovered ?? selected;
  const lit = useMemo(() => {
    if (!focus) return null;
    const ids = new Set<string>([focus]);
    for (const e of edges) {
      if (e.from === focus) ids.add(e.to);
      if (e.to === focus) ids.add(e.from);
    }
    return ids;
  }, [focus, edges]);

  const detail = selected ? byId.get(selected) : null;
  const feeds = selected ? edges.filter((e) => e.from === selected) : [];
  const fedBy = selected ? edges.filter((e) => e.to === selected) : [];

  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const n of nodes) c[n.state] = (c[n.state] ?? 0) + 1;
    return c;
  }, [nodes]);

  return (
    <Crt>
      <TopBar meta="SYSTEM" />

      <div className="system-header">
        <div style={{ display: "flex", alignItems: "baseline", gap: "var(--s-3)", flexWrap: "wrap" }}>
          <h1 className="t1" style={{ fontSize: "var(--fs-28)", fontWeight: 500, margin: 0, letterSpacing: "-0.01em" }}>
            {wants ? "Execution graph" : "System architecture"}
          </h1>
          <span className="t3" style={{ fontSize: "var(--fs-14)" }}>
            {wants
              ? graph
                ? `${graph.nodes.length} stages · ${graph.model_backed} call a model · ` +
                  `${graph.deterministic} deterministic`
                : ""
              : `${counts.live ?? 0} built · ${counts.stub ?? 0} stub · ${counts.planned ?? 0} not built`}
          </span>
          <div style={{ display: "flex", gap: 6, marginLeft: "auto" }}>
            {(["architecture", "pipeline"] as View[]).map((v) => (
              <button
                key={v}
                onClick={() => { setView_(v); setSelected(null); }}
                aria-pressed={view_ === v}
                className={view_ === v ? "t1" : "t3"}
                style={{
                  border: "1px solid " + (view_ === v ? "var(--gold)" : "var(--rule-strong)"),
                  background: "var(--ground)", cursor: "pointer", fontFamily: "inherit",
                  fontSize: "var(--fs-12)", letterSpacing: ".1em", padding: "7px 14px",
                  borderRadius: 4, color: view_ === v ? "var(--t1)" : "var(--t3)",
                }}
              >
                {v.toUpperCase()}
              </button>
            ))}
            {pipeline && (
              <button
                onClick={runGraph}
                disabled={running}
                className="t2"
                style={{
                  border: "1px solid var(--rule-strong)", background: "var(--ground)",
                  cursor: running ? "wait" : "pointer", fontFamily: "inherit",
                  fontSize: "var(--fs-12)", letterSpacing: ".1em", padding: "7px 14px",
                  borderRadius: 4, color: "var(--t2)", opacity: running ? 0.6 : 1,
                }}
              >
                {running ? "RUNNING…" : result ? "RUN AGAIN" : "RUN IT"}
              </button>
            )}
          </div>
        </div>
        <p className="t2" style={{ fontSize: "var(--fs-16)", lineHeight: 1.65, margin: "var(--s-2) 0 0", maxWidth: "78ch" }}>
          {wants
            ? result
              ? `Every stage, as it actually ran — ${result.total_ms.toLocaleString()} ms, ` +
                `${result.model_calls} model ${result.model_calls === 1 ? "call" : "calls"}. ` +
                (result.model_calls === 0
                  ? "Two stages are model-backed and neither had to ask: the residents were " +
                    "reasoned once and recorded, and a stage reporting 0 ms came from the " +
                    "content-hash cache. "
                  : "A stage reporting 0 ms was served from the content-hash cache. ") +
                "Select one to see what it produced."
              : "The order a run executes in. Run it to replace the diagram with measured timings."
            : "Select a component to see what it does. Drag to pan and scroll to zoom."}
        </p>
      </div>

      <div className="system-workspace">
        <div
          ref={frame}
          onWheel={onWheel}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          onPointerLeave={onPointerUp}
          style={{
            position: "relative",
            border: "1px solid var(--rule)",
            background: "var(--panel)",
            overflow: "hidden",
            cursor: drag.current ? "grabbing" : "grab",
            touchAction: "none",
            minHeight: 460,
          }}
        >
          <svg width="100%" height="100%" style={{ display: "block" }}>
            <defs>
              <pattern id="sysgrid" width="28" height="28" patternUnits="userSpaceOnUse">
                <path d="M 28 0 L 0 0 0 28" fill="none" stroke="var(--rule-faint)" strokeWidth={1} />
              </pattern>
              <marker id="sysarrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
                <path d="M 0 1 L 7 4 L 0 7 z" fill="var(--rule-strong)" />
              </marker>
              <marker id="sysarrowlit" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
                <path d="M 0 1 L 7 4 L 0 7 z" fill="var(--gold)" />
              </marker>
            </defs>

            <rect width="100%" height="100%" fill="url(#sysgrid)" opacity={0.55} />

            <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`}>
              {groups.map((g) => (
                <g key={g.id}>
                  <rect x={g.x} y={g.y} width={g.w} height={g.h}
                        fill="var(--ground)" fillOpacity={0.55}
                        stroke="var(--rule-dim)" strokeWidth={1} />
                  <text x={g.x + 12} y={g.y + 20} className="t3"
                        style={{ fontSize: 11, letterSpacing: "0.14em", fill: "var(--t3)" }}>
                    {g.label}
                  </text>
                  <text x={g.x + 12} y={g.y + 36} className="t3"
                        style={{ fontSize: 11, fill: "var(--fig-quiet)" }}>
                    {g.note}
                  </text>
                </g>
              ))}

              {edges.map((e, i) => {
                const a = byId.get(e.from);
                const b = byId.get(e.to);
                if (!a || !b) return null;
                const on = lit ? lit.has(e.from) && lit.has(e.to) : false;
                const dim = lit != null && !on;
                return (
                  <path
                    key={i}
                    d={connector(a, b)}
                    fill="none"
                    stroke={on ? "var(--gold)" : EDGE_COLOR[e.kind]}
                    strokeWidth={on ? 1.6 : 1}
                    strokeDasharray={e.kind === "stream" ? "5 4" : undefined}
                    opacity={dim ? 0.18 : 1}
                    markerEnd={on ? "url(#sysarrowlit)" : "url(#sysarrow)"}
                    style={{ transition: "opacity .16s ease, stroke .16s ease" }}
                  />
                );
              })}

              {nodes.map((nd) => {
                const isSel = nd.id === selected;
                const on = lit ? lit.has(nd.id) : false;
                const dim = lit != null && !on;
                const ink = nd.ink ?? stateInk(nd.state);
                return (
                  <g
                    key={nd.id}
                    data-system-node
                    role="button"
                    tabIndex={0}
                    aria-label={nd.label + ", " + STATE_COPY[nd.state].label}
                    transform={`translate(${nd.x} ${nd.y})`}
                    onMouseEnter={() => setHovered(nd.id)}
                    onMouseLeave={() => setHovered(null)}
                    onClick={(ev) => {
                      ev.stopPropagation();
                      setSelected(isSel ? null : nd.id);
                    }}
                    onKeyDown={(ev) => {
                      if (ev.key === "Enter" || ev.key === " ") {
                        ev.preventDefault();
                        setSelected(isSel ? null : nd.id);
                      }
                    }}
                    style={{ cursor: "pointer", opacity: dim ? 0.3 : 1, transition: "opacity .16s ease" }}
                  >
                    <rect width={nd.w} height={nd.h} fill="var(--ground)"
                          stroke={isSel ? "var(--gold)" : on ? "var(--rule-strong)" : "var(--rule)"}
                          strokeWidth={isSel ? 1.5 : 1} />
                    {/* one hairline of state, left edge. no fills, no glow. */}
                    <rect width={2} height={nd.h} fill={ink}
                          opacity={nd.state === "planned" ? 0.7 : 1} />
                    <text x={14} y={25} style={{ fontSize: 14, fill: "var(--t1)", fontWeight: 500 }}>
                      {nd.label}
                    </text>
                    <text x={14} y={43} style={{ fontSize: 11, fill: "var(--t3)" }}>
                      {nd.kind}
                    </text>
                    {nd.state === "live" && nd.facts?.[0] && (
                      <text x={14} y={58} style={{ fontSize: 11, fill: "var(--t2)" }}>
                        {nd.facts[0].value}{" "}
                        <tspan style={{ fill: "var(--fig-quiet)" }}>{nd.facts[0].label}</tspan>
                      </text>
                    )}
                    {nd.state !== "live" && (
                      <text x={14} y={59}
                            style={{ fontSize: 10, letterSpacing: "0.1em", fill: ink }}>
                        {STATE_COPY[nd.state].label}
                      </text>
                    )}
                  </g>
                );
              })}
            </g>
          </svg>

          {wants && !graph && (
            <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", padding: "var(--s-4)" }}>
              <p className="t3" style={{ fontSize: "var(--fs-14)", maxWidth: "52ch", textAlign: "center", lineHeight: 1.7 }}>
                {graphError ?? "Reading the graph from the server…"}
              </p>
            </div>
          )}

          <div style={{ position: "absolute", left: 12, bottom: 12, display: "flex", gap: 6 }}>
            {[["−", () => zoomBy(1 / 1.25)], ["+", () => zoomBy(1.25)], ["CORE", fitCore], ["ALL", fitAll]].map(
              ([label, fn]) => (
                <button
                  key={label as string}
                  onClick={fn as () => void}
                  className="t2"
                  style={{
                    border: "1px solid var(--rule-strong)", background: "var(--ground)",
                    color: "var(--t2)", fontFamily: "inherit", fontSize: "var(--fs-12)",
                    padding: "6px 11px", borderRadius: 4, cursor: "pointer", minWidth: 34,
                  }}
                >
                  {label as string}
                </button>
              )
            )}
          </div>

          <div style={{ position: "absolute", right: 12, bottom: 12, display: "flex", gap: "var(--s-2)" }}>
            {(pipeline
              ? [["var(--gold)", "CALLS A MODEL"], ["var(--rule-strong)", "DETERMINISTIC"]]
              : (["live", "stub", "planned"] as NodeState[]).map(
                  (s) => [stateInk(s), STATE_COPY[s].label] as const
                )
            ).map(([ink, label]) => (
              <span key={label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ width: 2, height: 12, background: ink, display: "inline-block" }} />
                <span className="t3" style={{ fontSize: "var(--fs-12)" }}>{label}</span>
              </span>
            ))}
          </div>
        </div>

        {detail && (
          <aside className="system-detail">
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "var(--s-2)" }}>
              <h2 className="t1" style={{ fontSize: "var(--fs-20)", fontWeight: 500, margin: 0 }}>
                {detail.label}
              </h2>
              <button
                onClick={() => setSelected(null)}
                className="t3"
                style={{ background: "none", border: "none", color: "var(--t3)", cursor: "pointer", fontFamily: "inherit", fontSize: "var(--fs-14)", padding: 0 }}
              >
                close
              </button>
            </div>
            <p className="t3" style={{ fontSize: "var(--fs-12)", margin: "4px 0 0", letterSpacing: "0.08em" }}>
              {detail.kind.toUpperCase()}
            </p>

            {(!pipeline || detail.state !== "live") && (
              <p style={{ fontSize: "var(--fs-12)", letterSpacing: "0.1em", margin: "var(--s-3) 0 0", color: stateInk(detail.state) }}>
                {STATE_COPY[detail.state].label}
                <span className="t3" style={{ letterSpacing: 0, marginLeft: 8 }}>
                  {STATE_COPY[detail.state].note}
                </span>
              </p>
            )}

            <p className="t2" style={{ fontSize: "var(--fs-14)", lineHeight: 1.7, margin: "var(--s-3) 0 0" }}>
              {detail.detail}
            </p>

            {detail.path && (
              <p className="t3" style={{ fontSize: "var(--fs-12)", margin: "var(--s-3) 0 0", wordBreak: "break-all" }}>
                {detail.path}
              </p>
            )}

            {detail.facts && detail.facts.length > 0 && (
              <div style={{ marginTop: "var(--s-3)", borderTop: "1px solid var(--rule)", paddingTop: "var(--s-2)" }}>
                {detail.facts.map((f) => (
                  <div key={f.label} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0" }}>
                    <span className="t3" style={{ fontSize: "var(--fs-14)" }}>{f.label}</span>
                    <span className="t1" style={{ fontSize: "var(--fs-14)" }}>{f.value}</span>
                  </div>
                ))}
              </div>
            )}

            {(fedBy.length > 0 || feeds.length > 0) && (
              <div style={{ marginTop: "var(--s-3)", borderTop: "1px solid var(--rule)", paddingTop: "var(--s-2)" }}>
                {fedBy.length > 0 && (
                  <>
                    <p className="t3" style={{ fontSize: "var(--fs-12)", letterSpacing: "0.08em", margin: 0 }}>READS FROM</p>
                    {fedBy.map((e) => (
                      <button key={e.from} onClick={() => setSelected(e.from)} className="t2"
                        style={{ display: "block", background: "none", border: "none", color: "var(--t2)", cursor: "pointer", fontFamily: "inherit", fontSize: "var(--fs-14)", padding: "4px 0", textAlign: "left" }}>
                        {byId.get(e.from)?.label}
                        {e.label && <span className="t3"> · {e.label}</span>}
                      </button>
                    ))}
                  </>
                )}
                {feeds.length > 0 && (
                  <>
                    <p className="t3" style={{ fontSize: "var(--fs-12)", letterSpacing: "0.08em", margin: "var(--s-2) 0 0" }}>FEEDS</p>
                    {feeds.map((e) => (
                      <button key={e.to} onClick={() => setSelected(e.to)} className="t2"
                        style={{ display: "block", background: "none", border: "none", color: "var(--t2)", cursor: "pointer", fontFamily: "inherit", fontSize: "var(--fs-14)", padding: "4px 0", textAlign: "left" }}>
                        {byId.get(e.to)?.label}
                        {e.label && <span className="t3"> · {e.label}</span>}
                      </button>
                    ))}
                  </>
                )}
              </div>
            )}
          </aside>
        )}
      </div>
    </Crt>
  );
}
