import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Boundary } from "@/components/Boundary";
import { Crt } from "@/components/Crt";
import { ThemeToggle, useTheme } from "@/components/ThemeToggle";
import { useRun } from "@/lib/useRun";
import "@/styles/landing.css";

const TransportHeroScene = lazy(() =>
  import("@/components/TransportHeroScene").then((module) => ({ default: module.TransportHeroScene })),
);

function Wordmark() {
  return (
    <Link to="/" className="hero-wordmark" aria-label="CivicTwin home">
      <svg viewBox="0 0 42 28" aria-hidden="true">
        <path d="M3 7h22c7 0 7 14 14 14" />
        <path d="M3 21h22c7 0 7-14 14-14" />
        <circle cx="3" cy="7" r="2.4" />
        <circle cx="3" cy="21" r="2.4" />
        <circle cx="39" cy="7" r="2.4" />
        <circle cx="39" cy="21" r="2.4" />
      </svg>
      <span>CivicTwin</span>
    </Link>
  );
}

type HeroPhase = "idle" | "revealing" | "ready" | "loading";

export function Hero() {
  const { run, error } = useRun();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const [phase, setPhase] = useState<HeroPhase>("idle");
  const loadingTimer = useRef<number | null>(null);
  const revealTimer = useRef<number | null>(null);

  useEffect(() => () => {
    if (loadingTimer.current) window.clearTimeout(loadingTimer.current);
  }, []);

  useEffect(() => {
    if (phase !== "revealing") return;
    // The scene normally signals completion itself. This timeout keeps the
    // primary journey usable if WebGL is unavailable and the fallback renders.
    revealTimer.current = window.setTimeout(
      () => setPhase((current) => current === "revealing" ? "ready" : current),
      3200,
    );
    return () => {
      if (revealTimer.current) window.clearTimeout(revealTimer.current);
    };
  }, [phase]);

  const advanceStage = () => {
    if (phase === "idle") {
      setPhase("revealing");
    } else if (phase === "ready") {
      setPhase("loading");
      loadingTimer.current = window.setTimeout(() => navigate("/simulation"), 1100);
    }
  };
  const isBusy = phase === "revealing" || phase === "loading";
  const buttonCopy = phase === "idle"
    ? "Reveal resident impact"
    : phase === "revealing"
      ? "Revealing impact"
      : phase === "loading"
        ? "Loading full simulation"
        : "Show full simulation";
  const bodyCopy = phase === "idle"
    ? "Start with Service 265 as it runs today."
    : phase === "revealing"
      ? "Tracing how two stop closures change daily journeys."
      : "See which journeys become harder—and why.";

  return (
    <Crt ambient={false}>
      <div className="hero-page">
        <header className="hero-header">
          <Wordmark />
          <ThemeToggle theme={theme} onToggle={toggleTheme} />
        </header>

        <main className="hero-main">
          <section className="hero-visual" aria-label="Ang Mo Kio transport digital twin">
            <div className="hero-visual__wash" />
            {run && (
              <Boundary label="The transport digital twin" fallback={<div className="hero-scene-fallback" />}>
                <Suspense fallback={<div className="hero-scene-fallback" />}>
                  <TransportHeroScene
                    run={run}
                    stage={phase === "idle" ? 0 : 2}
                    theme={theme}
                    onRevealComplete={() => setPhase((current) => current === "revealing" ? "ready" : current)}
                  />
                </Suspense>
              </Boundary>
            )}
            {error && <div className="hero-error" role="alert">Simulation data unavailable.</div>}
            {run && phase !== "idle" && <HeroInsights run={run} />}
          </section>

          <section className="hero-copy" aria-labelledby="hero-title">
            <div className="hero-copy__body">
              <div className="hero-eyebrow">
                <span>Transport policy simulator</span>
              </div>
              <h1 id="hero-title">
                Test the impact.
                <em>Improve the plan.</em>
              </h1>
              <p className="hero-stage-copy" aria-live="polite">{bodyCopy}</p>
              <div className="hero-actions">
                <button
                  type="button"
                  className="hero-primary"
                  onClick={advanceStage}
                  disabled={isBusy}
                  aria-busy={isBusy}
                >
                  {isBusy && <span className="hero-spinner" aria-hidden="true" />}
                  {buttonCopy}
                  {!isBusy && <span aria-hidden="true">→</span>}
                </button>
                <Link className="hero-secondary" to="/policy">Amend policy</Link>
              </div>
            </div>
          </section>
        </main>
      </div>
    </Crt>
  );
}

function HeroInsights({ run }: { run: NonNullable<ReturnType<typeof useRun>["run"]> }) {
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);
  const severe = run.metrics.overall.severe_harm_count;
  const indirect = run.outcomes.filter((outcome) => outcome.second_order).length;
  const cards = [
    {
      label: "Policy applied",
      value: run.policy.modifications.remove_stops.length + " stops close",
      body: "Service 265 runs express towards Ang Mo Kio interchange.",
    },
    {
      label: "Impact found",
      value: severe + " residents at risk",
      body: "Their essential journey is no longer reachable within their limits.",
    },
    {
      label: "Household effect",
      value: indirect + " carers affected",
      body: "They take over another person’s trip and miss their own obligation.",
    },
  ];

  useEffect(() => {
    if (paused) return;
    const timer = window.setInterval(() => setActive((index) => (index + 1) % cards.length), 5400);
    return () => window.clearInterval(timer);
  }, [paused, cards.length]);

  const show = (index: number) => setActive((index + cards.length) % cards.length);
  const card = cards[active];
  return (
    <aside
      className="hero-insight"
      aria-label="Live simulation findings"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
    >
      <div className="hero-insight__top">
        <span>{card.label}</span>
        <span>{active + 1} / {cards.length}</span>
      </div>
      <strong>{card.value}</strong>
      <p>{card.body}</p>
      <div className="hero-insight__controls">
        <button type="button" onClick={() => show(active - 1)} aria-label="Previous finding">←</button>
        <div aria-hidden="true">
          {cards.map((_, index) => (
            <span key={index} className={index === active ? "active" : ""} />
          ))}
        </div>
        <button type="button" onClick={() => show(active + 1)} aria-label="Next finding">→</button>
      </div>
    </aside>
  );
}
