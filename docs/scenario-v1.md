# CivicTwin — V1 Scenario Lock

> **Scenario:** Singapore public-bus stop rationalisation
> **Status:** Locked for implementation
> **Supersedes:** the illustrative "Route 14" material in `goal.md` and `docs/simulation.md`
>
> This document is the canonical specification for the V1 transport scenario.
> Product intent lives in [`../goal.md`](../goal.md); coding-agent behaviour in
> [`../AGENTS.md`](../AGENTS.md); system design in [`architecture.md`](./architecture.md);
> modelling rules in [`simulation.md`](./simulation.md); validation in
> [`evaluation.md`](./evaluation.md).
>
> **Precedence:** where this file and any of the above disagree on a transport-scenario
> detail, this file wins. Where it conflicts with product intent in `goal.md`, `goal.md`
> wins and this file is wrong.

Decision identifiers (`A1`, `F3`, `N2`, …) are stable and referenced from the other docs.

---

# 1. Status, scope, and rulings

## 1.1 What is locked

One public-policy scenario: **a bus operator removes two stops from a service and adds an
express segment between the retained termini**, in a Singapore mature estate. CivicTwin
simulates the effect on a synthetic resident population, audits who is harmed, explains why
through the dependency graph, generates alternatives, re-simulates them, publishes one for
consultation, and compares predicted against observed support.

## 1.2 Rulings on prior document conflicts

Four inconsistencies existed across the source documents. Each is resolved here and patched
at source.

| # | Conflict | Ruling |
|---|---|---|
| 1 | Public Confidence Score required as a capability (`goal.md` §29) but warned against as a display (`goal.md` §23, `evaluation.md` §12) | Compute and store it; never render it without components, response count, and subgroup spread on the same screen. See **K4**. |
| 2 | Three overlapping metric vocabularies (`goal.md` §20, `simulation.md` §32, `evaluation.md` §4), none marked canonical | §7 of this file (**I1**) is canonical for the transport scenario. The others are menus. |
| 3 | Every internal document link broken; flat `.md/` layout vs. referenced root + `docs/` layout | Resolved by restructure: `goal.md`, `AGENTS.md`, `README.md` at root; detailed docs in `docs/`. All links now resolve. |
| 4 | Graph ablation is both a core research question (`evaluation.md` §6, `goal.md` §44.1) and a droppable stretch goal (`evaluation.md` §29) | Promoted to required. See **N2**. |

## 1.3 Deferred out of V1

Capacity and crowding modelling (**F2**), social/peer influence (**B2**), historical
backtesting (**N3**), and cross-tabulated cohorts (**I4**). Each is recorded with its
rationale below rather than silently dropped.

**Reinstated after being deferred:** per-persona LLM reasoning, now §6A. The original
rejection was sized against the wrong call volume.

---

# 2. Scenario frame

## A1 — Policy lever · LOCKED

Remove **two stops** from one bus service and add a **non-stop express segment** between the
retained termini either side of the removed pair.

Chosen because it is the only candidate lever where the dependency graph visibly earns its
place. The first-order effect is pure geometry — walking distance rises, transfers rise —
and it cascades into second-order harm through `NEEDS` and `CARES_FOR` edges. Fare changes
barely touch the graph; frequency reductions are real but invisible on a network diagram.

Rejected: frequency reduction, fare change, route consolidation.

## A2 — Geography basis · LOCKED

**Real Singapore bus topology from open data; fully synthetic residents.**

Infrastructure — stops, services, road-distance travel times — is real and citable.
Residents are synthetic, sampled from published aggregates, and labelled synthetic wherever
they appear in the UI. No real individual's data enters the system at any point.

This split is what allows a grounded claim without fabricated provenance, per `AGENTS.md`
§16 and `goal.md` §36.

## A3 — City · LOCKED

**Singapore.** Selected for local relevance and for the quality of LTA's open transport data.

**Study area selection rule** (applied once data lands, not pre-guessed): among mature
estates, choose the town maximising residents aged 65+ that also has at least one polyclinic
and at least three bus services sharing a common corridor. Record the chosen town and the
figures behind the choice in the scenario config.

Singapore raises two scenario-relevant characteristics that shape defaults elsewhere in this
document:

- **Low private-vehicle access.** Certificate-of-Entitlement costs make car ownership
  strongly income-correlated, so `has_car_access` is a low-probability, income-conditioned
  attribute (**C1**) rather than a coin flip. This *increases* the harm from transit changes
  relative to a car-dependent city — a substantive modelling consequence, not a detail.
- **Polyclinics as the essential destination.** Subsidised polyclinics carry heavily
  elderly, heavily transit-dependent demand, which makes the clinic-access chain the natural
  spine of the harm story rather than a contrived one.

## A4 — Population size · LOCKED

**2,000 personas.** Configurable; this is the demo default.

Squeezed from both sides. Subgroup credibility needs roughly 30–50 personas in the thinnest
reported cohort; across four cohort axes (**I4**) that floor is met at 2,000 and missed at
500. Interactivity needs the full run well under a second, which NetworkX clears comfortably
at this size and does not at 10,000.

`simulation.md` §6 notes that population size is not itself a quality metric. Do not inflate
it for optics.

---

# 3. Time model

## B1 — Temporal structure · LOCKED

**One structural recomputation, then exactly three dependency-propagation rounds.** No
wall-clock time, no daily cycle.

```text
round 0   structural, deterministic, no randomness
          recompute paths, walk distances, transfers, arrival times

round 1   persona thresholds breach          → ACCESSIBILITY_THRESHOLD_EXCEEDED
round 2   dependants absorb the breach       → CAREGIVER_SUPPORT_TRIGGERED
round 3   dependants' own constraints breach → WORK_ARRIVAL_MISSED
```

Three is not arbitrary: it is the exact depth of the canonical harm chain in `goal.md` §14
(stop removed → clinic access degrades → family member drives → family member misses work).
One-pass propagation stops at the first arrow and forfeits the product's differentiator. A
fourth round produces nothing observable and invites runaway cascades.

**These are propagation depths, not days.** No claim is made that round 2 happens on
Tuesday. State this in the UI wherever rounds are exposed.

## B2 — Social influence · OUT of V1

Dependency propagation only. No peer contagion, no opinion diffusion.

`simulation.md` §13 explicitly permits omission. Influence weights would add parameters
nobody can calibrate to a mechanism this scenario does not need — whether a neighbour
switches services does not change whether a walk exceeds 800 metres. There is also a
positioning reason: `goal.md` §43 differentiates CivicTwin from PropSim-style opinion
simulation, and leaning on contagion moves toward the thing being differentiated from.

---

# 4. Persona schema

## C1 — Field set · LOCKED

Seventeen fields. **Every one is read by a named rule in §6.** Any field no rule reads is
decoration and was cut.

```text
identity      persona_id, age_band, home_subzone, household_id,
              household_role, income_band, employment_status

constraints   mobility_level, max_walk_m, transfer_tolerance,
              work_start_time, has_car_access, is_caregiver

behavioural   inconvenience_tolerance, switching_propensity, baseline_trust

state         accessibility_status, essential_trips_completed,
              journey_time_min, walk_distance_m, severity
```

Cut from the source documents' candidate lists, with reasons: `digital_literacy` (no rule
reads it in a transport scenario), `time_budget_min` (subsumed by `work_start_time` plus
arrival), `risk_tolerance` and `preference_for_familiar` (collapse into
`switching_propensity`), a general `schedule` structure (only the work-start constraint is
ever checked).

`has_car_access` is sampled conditional on `income_band`, per **A3**.

## C2 — Age representation · LOCKED

Six ordinal bands: `<18`, `18–34`, `35–54`, `55–64`, `65–74`, `75+`.

Bands match how Singapore's Department of Statistics publishes, so sampling needs no
invented within-band distribution. They are also the reporting unit for subgroups, and the
splits at 65 and 75 are where mobility and service dependency actually change. An integer
age would imply precision the source aggregates do not contain.

## C3 — Mobility representation · LOCKED

Four ordinal levels, each mapping to an explicit `max_walk_m`.

```text
none      max_walk_m = 1200
mild      max_walk_m =  800
moderate  max_walk_m =  500
severe    max_walk_m =  250   and forces transfer_tolerance = 0
```

This is the most consequential field in the scenario — it converts a geometric change into a
severity flag, so the entire impact audit rests on it. Ordinal levels with a declared metre
mapping keep the threshold inspectable and arguable, which is exactly what a citizen
challenging the model needs.

**Distribution is a declared assumption, not sampled data** (per your answer to blocking
question 2). Singapore does not publish disability or mobility-limitation rates at subzone
level. The V1 approach: apply a national-level rate by age band, declare the rates and their
source in scenario config, and list this in the limitations section (§14). Sensitivity to
this assumption is the first thing calibration should test.

Anchor to verify before locking the metre values: LTA planning guidance on walking distance
to a bus stop is commonly cited around 400 m. If confirmed, `moderate` at 500 m sits just
beyond the planned norm, which is the right place for a threshold to bite.

## C4 — Behavioural attributes · LOCKED

Exactly three, each a 0–1 scalar with a declared sampling distribution:
`inconvenience_tolerance`, `switching_propensity`, `baseline_trust`.

The first two feed the logistic in **G1**. The third feeds the simulated-support function in
**L1** and is therefore the parameter calibration actually tests.

These three are the least defensible numbers in the system. They are assumptions, not
evidence. That is acceptable for V1 — but they must appear in §14 and be the first
parameters calibration adjusts.

## C5 — Persona narratives · LOCKED

**Generated once at population build, cached into the fixture.** Labelled synthetic in
the UI.

Superseded in scope by **P1**: personas now also reason about the policy itself, not only
carry a description. The build-time cache still applies, and the constraint below is
unchanged and now matters more.

`AGENTS.md` §8 forbids an LLM call per citizen per timestep; that prohibition is about the
simulation loop. A one-off descriptive paragraph costs 2,000 cheap calls once, ships inside
the fixture, and makes the population screen land as people rather than rows — which matters
because `goal.md` §39 scores presentation.

**Hard constraint:** the narrative is derived from the structured fields and is never the
source of them. Text asserting anything the schema does not contain is a defect.

---

# 5. Graph schema

## D1 — Node types · LOCKED

Eight: `Person`, `Household`, `Stop`, `Service`, `Subzone`, `Workplace`, `School`,
`Polyclinic`.

Cut from `goal.md` §13's menu because no rule traverses them: `Neighborhood` (duplicates
`Subzone`), `Institution`, `CommunityCenter`, `PublicResource`, `TransportNode` (duplicates
`Stop`). `Route` is renamed `Service` to match Singapore usage.

## D2 — Edge types and direction · LOCKED

One `networkx.DiGraph`, typed nodes and edges, nine edge types.

```text
Person  ─LIVES_IN───→  Subzone
Person  ─MEMBER_OF──→  Household
Person  ─USES───────→  Stop         {walk_m}
Person  ─WORKS_AT───→  Workplace    {arrive_by}
Person  ─STUDIES_AT─→  School
Person  ─NEEDS─────→   Polyclinic   {trips_per_week, essential: true}
Person  ─CARES_FOR──→  Person       {criticality}   asymmetric
Service ─SERVES────→   Stop         {sequence, headway_min}
Stop    ─ROUTES_TO──→  Stop         {travel_time_min}
```

Directedness matters, and `CARES_FOR` is why: harm propagates *to* the carer, not back. An
undirected graph would run the cascade both ways and produce nonsense.

One graph rather than layered subgraphs — NetworkX handles heterogeneous typed nodes, and a
multi-layer abstraction would be architecture with no current consumer (`AGENTS.md` §2).

## D3 — Stop assignment · LOCKED

Nearest stop **on a service that reaches the destination**, within `max_walk_m`. If none
qualifies, the destination is transit-unreachable for that person.

**Assignment is recomputed after the policy applies. It is never held fixed.** This is the
mechanical heart of the scenario and the easiest thing to get quietly wrong: if a person
retains their original `USES` edge to a removed stop, no harm is ever detected and the whole
audit silently returns nothing. The removal must force a re-search, and the re-search is
what produces the longer walk.

"Unreachable" is a distinct outcome from "reachable but painful" and feeds **F3** directly.

## D4 — Conditional edges · LOCKED

Edges depend on persona attributes. The resulting sparsity is deliberate.

- `WORKS_AT` only if `employment_status = employed`
- `STUDIES_AT` only if `age_band = <18` or student
- `NEEDS → Polyclinic` weighted by age band — near-universal at 75+, sparse below 35
- `CARES_FOR` only where a household contains both a high-dependency and a low-dependency
  member

Uniform edges would flatten the population and destroy the subgroup variance the product
exists to surface. The clinic-dependency gradient by age is what makes the 65+ cohort
structurally exposed to a stop removal, which is what produces the headline finding.

---

# 6. Policy representation and simulation rules

## E1 — PolicyChange schema · BOUND

Shape fixed by `simulation.md` §9. Transport binding:

```text
modifications   remove_stops[], add_express_segment{from_stop, to_stop},
                frequency_delta_pct
constraints     fleet_increase_allowed, operating_budget_delta_pct
```

## E2 — Policy input · LOCKED

**Free text in, validated `PolicyChange` out**, with a structured form as an always-visible
fallback — not a hidden one.

This is one of the few places an LLM genuinely earns its place under `goal.md` §15.3, and it
is the demo's opening beat. But `AGENTS.md` §18 requires visible failure: if interpretation
fails schema validation, the UI falls back to the structured form and shows the parse error.
It does not retry silently and it does not guess.

## F1 — Deterministic rules · LOCKED

Seven rules, all pure functions of graph state, all unit-testable without a model call.

```text
F1.1  shortest path per (person, essential destination)   dijkstra on travel_time_min
F1.2  walk distance to assigned stop                      haversine × 1.35 detour factor
F1.3  transfer count on chosen path
F1.4  door-to-door journey = walk + wait + ride + transfer
F1.5  arrival vs work_start_time                          → WORK_ARRIVAL_MISSED
F1.6  walk_m > max_walk_m                                 → ACCESSIBILITY_THRESHOLD_EXCEEDED
F1.7  transfers > transfer_tolerance                      → enters G1 abandonment check
```

The 1.35 detour factor converts straight-line to walkable distance. It is a declared
constant, not a hidden one, and it is exactly the kind of assumption a citizen comment can
legitimately attack — which makes it useful demo material.

Per `AGENTS.md` §10, none of these may be delegated to an LLM.

## F2 — Capacity and crowding · OUT of V1

Not modelled. No `stop_capacity` parameter, no `STOP_CAPACITY_EXCEEDED` event.

It would have produced a genuinely non-obvious second-order effect — removed stops pushing
riders onto neighbours and harming people nowhere near the change — for pure arithmetic. But
it is not needed to prove the CivicTwin loop, and it adds a parameter with no empirical
anchor. **Revisit only if the core loop finishes early**; the natural re-entry point is a
1.4× baseline-boardings threshold, which needs no external ground truth.

## F3 — Severity definition · LOCKED

Severity is `HIGH` if **any** of four conditions holds.

```text
HIGH if:
    an essential destination becomes transit-unreachable
 OR walk_m > max_walk_m × 1.5
 OR an essential trip is abandoned            (from G1)
 OR a caregiver's own work arrival fails      (second-order)

MODERATE if:
    walk_m > max_walk_m  (but ≤ 1.5×)
 OR journey_time increases > 50%
```

**Lock this before anything in §7.** Every headline number resolves to this predicate —
severe-harm count, disparity, intervention ranking, and the demo's central claim. It must be
visible in the UI, not buried in configuration.

The fourth clause is deliberate and is where the graph pays off: a person with no mobility
limitation, living nowhere near a removed stop, can be classified as severely harmed because
of who they care for. That single row is the strongest available evidence that the
dependency model does real work, and it is what **N2** measures.

## G1 — Stochastic component · LOCKED

**Exactly one, in the deterministic layer.** The trip adaptation choice, via a logistic.
Everything else in that layer is deterministic.

Since **P3** this runs alongside the per-persona assessment rather than instead of it.
The logistic stays as the inspectable baseline; the two are compared in calibration.

```text
P(adapt) = σ( β0
            + β1 · Δjourney_time_norm
            + β2 · Δtransfers
            + β3 · (walk_m / max_walk_m)
            − β4 · inconvenience_tolerance
            − β5 · has_car_access )

outcome ∈ { continue_transit, switch_to_car, abandon_trip }
```

One stochastic component keeps the boundary `AGENTS.md` §8 requires genuinely crisp: you can
point at a single function and say this and only this is where randomness enters. It also
keeps seeded reproducibility trivial to test.

`simulation.md` §12 suggests a logistic may beat an LLM here. It does — this is a numeric
propensity, and a model call would be slower, costlier, unreproducible, and no more
accurate.

Note the Singapore consequence: with `has_car_access` low and income-correlated (**A3**),
the `switch_to_car` escape hatch is unavailable to exactly the residents most exposed, which
concentrates `abandon_trip` in the vulnerable cohort.

## G2 — Seed strategy · LOCKED

Hierarchical: `persona_seed = hash(scenario_seed, persona_id)`. **Never a single sequential
stream.**

This is what makes baseline-versus-alternative comparison fair. With one sequential RNG,
an intervention that changes how many personas reach the abandonment check shifts every
subsequent draw, so measured differences partly reflect reshuffled randomness rather than
policy. Per-persona derived seeds mean persona 1847 draws the same number under every
scenario, and the delta is causal.

Small implementation detail, large evaluation consequence — which is why it is locked here
rather than left to whoever writes the sampler. Satisfies `simulation.md` §23.

## G3 — Behavioural coefficients · LOCKED

**Declared assumptions for V1**, exposed in scenario config and tested against real feedback
through calibration.

Rejected for V1: fitting to consultation responses (circular — `evaluation.md` §14 warns
against using the same responses as independent validation) and a literature-derived
parameter search (better, but not worth the days).

The write-up must therefore say plainly: *these coefficients are assumptions; here is how
wrong they turned out to be.* That is a stronger and more honest story than an unverifiable
claim of realism, and it is what `evaluation.md` §28 actually asks for.

## H1 — SimulationResult · BOUND

Shape fixed by `architecture.md` §10. Reproducibility metadata from `goal.md` §34 attaches
to the same object.

## H2 — Event log · LOCKED

Material changes only. **Nine typed event kinds**, each carrying `before`, `after`, and
`cause`.

```text
ROUTE_UNAVAILABLE                 WALK_DISTANCE_INCREASED
TRANSFER_ADDED                    TRAVEL_TIME_INCREASED
ACCESSIBILITY_THRESHOLD_EXCEEDED  ESSENTIAL_ACCESS_DEGRADED
CAREGIVER_SUPPORT_TRIGGERED       WORK_ARRIVAL_MISSED
TRIP_ABANDONED
```

(`STOP_CAPACITY_EXCEEDED` is deferred with **F2**.)

`simulation.md` §16 permits skipping trivial changes. The binding constraint runs the other
way: the log must be complete enough that **every root-cause explanation is reconstructible
from it**. `evaluation.md` §9 proposes a Grounded Explanation Rate, computable only if the
chain is present. The `cause` field carries the upstream event id, which is what makes the
chain traversable.

---

# 6A. Persona deliberation

A reversal of an earlier position, recorded rather than quietly changed. The first draft of
this spec confined the LLM to policy interpretation and intervention planning and left
behaviour to the logistic in **G1**. That was sized against the wrong number: PropSim's
shape is every persona every round, 8,000 calls. Reasoning only where a persona's situation
is actually at stake costs 2,040.

The product is decision support for people who will run a scenario a handful of times and
want to understand it, not a service answering thousands of requests an hour. A two-minute
run that yields a subjective account from every resident is a better trade than a
sub-second run that yields a number.

## P1 — Every persona reasons about the policy · LOCKED

One pass over the whole population, plus re-reasoning only for personas whose state changed
in a later round.

```text
reaction pass    2,000   every resident, once
cascade pass        40   rounds 2 and 3, only those whose situation moved
total            2,040   about two minutes at 20 concurrent
cached replay        0   the demo runs from cache
```

`AGENTS.md` §8 forbids "every citizen on every timestep", which is the 8,000-call shape.
Reasoning once per resident, and again only when something happened to them, sits inside
that rule and is what `simulation.md` §14 already described.

## P2 — The model renders facts, it does not produce them · LOCKED

Every assessment is grounded in the persona's structured record and their event trace. The
prompt carries the facts; the model categorises and explains. It never invents a
circumstance, a number or a constraint.

```text
BehaviorAssessment {
    outcome_category      continue | switch_mode | abandon_trip | unaffected
    likelihood            0..1
    support               1..5, their view of the policy
    contributing_factors  which structured facts drove it
    explanation           first person, 2 to 3 sentences
}
```

Schema-validated like every other model output (`AGENTS.md` §7). An assessment citing a
fact absent from the persona's record is a defect, and §12 tests for it.

## P3 — The logistic stays, as a baseline to measure against · LOCKED

**G1** is not replaced. Both predictions are produced and compared.

The logistic is inspectable and its error attributes to a named coefficient. The reasoning
is richer and its error does not. Keeping both turns that weakness into a result:
calibration reports how far each sat from observed support, which is real evidence about
when structured reasoning beats a fitted curve and when it does not.

## P4 — Cached by content hash, so a run replays exactly · LOCKED

```text
cache_key = sha256(persona_id, policy_version, round, model_id, prompt_version)
```

A cached run is byte-identical on replay and costs nothing. A fresh run against a live model
may differ, because temperature 0 is not a determinism guarantee. That limit is stated in
§14 rather than papered over: the deterministic layer stays reproducible from a seed, the
reasoning layer is reproducible from cache.

## P5 — The deliberation is a screen, not a log · LOCKED

Assessments stream to a dedicated view as they complete, and the whole set is exportable.

A policymaker's question is "what did this do to people", and a per-person account answers
it in a way a metric cannot. The export exists because that account is evidence: it belongs
in the annex of whatever document the decision is written into. JSON for the record,
Markdown for reading.

---

# 7. Outcome metrics

## I1 — Canonical metric set · LOCKED

**This section is canonical.** Where `goal.md` §20, `simulation.md` §32, and
`evaluation.md` §4 list overlapping metric families, they are menus; this is the
implementation set.

Six metrics — one benefit, three harm, one equity, one cost — always reported at overall
**and** subgroup level together.

| Metric | Role |
|---|---|
| `avg_journey_time_delta` | The headline that improves — the policy's stated objective |
| `severe_harm_count` | Personas at `HIGH` severity per **F3** |
| `essential_trip_completion` | Share of essential trips still completed |
| `walk_distance_p90` | Tail exposure — averages hide this by construction |
| `subgroup_disparity` | Per **I3** |
| `operating_cost_index` | Relative to baseline 1.00×, per **J3** |

Built so the demo's central tension is visible in one table: metric 1 improves while
2–5 deteriorate for a specific cohort. A p90 rather than a mean on walking distance is
deliberate — it is the clearest single number showing the average moved the wrong way for
the tail.

## I2 — Utility score · LOCKED

**Components are primary. The combined utility is optional, off by default, and never shown
without its weights beside it.**

`goal.md` §19 requires explaining the trade-off rather than presenting a verdict, and §23
warns against a bare score. A single number is also the exact failure mode the product
exists to critique — collapsing distribution into an average is how policies hide harm.
Shipping it as the headline would undercut the thesis inside the demo.

## I3 — Disparity measure · LOCKED

Report two: **worst-cohort minus overall** on the primary metric, and the **max–min gap**
across cohorts.

They fail differently. Worst-minus-overall answers "how much worse is the most affected
group than the headline", which is the product's actual question. Max–min catches the case
where one group gains and another loses while the overall barely moves. A ratio was
considered and rejected — it explodes as the denominator approaches zero, which happens
routinely on harm counts.

## I4 — Reported cohorts · LOCKED

Four axes, reported independently: `age_band`, `mobility_level`, `home_subzone`,
`is_caregiver`. **No cross-tabulation in V1.**

Cross-tabs (65+ *and* mobility-constrained *and* one subzone) hold the most striking
findings, but at 2,000 personas those cells fall to single digits and stop meaning anything.
Better four honest axes than one dramatic unsupportable cell.

`is_caregiver` is on the list specifically because it is the cohort that exists as a finding
only if the graph works. It is the axis **N2** measures.

---

# 8. Intervention action space

## J1 — Action types · LOCKED

Five typed interventions with declared parameters. The planner **selects and parameterises;
it never invents a type.**

```text
retain_stop_peak    {stop_id, hours[]}             cheap, targeted, partial relief
add_shuttle_feeder  {from_subzone, to_stop, headway} costly, high coverage
reroute_feeder      {service_id, via_stop}         near-free, harms other riders
targeted_support    {cohort, subsidy_type}         bypasses the network entirely
phase_rollout       {delay_weeks, stages[]}        defers harm, does not remove it
```

Five gives the comparison table enough rows to show a real trade-off frontier without
near-duplicates. `reroute_feeder` is included specifically because it **can make things
worse for a different cohort** — the comparator needs at least one candidate that trades
harm between groups rather than reducing it, or the trade-off story is too easy and the
demo's honesty claim rings hollow.

## J2 — Generation budget · LOCKED

**Generate 5 → validate → simulate the 3 that pass and rank highest.** Hard cap, single
pass, **no regeneration loop.**

`AGENTS.md` §13 requires bounded loops. A regeneration loop ("if all candidates fail, try
again") is the obvious next step and is explicitly excluded from V1 — it is where demo
runtime and Bedrock spend become unpredictable. If fewer than two candidates validate, that
is a legitimate result to display, not an error to retry away.

Three simulated alternatives also fits the comparison table in `goal.md` §19 exactly.

## J3 — Cost model · LOCKED

A **relative index against baseline 1.00×**, from declared per-type coefficients. Never
currency.

A dollar figure for a shuttle service would be fabricated provenance — `AGENTS.md` §16
forbids inventing sourcing, and no real costing exists here. A relative index carries the
comparative information the trade-off table needs while making no claim the project cannot
support. Coefficients live in scenario config and are shown beside the comparison, labelled
illustrative.

## J4 — Residents propose remedies too · LOCKED

The planner's five typed actions stay exactly as **J1** defines them. Alongside them,
harmed residents are asked one further question during deliberation:

> What would make this workable for you?

Answers are clustered into distinct proposals, each mapped onto a typed action where one
fits, and each carrying the count of residents who asked for it. They then go through the
same validator and the same re-simulation as a planner candidate. No shortcut, no
exemption.

This is the difference between consulting people about a remedy and letting them author
one. It costs a prompt field and a clustering pass, because the deliberation in §6A is
already paid for.

**Unmappable requests are reported, not discarded.** When residents ask for something the
model cannot express as a simulable change, that is a finding in its own right:

```text
31 residents asked for something this model cannot simulate
   "somewhere to sit and wait"           14
   "a shelter over the new walk"         11
   "a different appointment time"         6
```

A model that quietly dropped those would be hiding the gap between what it can represent
and what people actually need. That gap belongs on the screen.


---

# 9. Public consultation and feedback

## K1 — Structured items · LOCKED

Five 5-point items plus one free-text field, mapping onto `goal.md` §22.

```text
support                    1–5      → the only calibration target (L1)
perceived_fairness         1–5
clarity_of_explanation     1–5
confidence_in_delivery     1–5
expected_personal_impact   −2..+2
comment                    free text, optional
```

**Only `support` is compared against a simulated prediction.** The simulation has no
principled basis for predicting perceived fairness or clarity, and pretending otherwise
would manufacture calibration error that means nothing. The other four are reported as
observed data and feed the PCS.

`expected_personal_impact` is signed because its neutral point is meaningful and must sit at
zero.

## K2 — Respondent cohort · LOCKED

Optional self-report of `age_band`, `home_subzone`, `mobility_level`. Pseudonymous id, no
account, no PII, skippable.

Without cohort, calibration collapses to one overall number — and the entire point of
`goal.md` §24 is that the overall figure can look fine while a subgroup is badly wrong.
These three are exactly the fields the simulation can predict against, and no more.

Optional means the analysis must handle missing cohort gracefully and report how many
responses lacked it, which `evaluation.md` §12 requires anyway.

## K3 — Demo responses · LOCKED

A committed seed set of **clearly labelled** demo responses, plus a live form that works
during the demo.

Calibration needs enough responses to compute subgroup error, and an audience will not
generate them in the demo window. `AGENTS.md` §22 permits deterministic fixtures for demo
reliability on the explicit condition that they are not presented dishonestly. So the UI
says "seeded demo responses" on its face, and any live submission is visibly distinguishable.

The seed set must contain at least one comment surfacing a constraint the model lacks — a
terrain or sheltered-walkway objection in the Singapore setting — because that drives the
final act of the demo and produces the `DiscoveredConstraint` in `simulation.md` §27.

## K4 — Public Confidence Score rendering · LOCKED

**Ruling on conflict 1.** PCS is computed and stored per `goal.md` §23. The UI **never**
renders the headline score without, on the same screen:

- its four component metrics,
- the response count (overall and per cohort),
- the subgroup spread,
- an explicit note that the sample is not representative.

The score is a way into the components, never a verdict. This reconciles the required
capability in `goal.md` §29 with the warnings in `goal.md` §23 and `evaluation.md` §12.

## K5 — Name who the consultation will under-hear · LOCKED

Turnout is not uniform, and it is not random. Residents who are most affected are often
least able to respond: the oldest, the least mobile, the ones already spending their spare
hours caring for someone else.

CivicTwin already models both halves. It computes severity per persona, and it weights
turnout by stake and capacity. Multiplying them gives a blind-spot score:

```text
blind_spot = severity x (1 - expected_response_rate)
```

Reported as cohorts, with counts, on the calibration screen:

```text
This consultation will under-hear an estimated 340 residents.
  75+ with severe mobility        118
  carers in full-time work         94
  low income, no car access       128
```

This is the one output a real ministry could act on the same afternoon: it names who to go
and find. It is also the honest counterweight to the Public Confidence Score, which can
only ever describe the people who did reply.

**It is an estimate about a synthetic population**, and the screen says so. It points at
cohorts to reach, never at individuals.


---

# 10. Calibration

## L1 — Simulated support function · LOCKED

An explicit, inspectable function of three persona quantities, kept as the baseline
alongside the LLM assessment from **P1**. See **P3** for why both.

```text
P(support) = σ( γ0
              + γ1 · baseline_trust
              − γ2 · personal_impact_delta
              − γ3 · severity_flag )

predicted_support(cohort) = mean over personas in cohort
```

This function is the object under test in the entire calibration story, so it must be
legible enough that its error is interpretable. If a model produced the prediction, "we
overestimated support among 65+ by 19 points" would have no actionable cause. With three
declared coefficients, the error attributes to trust, impact sensitivity, or the severity
penalty — and that attribution is the finding.

`goal.md` §20 forbids hiding weights inside prompts; the same principle applies to the
prediction, not just the objective.

## L2 — Error metrics · LOCKED

Signed error per cohort, MAE overall, and a **flag at |error| > 10 percentage points** with
the cohort's response count shown beside it.

Signed rather than absolute at cohort level, because direction is the finding — systematic
overestimation among older residents is a different and more useful statement than "off by
19". `evaluation.md` §11 asks for signed bias for this reason.

10pp is a judgement call: large enough to survive sampling noise at realistic response
counts, small enough to actually fire on demo data. It must appear beside the response count
so a flag from n=6 is not read as a finding.

## L3 — Auto-update · LOCKED

**No automatic parameter updates.** Calibration proposes a delta, records it, and waits for
explicit human approval. History is retained either way.

`goal.md` §27 lists treating calibration as authoritative among the actions requiring human
approval; `simulation.md` §28 warns against a model silently learning without recording what
changed. Auto-applying breaches both.

It is also better demo material: a proposed adjustment awaiting sign-off makes the
human-in-the-loop boundary *visible* rather than leaving it as a README claim.

---

# 11. Datasets

## M1 — Transit network · LOCKED (identifiers to verify)

Singapore bus stop, service, and route data from **LTA DataMall** (requires a free
`AccountKey`). Bus stop coordinates, service routes, and stop sequences are the required
fields.

**Take one service plus its immediate neighbours, not the whole network.** The full
Singapore bus network is thousands of stops, which slows the graph build for no demo benefit
and renders the visualisation illegible.

Exact dataset and endpoint names must be verified against current LTA DataMall documentation
before implementation — do not assume field names from this document.

## M2 — Demographics · LOCKED (identifiers to verify)

Resident population by planning area / subzone and age band, from the **Department of
Statistics Singapore**; subzone boundaries from **data.gov.sg** (URA Master Plan).

Mobility and disability rates are **not available at subzone level**, per your answer to
blocking question 2. V1 therefore applies a declared national rate by age band (**C3**),
records it in scenario config with its source, and lists it in §14. This is a documented
assumption, not a silent one.

Polyclinic locations are public and can be geocoded from the operators' published lists.

## M3 — Fixture strategy · LOCKED

**Vendor a trimmed, processed fixture into `data/fixtures/`** with a provenance file. Keep
the download and processing script, but the demo never runs it.

`AGENTS.md` §22 makes demo reliability a first-class engineering requirement and calls for
avoiding unnecessary external dependencies on the critical path. A live API fetch on stage —
with an API key, over conference wifi — is an unnecessary external dependency with a known
failure mode.

The provenance file records source URL, retrieval date, licence, and the trimming applied,
satisfying `goal.md` §36 without committing a large raw feed.

---

# 12. Validation strategy

## N1 — Minimum evaluation set · BOUND

`evaluation.md` §28 fixes eight required results (seven original plus the ablation promoted
by **N2**). Each must be bound to a concrete transport artefact — named cohort, named
metric, named run id — in the results file.

## N2 — Graph ablation · REQUIRED (promoted)

**Ruling on conflict 4.** Run identical configuration with `CARES_FOR` propagation disabled
and count what disappears.

`evaluation.md` previously filed this under stretch (§29) while §6 and `goal.md` §44.1 treat
"does the graph add value" as a core research question. It is promoted to required: one
configuration flag, one extra run, and it is the **only direct evidence for the project's
main originality claim**.

Expected headline: N caregiver-cohort severe-harm cases detected with the graph, zero
without. That comparison is the argument that this is not a dashboard with a network picture
on it.

## N3 — Historical backtest · OUT of V1

Excluded, and stated explicitly in §14.

Backtesting needs a documented historical stop removal *and* measured post-change outcomes
at subgroup level. That pairing is rare, and searching for it is unbounded work with a low
hit rate. `evaluation.md` §14 also warns against tuning on an outcome then presenting it as
independent validation — an easy trap under time pressure.

Stating the exclusion openly is stronger than a weak attempt; `evaluation.md` §27 makes
acknowledged limits a credibility asset.

---

# 13. Demo flow

## O1 — Live versus precomputed · LOCKED

| Step | Mode |
|---|---|
| Policy interpretation | Live LLM · cached fallback on failure, labelled if it fires |
| Baseline + alternative simulations | **Always live** — sub-second, no reason to fake it |
| Impact audit + root cause | Live — deterministic traversal of the event log |
| Intervention generation | Live LLM · cached fallback on failure, labelled if it fires |
| Persona deliberation | Cached by default; a live pass can be run before the demo |
| Consultation responses | Seeded fixture, labelled · live form open |
| Calibration | Live — arithmetic over the above |

The simulation running genuinely live is what makes the whole thing credible, and at 2,000
personas it costs nothing to keep it that way. Only the two model calls carry real failure
risk, and each gets a fallback that **announces itself** rather than pretending — the
condition `AGENTS.md` §22 attaches to fixture use.

## O2 — Demo narrative · LOCKED

Seven beats, following `goal.md` §30 and `evaluation.md` §25:

The single claim the demo makes is **harm prevented before rollout**, which is the
north-star metric in `goal.md` §50. Every beat below is evidence for it, and the closing
number is the one to remember.

```text
1  planner proposes removing two stops, in plain language
2  synthetic population and graph load; headline journey time improves
3  impact audit flags severe harm concentrated in 65+ / mobility-constrained
4  root cause traces the chain through the graph to polyclinic access
5  planner sees the caregiver cohort — harmed with no mobility limitation at all
6  three alternatives generated, validated, re-simulated, compared
7  consultation feedback reveals a constraint the model lacked;
   calibration shows support was overestimated for one cohort
8  the close: 103 residents would have been harmed. None of them had
   been asked. The strongest alternative prevents 79 of them, and it
   was proposed by residents rather than by the planner.
```

Beat 8 is the claim. Beats 1 to 7 exist to make it credible.

Beat 5 is the one to protect if anything gets cut — it is what **N2** measures and what
distinguishes the product.

**Submission constraint (background):** hackathon materials specify a maximum five-minute
solution video. Not driving scope decisions at this stage; recorded so the narrative above
can be timed against it later. The application stays live-capable regardless.

## 13.2 - Population rendering · LOCKED

Personas are drawn as **human figures, not abstract nodes**. Pattern adapted from Cortexia
(see `architecture.md` section 22.3): seven SVG primitives on a `0 0 64 96` viewBox - shadow
ellipse, head circle, rounded-rect torso, two arms, two legs.

**Fill colour carries severity, and nothing else carries state.**

```text
severity NONE      neutral   (cool grey, the ground state)
severity MODERATE  amber
severity HIGH      deep rose
```

Proportions, shadow, and stroke stay constant across all figures. This restraint is why a
population of 2,000 reads as a population rather than as noise - the eye picks up the colour
distribution before it picks up any individual.

**The caregiver connector.** CivicTwin needs one visual state Cortexia does not have: the
persona harmed *second-order*, via **F3**'s fourth clause. When a `CARES_FOR` edge actually
fires during propagation, draw a connector from the carer to the person they care for.

The figures then show harm **distribution**; the connectors show **why**. A `HIGH`-severity
figure with a connector running to a distant `HIGH`-severity figure is demo beat 5 of
section 13 made visible rather than narrated - a person with no mobility limitation, living
nowhere near a removed stop, harmed through someone else's dependency.

Connectors are drawn only for edges that fired. An always-on relationship layer would bury
the finding in a hairball.

**No basemap.** The bus corridor is drawn as SVG directly from GTFS stop coordinates. Mapbox
and deck.gl are not used: they need an API token and put a tile fetch on the demo critical
path, which `AGENTS.md` section 22 rules out. The route geometry is the map.

---

# 14. Open items and declared limitations

## 14.1 Still to verify before implementation

- Exact LTA DataMall dataset and field names (**M1**)
- Exact SingStat table identifiers for subzone × age band (**M2**)
- The study area, once the selection rule in **A3** is applied to real figures
- Whether LTA's cited walking-distance planning norm supports the **C3** metre mapping

## 14.2 Declared assumptions — must appear in the submission's limitations section

1. **Mobility rates are assumed, not sampled.** Singapore publishes no subzone-level
   disability data; a national rate by age band is applied (**C3**, **M2**).
2. **Behavioural coefficients are declared, not fitted** (**G3**). Calibration measures how
   wrong they were; it does not make them right.
3. **The simulated-support function is a hypothesis** (**L1**), not a validated model of
   Singaporean public opinion.
4. **Consultation responses are not representative.** Sample size and composition are shown
   beside every aggregate (**K4**).
5. **Synthetic residents are not real people.** Labelled as such throughout, per `goal.md`
   §12 and `AGENTS.md` §16.
6. **No historical validation was performed** (**N3**). No claim of predictive accuracy is
   made anywhere in the submission.
7. **The 1.35 walking detour factor is a constant, not a measurement** (**F1.2**).
8. **Persona reasoning replays from cache, not from scratch** (**P4**). The deterministic
   layer reproduces exactly on a seed; a fresh model pass may differ.
9. **A synthetic resident's stated view is not a real person's view** (**P2**). It is the
   model's account of a hypothesis, and the calibration screen exists precisely because
   that account can be wrong.

## 14.3 Deferred, with re-entry points

| Item | Decision | Re-entry condition |
|---|---|---|
| Stop capacity / crowding | **F2** | Core loop complete early; use 1.4× baseline boardings |
| Social / peer influence | **B2** | Only if a scenario needs opinion diffusion |
| Cross-tabulated cohorts | **I4** | Population above ~10,000 |
| Historical backtest | **N3** | A documented removal with subgroup outcome data surfaces |
| Intervention regeneration loop | **J2** | Never in V1 — unbounded runtime and spend |
