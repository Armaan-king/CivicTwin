/**
 * The contract. Mirrors HANDOFF.md section 3 exactly.
 *
 * The fixture at data/fixtures/demo_run.json is the source of truth until the API
 * exists. Neither side adds a field without changing the handoff first.
 */

export type Severity = "none" | "moderate" | "high";
export type AgeBand = "<18" | "18-34" | "35-54" | "55-64" | "65-74" | "75+";
export type Mobility = "none" | "mild" | "moderate" | "severe";
export type IncomeBand = "low" | "mid" | "high";
export type Employment = "employed" | "unemployed" | "retired" | "student";
export type AccessibilityStatus = "ok" | "degraded" | "unreachable";

/** Nine kinds, no more. scenario-v1.md H2. */
export type EventKind =
  | "PATH_UNAVAILABLE"
  | "EFFORT_INCREASED"
  | "FRICTION_ADDED"
  | "DURATION_INCREASED"
  | "THRESHOLD_EXCEEDED"
  | "ESSENTIAL_ACCESS_LOST"
  | "DEPENDENCY_ABSORBED"
  | "OBLIGATION_MISSED"
  | "SERVICE_ABANDONED";

export type EdgeKind =
  | "LIVES_IN" | "MEMBER_OF" | "USES" | "WORKS_AT"
  | "STUDIES_AT" | "NEEDS" | "CARES_FOR" | "SERVES" | "ROUTES_TO";

export interface Persona {
  persona_id: string;
  age_band: AgeBand;
  home_subzone: string;
  household_id: string;
  household_role: string;
  income_band: IncomeBand;
  employment_status: Employment;

  mobility_level: Mobility;
  max_walk_m: number;
  transfer_tolerance: number;
  work_start_time: string | null;
  has_car_access: boolean;
  is_caregiver: boolean;

  inconvenience_tolerance: number;
  switching_propensity: number;
  baseline_trust: number;

  needs_clinic: boolean;
  /** which city block they live in. see Geography. */
  block_id: string;
  /** normalised 0..1, kept for scatter views */
  xy: [number, number];
}

export interface PersonaOutcome {
  persona_id: string;
  severity: Severity;
  walk_distance_m: number;
  journey_time_min: number;
  essential_trips_completed: number;
  essential_trips_total: number;
  accessibility_status: AccessibilityStatus;
  /** harmed through a CARES_FOR edge rather than directly. F3 clause 4. */
  second_order: boolean;
  /** harmed by an alternative in a place the baseline never touched */
  newly_exposed?: boolean;
}

export interface SimEvent {
  event_id: string;
  round: 0 | 1 | 2 | 3;
  persona_id: string;
  kind: EventKind;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
  /** upstream event_id. this is what makes the chain traversable. */
  cause: string | null;
}

export interface GraphEdge {
  source: string;
  target: string;
  kind: EdgeKind;
  attrs?: Record<string, unknown>;
}

/** Six metrics, canonical. scenario-v1.md I1. */
export interface Metrics {
  n: number;
  avg_journey_time_delta: number;
  severe_harm_count: number;
  severe_harm_rate: number;
  essential_trip_completion: number | null;
  walk_distance_p90: number;
}

/** Four axes, reported independently. No cross-tabs in V1. I4. */
export interface SubgroupMetrics {
  age_band: Record<string, Metrics>;
  mobility_level: Record<string, Metrics>;
  home_subzone: Record<string, Metrics>;
  is_caregiver: Record<string, Metrics>;
}

export interface PolicyChange {
  text: string;
  objective: string;
  modifications: {
    remove_stops: string[];
    add_express_segment: { from_stop: string; to_stop: string };
    frequency_delta_pct: number;
  };
  constraints: {
    fleet_increase_allowed: boolean;
    operating_budget_delta_pct: number;
  };
  reading: PolicyReadingStep[];
  resolved_entities: ResolvedEntity[];
}

/**
 * Four shapes of harm that recur across policy areas. Naming the shape is what lets a
 * finding here be recognised by someone working on clinics, benefits or catchments.
 * Mirrors backend/app/schemas/core.py; the descriptions ship with the run so this file
 * never has to restate them.
 */
export type HarmPattern =
  | "threshold_cliff"
  | "dependency_cascade"
  | "capacity_displacement"
  | "participation_gap";

export interface PatternDescription {
  pattern: HarmPattern;
  name: string;
  mechanism: string;
  /** other policy areas where the same shape appears, so the finding travels */
  also_seen_in: string[];
}

export interface SimulationRun {
  run_id: string;
  scenario_id: string;
  /** which environment pack produced this run. transport is the only one V1 registers. */
  environment: string;
  seed: number;
  population_version: string;
  policy_version: string;
  rounds: number;
  generated_by: string;
  /** always true in V1. surfaced in the UI, never hidden. */
  is_synthetic: boolean;
  policy: PolicyChange;
  personas: Persona[];
  graph: { edges: GraphEdge[] };
  geography: Geography;
  outcomes: PersonaOutcome[];
  events: SimEvent[];
  study_area: string;
  metrics: {
    overall: Metrics;
    subgroup: SubgroupMetrics;
    subgroup_disparity_pp: number;
    operating_cost_index: number;
  };
  interventions: Intervention[];
  consultation: Consultation;
  /** shipped with the run so the UI never restates a description the engine owns. */
  harm_patterns: Record<HarmPattern, PatternDescription>;
}

/* ---------- policy reading, interventions, consultation ---------- */

export interface PolicyReadingStep {
  n: string;
  claim: string;
  why: string;
  /** true where the interpreter filled a gap you did not specify */
  assumed: boolean;
}

export interface ResolvedEntity { label: string; ref: string; }

export type InterventionKind =
  | "retain_stop_peak" | "add_shuttle_feeder" | "reroute_feeder"
  | "targeted_support" | "phase_rollout";

export interface Intervention {
  intervention_id: string;
  kind: InterventionKind;
  name: string;
  params: Record<string, unknown>;
  rationale: string;
  valid: boolean;
  validation_errors: string[];
  estimated_cost_index: number;
  /** null when the validator rejected it: never simulated, so never scored */
  metrics: Metrics | null;
  carers_harmed?: number;
  newly_harmed_elsewhere?: number;
  subgroup_disparity_pp?: number;
}

export interface FeedbackResponse {
  response_id: string;
  persona_id: string;
  support: 1 | 2 | 3 | 4 | 5;
  perceived_fairness: number;
  clarity_of_explanation: number;
  confidence_in_delivery: number;
  expected_personal_impact: -2 | -1 | 0 | 1 | 2;
  comment: string | null;
  cohort: { age_band?: AgeBand; home_subzone?: string; mobility_level?: Mobility };
  /** seeded for the demo. surfaced in the UI, never passed off as live. */
  is_seeded: boolean;
}

export interface CalibrationRow {
  cohort_axis: string;
  cohort_value: string;
  predicted_support: number;
  observed_support: number;
  signed_error: number;
  n: number;
  /** |error| > 10pp AND n >= 30. both conditions, always. */
  flagged: boolean;
}

/** K5, W12: harm the consultation is least likely to hear about. */
export interface BlindSpot {
  cohort_axis: string;
  cohort_value: string;
  harmed: number;
  expected_responses: number;
  /** harmed minus expected responses: how much of it goes unheard */
  score: number;
}

export interface Consultation {
  responses: FeedbackResponse[];
  response_count: number;
  is_representative: boolean;
  pcs: {
    score: number;
    components: Record<string, number>;
  };
  calibration: CalibrationRow[];
  blind_spots: BlindSpot[];
  discovered_constraint: {
    type: string; location: string; affects: string[]; source: string; note: string;
  };
  proposed_adjustment: {
    parameter: string; from: number; to: number; status: string;
  };
}

/* ---------- geography: the estate both visuals render ---------- */

export interface CityBlock {
  block_id: string;
  subzone: string;
  x: number;
  y: number;
  w: number;
  h: number;
  /** floors, so the 3D view has real height variation */
  storeys: number;
  population: number;
}

export interface Road {
  x1: number; y1: number; x2: number; y2: number;
  kind: "minor" | "arterial";
}

export interface Stop {
  stop_id: string;
  x: number;
  y: number;
  removed: boolean;
  name: string;
}

/** A real bus route, as a polyline through real stop positions. */
export interface ServiceLine {
  service_id: string;
  points: [number, number][];
}

export interface Geography {
  span: [number, number];
  blocks: CityBlock[];
  /** empty on the real network: LTA publishes where buses go, not where streets are */
  roads: Road[];
  /** the busiest routes, drawn in place of a street plan */
  service_lines: ServiceLine[];
  stops: Stop[];
  route: [number, number][];
  polyclinic: { x: number; y: number };
}
