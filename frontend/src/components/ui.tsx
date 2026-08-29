import type { CSSProperties, ReactNode } from "react";

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
        background: tone === "alert" ? "rgba(239,78,54,.08)" : undefined,
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
  return (
    <div style={{ padding: 40 }}>
      <p className="alert" style={{ fontSize: "var(--fs-16)", margin: "0 0 8px" }}>{message}</p>
      <p className="t3" style={{ fontSize: "var(--fs-14)", margin: 0, lineHeight: 1.6 }}>
        Regenerate it with <code>python scripts/make_fixture.py</code>, then copy it into{" "}
        <code>frontend/public/fixtures/</code>.
      </p>
    </div>
  );
}
