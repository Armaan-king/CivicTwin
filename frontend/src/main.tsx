import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "./styles/tokens.css";
// Last, so its media queries win over the fixed tracks they are overriding without
// needing !important. Nothing in it applies above 900px.
import "./styles/responsive.css";
import { App } from "./App";


createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
);
