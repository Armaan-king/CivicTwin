import type { VoiceListing } from "@/types/voice";
/**
 * The API surface, as defined in docs/architecture.md section 5.
 *
 * Every call goes through here. Under the fixture transport the reads resolve from the
 * committed run and the writes are refused loudly rather than faked, so a demo can never
 * silently present a stubbed write as a real one (AGENTS.md section 28).
 */
import { API_BASE, FIXTURE_PATH, TRANSPORT } from "./config";
import type {
  SimulationRun, Intervention, FeedbackResponse, PolicyChange, SimEvent,
} from "@/types/simulation";

export class ApiError extends Error {
  constructor(message: string, readonly status?: number, readonly retryable = false) {
    super(message);
    this.name = "ApiError";
  }
}

/** Writes are unavailable without a backend. Say so; never pretend it worked. */
export class NotAvailableOffline extends ApiError {
  constructor(action: string) {
    super(
      `${action} needs the backend. Start it, then run the frontend with ` +
      `VITE_TRANSPORT=http.`,
      undefined,
      false
    );
    this.name = "NotAvailableOffline";
  }
}

async function get<T>(path: string, fixtureFallback?: () => Promise<T>): Promise<T> {
  if (TRANSPORT === "fixture") {
    if (!fixtureFallback) throw new NotAvailableOffline(path);
    return fixtureFallback();
  }
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { headers: { accept: "application/json" } });
  } catch {
    throw new ApiError(`Could not reach the API at ${API_BASE}`, undefined, true);
  }
  if (!res.ok) {
    throw new ApiError(`${path} failed`, res.status, res.status >= 500);
  }
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown, action: string): Promise<T> {
  if (TRANSPORT === "fixture") throw new NotAvailableOffline(action);
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "content-type": "application/json", accept: "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiError(`Could not reach the API at ${API_BASE}`, undefined, true);
  }
  if (!res.ok) throw new ApiError(`${action} failed`, res.status, res.status >= 500);
  return res.json() as Promise<T>;
}

/* ---------------------------------------------------------------- reads */

let fixtureCache: Promise<SimulationRun> | null = null;

function fixtureRun(): Promise<SimulationRun> {
  if (!fixtureCache) {
    fixtureCache = fetch(FIXTURE_PATH).then((r) => {
      if (!r.ok) throw new ApiError(`Could not load the run fixture (${r.status})`, r.status);
      return r.json() as Promise<SimulationRun>;
    });
  }
  return fixtureCache;
}

export const api = {
  /** GET /api/runs/{id} */
  getRun(runId = "latest"): Promise<SimulationRun> {
    return get(`/api/runs/${runId}`, fixtureRun);
  },

  /** GET /api/runs/{id}/interventions */
  async getInterventions(runId = "latest"): Promise<Intervention[]> {
    return get(`/api/runs/${runId}/interventions`, async () => (await fixtureRun()).interventions);
  },

  /* -------------------------------------------------------------- writes */

  /** POST /api/runs - interpret a proposal and start a baseline run. */
  startRun(policyText: string): Promise<{ run_id: string; policy: PolicyChange }> {
    return post("/api/runs", { policy_text: policyText }, "Running a simulation");
  },

  /** POST /api/runs/{id}/interventions - generate, validate, simulate. */
  generateInterventions(runId: string): Promise<Intervention[]> {
    return post(`/api/runs/${runId}/interventions`, {}, "Generating alternatives");
  },

  /** POST /api/consultations/{id}/feedback */
  submitFeedback(
    consultationId: string,
    body: Omit<FeedbackResponse, "response_id" | "persona_id" | "is_seeded">
  ): Promise<{ response_id: string }> {
    return post(`/api/consultations/${consultationId}/feedback`, body, "Submitting feedback");
  },

  /** POST /api/runs/{id}/calibration/apply - human approval, never automatic (L3). */
  applyCalibration(runId: string, approved: boolean): Promise<{ status: string }> {
    return post(`/api/runs/${runId}/calibration/apply`, { approved }, "Recording your decision");
  },
};

/* ---------------------------------------------------------- round stream */

export type StreamFrame =
  | { type: "round_start"; round: number; active: string[] }
  | { type: "event"; round: number; persona_id: string; event: SimEvent["kind"];
      before: Record<string, unknown>; after: Record<string, unknown>; cause: string | null }
  | { type: "round_complete"; round: number; changed: string[] }
  | { type: "complete"; run_id: string };

/**
 * POST /api/runs/{id}/rounds/stream, NDJSON, one JSON object per line.
 * architecture.md section 5.1. Cancellable, and it never buffers the whole body.
 */
export async function streamRounds(
  runId: string,
  onFrame: (f: StreamFrame) => void,
  signal?: AbortSignal
): Promise<void> {
  if (TRANSPORT === "fixture") throw new NotAvailableOffline("Streaming rounds");

  const res = await fetch(`${API_BASE}/api/runs/${runId}/rounds/stream`, {
    method: "POST",
    headers: { "content-type": "application/json", accept: "application/x-ndjson" },
    body: "{}",
    signal,
  });
  if (!res.ok || !res.body) throw new ApiError("Round stream failed", res.status, true);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // a chunk boundary can land mid-line, so keep the tail for the next read
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        onFrame(JSON.parse(trimmed) as StreamFrame);
      } catch {
        // a malformed frame is a backend bug; drop it rather than killing the stream
      }
    }
  }
  if (buffer.trim()) {
    try { onFrame(JSON.parse(buffer.trim()) as StreamFrame); } catch { /* ignore */ }
  }
}


/**
 * Resident voices. W10.
 *
 * In fixture mode there is no server to generate them, so this raises the same
 * NotAvailableOffline the other write paths do rather than inventing a transcript. The
 * page shows that honestly: voices are a live-backend feature.
 */
export async function fetchVoices(runId: string, limit = 300): Promise<VoiceListing> {
  if (TRANSPORT === "fixture") {
    throw new NotAvailableOffline(
      "Residents deliberate through a model on the backend. There is no offline " +
      "substitute: start the backend and set VITE_TRANSPORT=http."
    );
  }
  const res = await fetch(`${API_BASE}/api/runs/${runId}/voices?limit=${limit}`);
  if (res.status === 503) {
    // no model configured. Say so rather than showing an empty page.
    throw new Error((await res.json()).detail ?? "No model configured for deliberation.");
  }
  if (!res.ok) throw new Error(`voices: ${res.status}`);
  return res.json();
}
