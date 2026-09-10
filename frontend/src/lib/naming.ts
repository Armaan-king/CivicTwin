import type { SimulationRun } from "@/types/simulation";

/**
 * Every place and service name the interface shows, derived from the run.
 *
 * These were literals scattered across seven files -- "Service 265", "Ang Mo Kio Ave 3",
 * "Blk 700B and Blk 324", "Ang Mo Kio" -- written when there was one study area and no
 * way to submit a different one. There is now: a policy naming Bedok stops resolves to
 * Bedok, and the engine correctly simulates Bedok geography, Bedok residents and Bedok
 * closures. The headings still said Ang Mo Kio.
 *
 * That is the worst kind of wrong. Nothing errors, every number is real, and the label
 * above them names a different town — so it reads as a result rather than as a bug. A
 * planner would have no way to tell.
 *
 * The run already carries all of it. `resolved_entities` is the interpreter's own
 * reading of the policy — which service, which stops, which interchange — so these read
 * that rather than re-deriving from ids, and a name shown on screen is the same name the
 * reading claimed.
 */

/** The one thing every fallback here has in common: say nothing rather than say a town. */
const UNKNOWN = "";

function entity(run: SimulationRun | null, kind: string): { id: string; label: string } | null {
  return run?.policy?.resolved_entities?.find((e) => e.kind === kind) ?? null;
}

/** "265". The service the policy changes. */
export function serviceId(run: SimulationRun | null): string {
  return entity(run, "service")?.id ?? UNKNOWN;
}

/** "Service 265", or just "the service" when the run does not name one. */
export function serviceLabel(run: SimulationRun | null): string {
  const id = serviceId(run);
  return id ? `Service ${id}` : "the affected service";
}

/** "Ang Mo Kio". The town, as a person writes it rather than as a directory is named. */
export function townName(run: SimulationRun | null): string {
  return run?.study_area ?? UNKNOWN;
}

/** "Ang Mo Kio Int". Where local journeys are modelled as heading. */
export function interchangeName(run: SimulationRun | null): string {
  return entity(run, "interchange")?.label ?? UNKNOWN;
}

/** The stops this policy closes, by name: ["Blk 700B", "Blk 324"]. */
export function closedStopNames(run: SimulationRun | null): string[] {
  if (!run) return [];
  const byId = new Map(run.geography.stops.map((s) => [s.stop_id, s.name]));
  return run.policy.modifications.remove_stops.map((id) => byId.get(id) ?? id);
}

/** "Blk 700B and Blk 324" — an Oxford-comma-free list, for prose. */
export function closedStopList(run: SimulationRun | null): string {
  const names = closedStopNames(run);
  if (names.length === 0) return "the affected stops";
  if (names.length === 1) return names[0];
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}

/**
 * "Ang Mo Kio Ave 3". The road the closures sit on.
 *
 * Taken from the subzone label the backend already assigns each block, which is the
 * stop's real road name from the LTA extract rather than an invented district. When the
 * closures span more than one road the first is used, because a heading has room for one
 * and the map shows the rest.
 */
export function affectedRoad(run: SimulationRun | null): string {
  if (!run) return UNKNOWN;
  const closed = new Set(run.policy.modifications.remove_stops);
  const stop = run.geography.stops.find((s) => closed.has(s.stop_id));
  if (!stop) return UNKNOWN;
  // blocks carry the road name as their subzone; find the one nearest this stop
  let best: { subzone: string; d: number } | null = null;
  for (const b of run.geography.blocks) {
    const dx = b.x + b.w / 2 - stop.x;
    const dy = b.y + b.h / 2 - stop.y;
    const d = dx * dx + dy * dy;
    if (!best || d < best.d) best = { subzone: b.subzone, d };
  }
  return best?.subzone ?? UNKNOWN;
}

/** "Ang Mo Kio · Singapore · Service 265 corridor", for the map caption. */
export function corridorCaption(run: SimulationRun | null): string {
  const id = serviceId(run);
  return id ? `Singapore · ${serviceLabel(run)} corridor` : "Singapore";
}

/** The four stage headings on the simulation page, named for this run's own policy. */
export function stageLabels(run: SimulationRun | null): string[] {
  const svc = serviceLabel(run);
  const road = affectedRoad(run);
  const n = closedStopNames(run).length;
  const where = road ? ` on ${road}` : "";
  return [
    `${svc} before the change`,
    n === 1 ? `One stop closes${where}` : `${n} stops close${where}`,
    "Residents adjust their journeys",
    "The full transport impact",
  ];
}

/** The note under each stage heading. Same derivation, longer sentences. */
export function stageNotes(run: SimulationRun | null): string[] {
  const svc = serviceLabel(run);
  const stops = closedStopList(run);
  return [
    `Both proposed stops are open. Explore today’s route before the policy takes effect.`,
    `Closures at ${stops} add walking time for nearby residents.`,
    `Families change who travels and how they reach essential services.`,
    `See who loses access, walks farther or relies on family support. ${svc} runs express through this section.`,
  ];
}

/** "Ang Mo Kio Community Hosp". The trip the policy can cut people off from. */
export function essentialDestination(run: SimulationRun | null): string {
  return entity(run, "destination")?.label ?? "the essential destination";
}

/**
 * Which cohort a rate map actually hits hardest, and by how much.
 *
 * The impact page used to assert "older residents are affected most" as fixed prose. On
 * the run it shipped with, 65-74 was the worst band at 5.2% while 75+ sat at 1.5% -- so
 * the sentence contradicted the chart printed directly beneath it. A claim about the data
 * has to be read off the data.
 */
export function worstCohort(
  rates: Record<string, { severe_harm_rate: number; n: number }>,
  minN = 30,
): { label: string; rate: number } | null {
  const eligible = Object.entries(rates).filter(([, v]) => v.n >= minN);
  if (!eligible.length) return null;
  const [label, v] = eligible.reduce((a, b) =>
    b[1].severe_harm_rate > a[1].severe_harm_rate ? b : a);
  return { label, rate: v.severe_harm_rate };
}
