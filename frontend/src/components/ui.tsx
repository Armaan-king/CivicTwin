import type { CSSProperties, ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { stepKicker } from "@/lib/workflow";

/** Shared primitives so no screen reinvents a rule, a heading, or a bar. */

export function Heading({ children, style }: { children: ReactNode; style?: CSSProperties }) {
  return (
    <h2
      className="t1"
      style={{
        fontSize: "var(--fs-20)", fontWeight: 600, letterSpacing: ".09em",
        margin: 0, ...style,
      }}
    >
      {children}
    </h2>
  );
}

export function Prose({ children, style }: { children: ReactNode; style?: CSSProperties }) {
  return (
    <p className="t2" style={{ fontSize: "var(--fs-14)", lineHeight: 1.6, margin: 0, maxWidth: "72ch", ...style }}>
      {children}
    </p>
  );
}

export function Note({ children, tone = "quiet" }: { children: ReactNode; tone?: "quiet" | "alert" }) {
  return (
    <div
      className={tone === "alert" ? "box-alert" : "box"}
      style={{
        padding: "14px 16px",
        background: tone === "alert" ? "rgba(180,35,24,.06)" : undefined,
      }}
    >
      {children}
    </div>
  );
}

/**
 * A cohort bar. Always renders its n, because a rate without a denominator
 * is not a finding. evaluation.md section 12.
 */
export function CohortBar({
  label, rate, n, max, alert = false, thin = false,
}: { label: string; rate: number; n: number; max: number; alert?: boolean; thin?: boolean }) {
  const pct = max > 0 ? Math.min(100, (rate / max) * 100) : 0;
  const tooFew = n < 30;
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5, alignItems: "baseline" }}>
        <span className="t2" style={{ fontSize: "var(--fs-14)" }}>{label}</span>
        <span className={alert ? "alert" : "t2"} style={{ fontSize: "var(--fs-14)" }}>
          {(rate * 100).toFixed(1)}%{" "}
          <span className="t3">n {n.toLocaleString()}</span>
          {tooFew && <span className="t3"> · too few</span>}
        </span>
      </div>
      <div style={{ height: thin ? 5 : 7, border: "1px solid var(--rule-strong)" }}>
        <div
          style={{
            height: "100%", width: "100%",
            transformOrigin: "left",
            transform: `scaleX(${(pct / 100).toFixed(4)})`,
            background: alert ? "var(--alert)" : "var(--fig-quiet)",
            transition: "transform .6s cubic-bezier(.16,1,.3,1)",
          }}
        />
      </div>
    </div>
  );
}

export function Stat({ label, value, tone }: { label: string; value: string; tone?: "gold" | "alert" }) {
  return (
    <div>
      <div className={tone ?? "t1"} style={{ fontSize: "var(--fs-28)", fontWeight: 500, lineHeight: 1.1 }}>
        {value}
      </div>
      <div className="t3" style={{ fontSize: "var(--fs-12)", marginTop: 3 }}>{label}</div>
    </div>
  );
}

export function Loading({ what }: { what: string }) {
  return (
    <p className="t3" style={{ padding: 24, fontSize: "var(--fs-14)" }}>
      Loading {what}<span className="caret">_</span>
    </p>
  );
}

export function Failed({ message }: { message: string }) {
  // The advice here used to be "regenerate it with python scripts/make_fixture.py", which
  // was deleted from this repository some time ago. Pointing someone at a script that does
  // not exist is worse than saying nothing, so this now names the two things that are
  // actually true when a screen cannot load: the API it wanted, and how to check it.
  return (
    <div style={{ padding: 40 }}>
      <p className="alert" style={{ fontSize: "var(--fs-16)", margin: "0 0 8px" }}>{message}</p>
      <p className="t3" style={{ fontSize: "var(--fs-14)", margin: 0, lineHeight: 1.6 }}>
        This screen reads from the CivicTwin API. Check it is running with{" "}
        <code>uvicorn app.main:app --port 8000</code> from <code>backend/</code>, then reload.
      </p>
    </div>
  );
}

/**
 * "Step 3 · Impact", and the reason it is a component rather than a line of JSX.
 *
 * Every page used to write `{stepKicker(useLocation().pathname)}` inline. A hook inside
 * JSX still runs during render, so that is legal right up until the component returns
 * early -- and all seven of these do, for loading and for error. React then sees
 * eighteen hooks on the first render and nineteen on the second and warns that the order
 * changed, which it had, on every page on the demo path.
 *
 * Calling the hook inside a component of its own makes it unconditional again, because
 * this function has one return and no branch above it. One fix, eight call sites, instead
 * of hoisting a `const` into seven page bodies and waiting for the eighth page to forget.
 */
export function PageKicker() {
  const { pathname } = useLocation();
  return <span className="page-kicker">{stepKicker(pathname)}</span>;
}
