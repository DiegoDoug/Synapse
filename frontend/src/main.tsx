import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";

import App from "@/App";
import { queryClient } from "@/lib/queryClient";
import { useAppStore } from "@/store/useAppStore";
import "@/styles/globals.css";

// Apply the initial theme class (dark-mode first per GOVERNANCE).
document.documentElement.classList.toggle(
  "dark",
  useAppStore.getState().themeMode === "dark",
);

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element #root not found");
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
