/** Mirrors backend/app/schemas/deliberation.py. V2. */

export type Response =
  | "unaffected"
  | "absorbing"
  | "adapting"
  | "substituting"
  | "delegating"
  | "giving_up";

export type Severity = "none" | "moderate" | "high";

export interface AgentTurn {
  round: number;
  /** the resident's own judgement, not a computed predicate */
  severity: Severity;
  response: Response;
  /** support for the policy, 0 against to 1 for */
  position: number;
  confidence: number;
  reasoning: string;
  changed_because: string | null;
  /** the neighbour who moved them. What makes this a deliberation. */
  influenced_by: string | null;
  /** fact ids they were given and reasoned from. The grounding guard. */
  grounded_in: string[];
  /** a household member whose journey they have taken on */
  absorbing_for: string | null;
}

export interface AgentVoice {
  persona_id: string;
  name: string;
  summary: string;
  turns: AgentTurn[];
}

export interface VoiceListing {
  run_id: string;
  /** which model reasoned. There is no offline substitute. */
  model: string;
  total: number;
  offset: number;
  spoke: number;
  moved: number;
  /** turns rejected for citing a fact they were not given */
  rejected: number;
  calls: number;
  cached_batches: number;
  seconds: number;
  participation: Record<string, number>;
  voices: AgentVoice[];
}
