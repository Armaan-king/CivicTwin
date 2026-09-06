/**
 * The policy workflow, in one place.
 *
 * The step numbers used to live twice: once in the top bar's progress rail and once as a
 * hardcoded string on each page ("Step 6 · Learn"). Inserting Voices into the flow moved
 * everything after it and the two halves disagreed immediately -- the rail said 7 while
 * the page said 6. Derived from this array, they cannot.
 */
export const STEPS = [
  { to: "/policy", label: "Policy" },
  { to: "/simulation", label: "Simulate" },
  { to: "/impact", label: "Impact" },
  // Who was harmed, then why. The deliberation answers "why", so it belongs between the
  // finding and the remedy rather than as a utility link in the corner.
  { to: "/voices", label: "Voices" },
  { to: "/interventions", label: "Options" },
  { to: "/consultation", label: "Consult" },
  { to: "/calibration", label: "Learn" },
] as const;

/** "Step 4 · Voices", for the kicker above a page title. */
export function stepKicker(path: string): string {
  const index = STEPS.findIndex((step) => path.startsWith(step.to));
  if (index < 0) return "";
  return `Step ${index + 1} · ${STEPS[index].label}`;
}
