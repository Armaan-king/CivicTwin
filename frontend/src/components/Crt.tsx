import type { ReactNode } from "react";

/** The screen surface. Texture sits under the interface, never over it. */
export function Crt({ children, ambient = true }: { children: ReactNode; ambient?: boolean }) {
  return (
    <div style={{ position: "relative", minHeight: "100%", overflow: "hidden" }}>
      {ambient && <div className="crt-amb" />}
      <div className="crt-scan" />
      <div className="crt-vig" />
      <div style={{ position: "relative", zIndex: 2, minHeight: "100%", display: "flex", flexDirection: "column" }}>
        {children}
      </div>
    </div>
  );
}
