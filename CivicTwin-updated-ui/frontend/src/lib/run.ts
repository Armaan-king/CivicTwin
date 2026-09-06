import { api } from "./api";
import type { SimulationRun, PersonaOutcome, SimEvent } from "@/types/simulation";

/** Kept as the single entry point the screens call. Transport is chosen in config.ts. */
export function loadRun(): Promise<SimulationRun> {
  return api.getRun();
}

/** persona_id -> outcome, built once rather than per lookup. */
export function indexOutcomes(run: SimulationRun): Map<string, PersonaOutcome> {
  return new Map(run.outcomes.map((o) => [o.persona_id, o]));
}

/**
 * Walks an event back up its cause chain to the root.
 * This is what makes a root-cause trace evidence rather than prose.
 */
export function traceToRoot(events: SimEvent[], leafId: string): SimEvent[] {
  const byId = new Map(events.map((e) => [e.event_id, e]));
  const chain: SimEvent[] = [];
  let cursor = byId.get(leafId);
  const guard = new Set<string>();
  while (cursor && !guard.has(cursor.event_id)) {
    guard.add(cursor.event_id);
    chain.push(cursor);
    cursor = cursor.cause ? byId.get(cursor.cause) : undefined;
  }
  return chain.reverse();
}

/** The finding the product exists to surface: harmed only via a dependency. */
export function secondOrderVictims(run: SimulationRun): PersonaOutcome[] {
  return run.outcomes.filter((o) => o.second_order);
}
