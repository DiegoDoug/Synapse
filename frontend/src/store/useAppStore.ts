import { create } from "zustand";

export type ThemeMode = "light" | "dark";

interface AppState {
  /** Whether the sidebar is collapsed. */
  sidebarCollapsed: boolean;
  /** Active color theme (dark-mode first). */
  themeMode: ThemeMode;
  /** Current active route path (for nav highlighting). */
  activeRoute: string;
  /** Speak the assistant's replies aloud after each turn (Stage 4.7). */
  voiceAutoRead: boolean;

  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setThemeMode: (mode: ThemeMode) => void;
  setActiveRoute: (route: string) => void;
  setVoiceAutoRead: (enabled: boolean) => void;
}

/**
 * Global UI store (Zustand): sidebar, theme, active route.
 * No server state here — that lives in React Query.
 */
export const useAppStore = create<AppState>((set) => ({
  sidebarCollapsed: false,
  themeMode: "dark",
  activeRoute: "/dashboard",
  voiceAutoRead: false,

  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  setThemeMode: (mode) => set({ themeMode: mode }),
  setActiveRoute: (route) => set({ activeRoute: route }),
  setVoiceAutoRead: (enabled) => set({ voiceAutoRead: enabled }),
}));
