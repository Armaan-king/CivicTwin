/**
 * Where the app gets its data.
 *
 * Two transports, one contract. `fixture` reads the committed run so the frontend can be
 * built and demoed with no backend at all; `http` talks to the FastAPI service. Both
 * return the same shapes, so no screen knows or cares which is live.
 *
 *   VITE_TRANSPORT=http VITE_API_BASE=http://localhost:8000 npm run dev
 */

export type Transport = "fixture" | "http";

const env = import.meta.env;

export const TRANSPORT: Transport =
  env.VITE_TRANSPORT === "http" ? "http" : "fixture";

export const API_BASE = (env.VITE_API_BASE ?? "http://localhost:8000").replace(/\/$/, "");

/** Path to the committed run used by the fixture transport. */
export const FIXTURE_PATH = "/fixtures/demo_run.json";

/** Surfaced in the UI so nobody demos cached data believing it is live. */
export function transportLabel(): string {
  return TRANSPORT === "http" ? `LIVE ${API_BASE}` : "FIXTURE";
}
