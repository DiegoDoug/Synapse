import { useEffect } from "react";

import { useAppStore } from "@/store/useAppStore";

/**
 * Applies the active theme to <html> and exposes a toggle.
 * Call once in the layout so the `dark` class stays in sync with the store.
 */
export function useTheme() {
  const themeMode = useAppStore((state) => state.themeMode);
  const setThemeMode = useAppStore((state) => state.setThemeMode);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", themeMode === "dark");
  }, [themeMode]);

  const toggleTheme = () => setThemeMode(themeMode === "dark" ? "light" : "dark");

  return { themeMode, toggleTheme };
}
