import { useEffect, useMemo, useRef, useState } from "react";
import { Crt } from "@/components/Crt";
import { TopBar } from "@/components/TopBar";
import { Loading, Failed } from "@/components/ui";
import { useRun } from "@/lib/useRun";
import type { AgentVoice, VoiceListing } from "@/types/voice";

/**
 * Two thousand residents, one at a time.
 *
 * Every other screen reports the population as a rate. This one is the only place it
 * appears as people, which is the whole reason it exists: a planner can dismiss "2.2% of
 * Ang Mo Kio Ave 3" and cannot dismiss a named person saying they have stopped going to
 * the hospital.
 *
 * Nothing here is decoration. Each turn cites the engine events it was written from, the
 * page says which of them produced the text, and a resident who was not affected says so
 * rather than being hidden — most of a town not noticing is a finding too.
 */

const ADAPTATION: Record<string, { label: string; tone: "alert" | "gold" | "quiet" }> = {
  unaffected: { label: "no change", tone: "quiet" },
  adapting: { label: "adapting", tone: "gold" },
  absorbing: { label: "absorbing it", tone: "alert" },
  substituting: { label: "paying another way", tone: "gold" },
  delegating: { label: "someone else goes", tone: "alert" },
  giving_up: { label: "stopped going", tone: "alert" },
};

type Filter = "affected" | "moved" | "all";

export function Voices() {
  const { run, error } = useRun();
  const [data, setData] = useState<VoiceListing | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("affected");
  const [open, setOpen] = useState<string | null>(null);
  const [revealed, setRevealed] = useState(0);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    let alive = true;
    import("@/lib/api")
      .then((m) => m.fetchVoices(run?.run_id ?? "run_a91f", 300))
      .then((d) => alive && setData(d))
      .catch((e) => alive && setFailed(String(e?.message ?? e)));
    return () => {
      alive = false;
    };
  }, [run?.run_id]);

  const shown = useMemo(() => {
    const all = data?.voices ?? [];
    if (filter === "all") return all;
    if (filter === "moved") {
      return [...all]
        .filter((v) => v.turns.length > 1)
        .sort((a, b) => moved(a) - moved(b));
    }
    return all.filter((v) => v.turns.length > 1);
  }, [data, filter]);

  // reveal in sequence: this is a queue of people arriving, not a table painting itself
  useEffect(() => {
    setRevealed(0);
    if (timer.current) window.clearInterval(timer.current);
    if (!shown.length) return;
    timer.current = window.setInterval(() => {
      setRevealed((r) => {
        if (r >= shown.length) {
          if (timer.current) window.clearInterval(timer.current);
          return r;
        }
        return r + 1;
      });
    }, 26);
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [shown]);

  if (error) return <Failed message={error} />;
  if (failed) return <Failed message={failed} />;
  if (!run || !data) return <Loading what="residents" />;

  const download = () => {
    const lines = (data.voices ?? []).map((v) => {
      const head = `## ${v.name}  (${v.persona_id})\n\n_${v.summary}_\n`;
      const turns = v.turns
        .map(
          (t) =>
            `**Round ${t.round}** · support ${t.position.toFixed(2)} · ` +
            `${t.response} · ${t.severity}\n\n` +
            `${t.reasoning}\n` +
            (t.changed_because ? `\n> changed because: ${t.changed_because}\n` : "") +
            (t.influenced_by ? `\n> after hearing from ${t.influenced_by}\n` : "") +
            (t.grounded_in.length ? `\n\`facts: ${t.grounded_in.join(", ")}\`\n` : "")
        )
        .join("\n");
      return `${head}\n${turns}`;
    });
    const doc =
      `# Resident deliberation\n\n` +
      `Run \`${run.run_id}\` · ${run.study_area} · ${data.total} residents, ` +
      `${data.spoke} who spoke more than once, ${data.moved} who changed their mind.\n\n` +
      `Reasoned by **${data.model}** in ${data.seconds}s over ${data.calls} model calls ` +
      `(${data.cached_batches} served from cache). Each resident reasoned only from facts ` +
      `they were given; ${data.rejected} turns were rejected for citing something they ` +
      `were not told.\n\n` +
      `Residents are synthetic. The bus network is real (LTA DataMall).\n\n---\n\n` +
      lines.join("\n---\n\n");
    const url = URL.createObjectURL(new Blob([doc], { type: "text/markdown" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `civictwin-voices-${run.run_id}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Crt>
      <TopBar meta={`${data.total.toLocaleString()} RESIDENTS`} />

      <div style={{ padding: "var(--s-4) var(--s-6) var(--s-2)", flexShrink: 0 }}>
        <h1 className="t1" style={{ fontSize: "var(--fs-28)", fontWeight: 500, margin: 0 }}>
          What residents make of it
        </h1>
        <p className="t2" style={{ fontSize: "var(--fs-16)", lineHeight: 1.7, margin: "var(--s-2) 0 0", maxWidth: "76ch" }}>
          Every resident reasons about the policy in each round, using only what the
          simulation recorded happening to them.{" "}
          <span className="t1">{data.spoke.toLocaleString()}</span> of{" "}
          {data.total.toLocaleString()} had something to report. The rest did not notice,
          which is its own finding.
        </p>

        <div style={{ display: "flex", gap: "var(--s-3)", alignItems: "center", flexWrap: "wrap", marginTop: "var(--s-3)" }}>
          {(["affected", "moved", "all"] as Filter[]).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              aria-pressed={filter === f}
              className={filter === f ? "t1" : "t3"}
              style={{
                background: "none", border: "none", borderBottom: `1px solid ${filter === f ? "var(--gold)" : "transparent"}`,
                color: "inherit", fontFamily: "inherit", fontSize: "var(--fs-14)",
                padding: "2px 0", cursor: "pointer", borderRadius: 0,
              }}
            >
              {f === "affected" ? "affected" : f === "moved" ? "changed their mind most" : "everyone"}
            </button>
          ))}
          <span style={{ flexGrow: 1 }} />
          <span className="t3" style={{ fontSize: "var(--fs-12)" }}>
            reasoned by {data.model} · {data.calls} calls, {data.cached_batches} cached, {data.seconds}s
            {data.rejected > 0 && ` · ${data.rejected} turns rejected as ungrounded`}
          </span>
          <button className="btn" onClick={download}>DOWNLOAD TRANSCRIPT</button>
        </div>
      </div>

      <div style={{ flexGrow: 1, overflowY: "auto", padding: "0 var(--s-6) var(--s-5)", minHeight: 0 }}>
        <div style={{ display: "flex", flexDirection: "column" }}>
          {shown.slice(0, revealed).map((v) => {
            const last = v.turns[v.turns.length - 1];
            const tone = ADAPTATION[last?.response ?? "unaffected"];
            const isOpen = open === v.persona_id;
            return (
              <article
                key={v.persona_id}
                onClick={() => setOpen(isOpen ? null : v.persona_id)}
                style={{
                  borderTop: "1px solid var(--rule-dim)",
                  padding: "var(--s-3) 0",
                  cursor: "pointer",
                  animation: "voiceIn .28s ease both",
                }}
              >
                <div style={{ display: "flex", alignItems: "baseline", gap: "var(--s-2)", flexWrap: "wrap" }}>
                  <span className="t1" style={{ fontSize: "var(--fs-16)", fontWeight: 600 }}>{v.name}</span>
                  <span
                    className={tone.tone === "quiet" ? "t3" : tone.tone}
                    style={{ fontSize: "var(--fs-12)", letterSpacing: "0.08em" }}
                  >
                    {tone.label.toUpperCase()}
                  </span>
                  <span style={{ flexGrow: 1 }} />
                  <span className="t3" style={{ fontSize: "var(--fs-12)" }}>
                    support {v.turns[0].position.toFixed(2)}
                    {v.turns.length > 1 && ` → ${last.position.toFixed(2)}`}
                  </span>
                </div>
                <p className="t3" style={{ fontSize: "var(--fs-12)", margin: "3px 0 0" }}>{v.summary}</p>
                <p className="t2" style={{ fontSize: "var(--fs-16)", lineHeight: 1.7, margin: "var(--s-2) 0 0", maxWidth: "72ch" }}>
                  {last.reasoning}
                </p>

                {isOpen && v.turns.length > 1 && (
                  <ol style={{ listStyle: "none", margin: "var(--s-3) 0 0", padding: "0 0 0 var(--s-3)", borderLeft: "1px solid var(--rule)", display: "flex", flexDirection: "column", gap: "var(--s-2)" }}>
                    {v.turns.map((t) => (
                      <li key={t.round}>
                        <div style={{ display: "flex", gap: "var(--s-2)", alignItems: "baseline" }}>
                          <span className="t3" style={{ fontSize: "var(--fs-12)" }}>ROUND {t.round}</span>
                          <span className="t3" style={{ fontSize: "var(--fs-12)" }}>
                            support {t.position.toFixed(2)} · confidence {t.confidence.toFixed(2)}
                          </span>
                        </div>
                        <p className="t2" style={{ fontSize: "var(--fs-14)", lineHeight: 1.65, margin: "4px 0 0", maxWidth: "70ch" }}>
                          {t.reasoning}
                        </p>
                        {t.changed_because && (
                          <p className="t3" style={{ fontSize: "var(--fs-12)", margin: "4px 0 0" }}>
                            changed because: {t.changed_because}
                          </p>
                        )}
                        {t.grounded_in.length > 0 && (
                          <p className="t3" style={{ fontSize: "var(--fs-12)", margin: "4px 0 0", color: "var(--fig-quiet)" }}>
                            from facts {t.grounded_in.slice(0, 6).join(", ")}
                            {t.grounded_in.length > 6 && ` +${t.grounded_in.length - 6}`}
                          </p>
                        )}
                      </li>
                    ))}
                  </ol>
                )}
              </article>
            );
          })}
        </div>
        {revealed < shown.length && (
          <p className="t3" style={{ fontSize: "var(--fs-14)", padding: "var(--s-3) 0" }}>
            {shown.length - revealed} more arriving…
          </p>
        )}
      </div>
    </Crt>
  );
}

function moved(v: AgentVoice): number {
  if (v.turns.length < 2) return 0;
  return v.turns[v.turns.length - 1].position - v.turns[0].position;
}
