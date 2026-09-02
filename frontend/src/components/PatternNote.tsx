import type { HarmPattern, SimulationRun } from "@/types/simulation";

/**
 * The line that makes a finding travel.
 *
 * A number about bus stops in Ang Mo Kio is only interesting to someone working on bus
 * stops in Ang Mo Kio. Naming the shape underneath it, and where else that shape turns
 * up, is what turns one result into a reason to run the next policy through here.
 *
 * The descriptions come from the run, not from this file. `core.PATTERNS` is their one
 * home, so the UI can never describe a pattern the engine does not have.
 */
export function PatternNote({ run, pattern }: { run: SimulationRun; pattern: HarmPattern }) {
  const p = run.harm_patterns?.[pattern];
  if (!p) return null;

  return (
    <div style={{ borderTop: "1px solid var(--rule)", paddingTop: "var(--s-3)" }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: "var(--s-2)", flexWrap: "wrap" }}>
        <span className="t3" style={{ fontSize: "var(--fs-12)", letterSpacing: ".08em" }}>
          PATTERN
        </span>
        <span className="gold" style={{ fontSize: "var(--fs-16)", fontWeight: 600 }}>
          {p.name}
        </span>
      </div>
      <p className="t2" style={{ fontSize: "var(--fs-14)", lineHeight: 1.65, margin: "var(--s-2) 0 0", maxWidth: "62ch" }}>
        {p.mechanism}
      </p>
      <p className="t3" style={{ fontSize: "var(--fs-12)", lineHeight: 1.6, margin: "var(--s-2) 0 0", maxWidth: "62ch" }}>
        Also seen in {p.also_seen_in.join(", ")}.
      </p>
    </div>
  );
}
