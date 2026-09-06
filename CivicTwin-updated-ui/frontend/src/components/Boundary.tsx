import { Component, type ErrorInfo, type ReactNode } from "react";

/**
 * A thrown component should cost one panel, not the whole screen.
 *
 * Without this, a bad field in the run or a machine without WebGL turns the demo into a
 * white page with nothing to say. AGENTS.md 18: fail visibly and diagnosably.
 */
interface Props {
  children: ReactNode;
  /** shown instead of the children; keep it small and specific to what was lost */
  label: string;
  /** rendered in place of the failed subtree, so the rest of the page survives */
  fallback?: ReactNode;
}

interface State {
  error: Error | null;
}

export class Boundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error(`[CivicTwin] ${this.props.label} failed`, error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    if (this.props.fallback) return this.props.fallback;

    return (
      <div
        className="box"
        style={{
          padding: "var(--s-3)", display: "flex", flexDirection: "column",
          gap: "var(--s-1)", alignSelf: "start",
        }}
      >
        <span className="alert" style={{ fontSize: "var(--fs-14)", fontWeight: 600 }}>
          {this.props.label} could not be drawn
        </span>
        <span className="t3" style={{ fontSize: "var(--fs-12)", lineHeight: 1.6 }}>
          {this.state.error.message}. The rest of this screen is unaffected.
        </span>
      </div>
    );
  }
}

/** True when the browser can actually give us a WebGL context. */
export function hasWebGL(): boolean {
  try {
    const c = document.createElement("canvas");
    return Boolean(
      window.WebGLRenderingContext &&
        (c.getContext("webgl2") || c.getContext("webgl"))
    );
  } catch {
    return false;
  }
}
