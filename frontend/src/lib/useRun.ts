import { useEffect, useState } from "react";
import { loadRun, indexOutcomes } from "./run";
import type { SimulationRun, PersonaOutcome } from "@/types/simulation";

export interface RunState {
  run: SimulationRun | null;
  outcomes: Map<string, PersonaOutcome>;
  error: string | null;
}

/** Loading, error and ready are all real states here, not just the happy path. */
export function useRun(): RunState {
  const [run, setRun] = useState<SimulationRun | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    loadRun()
      .then((r) => live && setRun(r))
      .catch((e: Error) => live && setError(e.message));
    return () => { live = false; };
  }, []);

  return {
    run,
    outcomes: run ? indexOutcomes(run) : new Map(),
    error,
  };
}
