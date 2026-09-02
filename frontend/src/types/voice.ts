/** Mirrors backend/app/schemas/voice.py. W10. */

export type Adaptation =
  | "unaffected"
  | "absorbing"
  | "adapting"
  | "substituting"
  | "giving_up";

export interface PersonaTurn {
  round: number;
  /** support for the policy, 0 against to 1 for */
  position: number;
  confidence: number;
  reasoning: string;
  /** what moved them since the previous round */
  changed_because: string | null;
  adaptation: Adaptation;
  /** event ids from this resident's own trace. The grounding guard. */
  cites: string[];
}

export interface PersonaVoice {
  persona_id: string;
  name: string;
  summary: string;
  turns: PersonaTurn[];
}

export interface VoiceListing {
  run_id: string;
  /** which produced these: a model, or the offline template. Shown, never hidden. */
  generated_by: string;
  total: number;
  offset: number;
  spoke: number;
  ungrounded_dropped: number;
  cached_batches: number;
  model_batches: number;
  voices: PersonaVoice[];
}
