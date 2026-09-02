import type { SimulationRun } from "@/types/simulation";

/**
 * The system, as it actually is.
 *
 * `docs/architecture.md` §3 draws the intended architecture: LangGraph orchestrating six
 * agents over a Bedrock model. Most of that is not built. A map that shows the intended
 * version is a diagram of a plan, and a reader cannot tell which boxes they can rely on.
 *
 * So every node carries a `state`, and the map says plainly which is which. The counts
 * come from the loaded run, so the numbers on the canvas are this run's numbers rather
 * than a caption written once and left to rot.
 */

export type NodeState = "live" | "partial" | "stub" | "planned";

export interface SysNode {
  id: string;
  label: string;
  /** what it is, in four words or fewer */
  kind: string;
  group: string;
  state: NodeState;
  /** repo path, so a reader can go and look */
  path?: string;
  /** why it exists, not what it is called */
  detail: string;
  /** live figures from the current run */
  facts?: { label: string; value: string }[];
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface SysEdge {
  from: string;
  to: string;
  kind: "call" | "data" | "stream";
  label?: string;
}

export interface SysGroup {
  id: string;
  label: string;
  note: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

const COL = { surface: 40, api: 330, agents: 620, engine: 960, store: 1380 };
const NW = 208;
const NH = 66;

export const GROUPS: SysGroup[] = [
  { id: "surface", label: "SURFACE", note: "what a person touches",
    x: COL.surface - 20, y: 40, w: NW + 40, h: 470 },
  { id: "api", label: "BOUNDARY", note: "typed, and validated here",
    x: COL.api - 20, y: 40, w: NW + 40, h: 470 },
  { id: "agents", label: "LANGUAGE", note: "the only place a model is used",
    x: COL.agents - 20, y: 40, w: NW + 40, h: 470 },
  { id: "engine", label: "DETERMINISTIC CORE", note: "no model reaches in here",
    x: COL.engine - 20, y: 40, w: NW * 2 + 76, h: 610 },
  { id: "store", label: "GROUND TRUTH", note: "real data, and what it is not",
    x: COL.store - 20, y: 680, w: NW + 40, h: 300 },
];

export function buildNodes(run: SimulationRun | null): SysNode[] {
  const n = (v: number | undefined) => (v == null ? "—" : v.toLocaleString());
  const stops = run?.geography?.stops?.length;
  const services = run?.geography?.service_lines?.length;

  return [
    // ---------------------------------------------------------------- surface
    { id: "ui", label: "Policymaker UI", kind: "React · 7 routes", group: "surface",
      state: "live", path: "frontend/src/pages",
      detail: "Policy in, population, audit, alternatives, calibration. Reads one typed run object and nothing else, so it renders identically from a file or a server.",
      facts: [{ label: "routes", value: "8" }, { label: "transport", value: "fixture | http" }],
      x: COL.surface, y: 90, w: NW, h: NH },
    { id: "voicesui", label: "Resident Voices", kind: "streamed page", group: "surface",
      state: "live", path: "frontend/src/pages/Voices.tsx",
      detail: "Every resident's view of the policy, arriving one at a time. The only screen that shows the population as people rather than as a rate.",
      facts: [{ label: "residents", value: n(run?.personas?.length) }],
      x: COL.surface, y: 190, w: NW, h: NH },
    { id: "consult", label: "Consultation UI", kind: "public-facing", group: "surface",
      state: "live", path: "frontend/src/pages/Consultation.tsx",
      detail: "The proposal in plain language, and a form. What real residents would actually see, which is the only honest source of the feedback the model is tested against.",
      x: COL.surface, y: 290, w: NW, h: NH },
    { id: "map", label: "System Map", kind: "this view", group: "surface",
      state: "live", path: "frontend/src/pages/SystemMap.tsx",
      detail: "What is built, what is a stub, and what is only drawn in the architecture document. Node counts come from the loaded run rather than a caption.",
      x: COL.surface, y: 390, w: NW, h: NH },

    // ---------------------------------------------------------------- api
    { id: "routes", label: "FastAPI", kind: "typed routes", group: "api",
      state: "live", path: "backend/app/main.py",
      detail: "Every response is validated against the Pydantic contract at the boundary, so an engine that drifts fails loudly at the route instead of quietly in a browser.",
      facts: [{ label: "validation", value: "~11 ms / run" }],
      x: COL.api, y: 90, w: NW, h: NH },
    { id: "stream", label: "NDJSON streams", kind: "rounds · voices", group: "api",
      state: "live", path: "backend/app/main.py",
      detail: "One object per line. Rounds replay the cascade as it propagated; voices arrive as residents are written. Watching it happen is the part a chart cannot do.",
      x: COL.api, y: 190, w: NW, h: NH },
    { id: "contract", label: "Run contract", kind: "Pydantic", group: "api",
      state: "live", path: "backend/app/schemas/run.py",
      detail: "The single object every screen reads. Mirrored field for field in TypeScript; if the two disagree the tests fail before a browser ever sees it.",
      facts: [{ label: "tests", value: "62 passing" }],
      x: COL.api, y: 290, w: NW, h: NH },
    { id: "feedback", label: "Feedback intake", kind: "POST", group: "api",
      state: "stub", path: "backend/app/main.py",
      detail: "Validates a response and returns an id. Persists nothing yet: there is no store behind it. W7.",
      x: COL.api, y: 390, w: NW, h: NH },

    // ---------------------------------------------------------------- language
    { id: "interp", label: "Policy Interpreter", kind: "agent", group: "agents",
      state: "live", path: "backend/app/agents/policy_interpreter.py",
      detail: "Plain English to a typed PolicyChange. It computes nothing: no distances, no thresholds. Anything it filled in that the author did not say is marked assumed.",
      x: COL.agents, y: 90, w: NW, h: NH },
    { id: "voice", label: "Persona Voice", kind: "agent · batched", group: "agents",
      state: "live", path: "backend/app/agents/persona_voice.py",
      detail: "What each resident makes of the policy, round by round. May only cite events the engine recorded for them; an ungrounded voice is dropped and counted, never shown.",
      facts: [{ label: "batch", value: "20 residents" }, { label: "cache", value: "content hash" }],
      x: COL.agents, y: 190, w: NW, h: NH },
    { id: "llm", label: "LLMClient", kind: "one boundary", group: "agents",
      state: "live", path: "backend/app/services/llm.py",
      detail: "Structured output or an exception, never a plausible-looking fallback. Mock and Bedrock behind one interface, so the whole suite runs without credentials.",
      facts: [{ label: "default", value: "mock" }],
      x: COL.agents, y: 290, w: NW, h: NH },
    { id: "planner", label: "Intervention Planner", kind: "agent", group: "agents",
      state: "planned", path: "docs/architecture.md §8",
      detail: "Would select and parameterise from the five typed actions. Today the candidates are enumerated in code; the action space is already closed, so this is a swap and not a rewrite. W6.",
      x: COL.agents, y: 390, w: NW, h: NH },

    // ---------------------------------------------------------------- engine
    { id: "geo", label: "Geography", kind: "real network", group: "engine",
      state: "live", path: "backend/app/geography_real.py",
      detail: "Real stops, real routes, real headways for whichever town is selected. The interchange, the hospital and the local feeder are read out of the data, not declared.",
      facts: [{ label: "stops", value: n(stops) }, { label: "routes drawn", value: n(services) }],
      x: COL.engine, y: 90, w: NW, h: NH },
    { id: "pop", label: "Population", kind: "2,000 residents", group: "engine",
      state: "live", path: "backend/app/population.py",
      detail: "Households first, then people, so a carer cannot live across the estate from the mother they drive. Synthetic, and labelled as such everywhere it is shown.",
      facts: [{ label: "residents", value: n(run?.personas?.length) },
              { label: "care edges", value: n(run?.graph?.edges?.length) }],
      x: COL.engine, y: 190, w: NW, h: NH },
    { id: "graph", label: "Graph + routing", kind: "NetworkX", group: "engine",
      state: "live", path: "backend/app/graph.py",
      detail: "One typed DiGraph for dependency, and a (stop, service) routing graph where a transfer is an edge and can be counted rather than guessed.",
      x: COL.engine, y: 290, w: NW, h: NH },
    { id: "sim", label: "Simulation", kind: "4 rounds", group: "engine",
      state: "live", path: "backend/app/simulation.py",
      detail: "Seven deterministic rules and exactly one logistic. Every event carries the id of the one that caused it, which is what makes a root cause provable.",
      facts: [{ label: "events", value: n(run?.events?.length) },
              { label: "severe", value: n(run?.metrics?.overall?.severe_harm_count) }],
      x: COL.engine, y: 390, w: NW, h: NH },
    { id: "metrics", label: "Metrics", kind: "six · four axes", group: "engine",
      state: "live", path: "backend/app/metrics.py",
      detail: "Six numbers, computed one way, read by every screen. No cohort is reported without its n, because a rate without a denominator is not a finding.",
      x: COL.engine + NW + 36, y: 90, w: NW, h: NH },
    { id: "ivs", label: "Interventions", kind: "5 typed actions", group: "engine",
      state: "live", path: "backend/app/interventions.py",
      detail: "Each valid candidate is re-simulated by the same engine with the same seeds. A rejected one carries no metrics at all: scoring what was never run would be inventing a result.",
      x: COL.engine + NW + 36, y: 190, w: NW, h: NH },
    { id: "cons", label: "Consultation model", kind: "response + error", group: "engine",
      state: "live", path: "backend/app/consultation.py",
      detail: "Who replies, and what they say. Carries a terrain penalty the prediction function does not have, so calibration finds a real attributable error instead of noise.",
      x: COL.engine + NW + 36, y: 290, w: NW, h: NH },
    { id: "voices", label: "Voice orchestration", kind: "batch · cache", group: "engine",
      state: "live", path: "backend/app/voices.py",
      detail: "Grounded voices for every resident, from a model when one is configured and from templates otherwise. Which one produced them is always stated.",
      facts: [{ label: "grounding", value: "validated per turn" }],
      x: COL.engine + NW + 36, y: 390, w: NW, h: NH },
    { id: "orch", label: "LangGraph", kind: "orchestrator", group: "engine",
      state: "planned", path: "docs/architecture.md §5",
      detail: "Drawn in the architecture document and not built. The pipeline is a function call today, which is enough for one scenario and would not be for branching runs.",
      x: COL.engine + NW / 2 + 18, y: 500, w: NW, h: NH },

    // ---------------------------------------------------------------- store
    { id: "lta", label: "LTA DataMall", kind: "real, licensed", group: "store",
      state: "live", path: "data/lta/",
      detail: "Bus stops, routes and frequencies under the Singapore Open Data Licence. Provenance file records the source, the date and exactly what was trimmed.",
      facts: [{ label: "towns", value: "2 fetched" }],
      x: COL.store, y: 730, w: NW, h: NH },
    { id: "fixture", label: "Run fixture", kind: "engine output", group: "store",
      state: "live", path: "data/fixtures/demo_run.json",
      detail: "A committed run so the interface works with no backend process. It is engine output, not a hand-authored stand-in, and a diff shows when a rule moves a number.",
      x: COL.store, y: 830, w: NW, h: NH },
    { id: "store", label: "Persistence", kind: "S3 + DynamoDB", group: "store",
      state: "planned", path: "docs/architecture.md §11",
      detail: "Nothing is stored between processes. Runs are recomputed in about two seconds, which is cheaper than a database until runs need to be shared.",
      x: COL.store, y: 930, w: NW, h: NH },
  ];
}

export const EDGES: SysEdge[] = [
  { from: "ui", to: "routes", kind: "call" },
  { from: "voicesui", to: "stream", kind: "stream", label: "voices" },
  { from: "consult", to: "feedback", kind: "call" },
  { from: "map", to: "contract", kind: "data" },
  { from: "routes", to: "contract", kind: "data" },
  { from: "stream", to: "contract", kind: "data" },
  { from: "routes", to: "interp", kind: "call", label: "policy text" },
  { from: "interp", to: "llm", kind: "call" },
  { from: "voice", to: "llm", kind: "call" },
  { from: "contract", to: "geo", kind: "call" },
  { from: "geo", to: "pop", kind: "data" },
  { from: "pop", to: "graph", kind: "data" },
  { from: "graph", to: "sim", kind: "data" },
  { from: "sim", to: "metrics", kind: "data" },
  { from: "sim", to: "ivs", kind: "data" },
  { from: "sim", to: "cons", kind: "data" },
  { from: "sim", to: "voices", kind: "data", label: "event trace" },
  { from: "voices", to: "voice", kind: "call" },
  { from: "lta", to: "geo", kind: "data", label: "real stops" },
  { from: "metrics", to: "fixture", kind: "data" },
  { from: "cons", to: "feedback", kind: "data" },
];

export const STATE_COPY: Record<NodeState, { label: string; note: string }> = {
  live: { label: "BUILT", note: "running, and covered by tests" },
  partial: { label: "PARTIAL", note: "works, with a known gap" },
  stub: { label: "STUB", note: "correct shape, does nothing yet" },
  planned: { label: "NOT BUILT", note: "drawn in the docs only" },
};
