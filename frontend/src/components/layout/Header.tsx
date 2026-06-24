import { Menu, Moon, PanelLeft, Sun } from "lucide-react";

import { useTheme } from "@/hooks/useTheme";
import { useAppStore } from "@/store/useAppStore";

interface HeaderProps {
  /** Open the mobile sidebar drawer. */
  onOpenMobile: () => void;
}

/** Top navigation bar: mobile menu, sidebar collapse, and theme toggle. */
export default function Header({ onOpenMobile }: HeaderProps) {
  const toggleSidebar = useAppStore((state) => state.toggleSidebar);
  const { themeMode, toggleTheme } = useTheme();

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-border bg-background/95 px-4 backdrop-blur">
      <button
        type="button"
        onClick={onOpenMobile}
        className="inline-flex h-9 w-9 items-center justify-center rounded-md hover:bg-accent hover:text-accent-foreground md:hidden"
        aria-label="Open navigation"
      >
        <Menu className="h-5 w-5" />
      </button>

      <button
        type="button"
        onClick={toggleSidebar}
        className="hidden h-9 w-9 items-center justify-center rounded-md hover:bg-accent hover:text-accent-foreground md:inline-flex"
        aria-label="Toggle sidebar"
      >
        <PanelLeft className="h-5 w-5" />
      </button>

      <div className="flex-1" />

      <button
        type="button"
        onClick={toggleTheme}
        className="inline-flex h-9 w-9 items-center justify-center rounded-md hover:bg-accent hover:text-accent-foreground"
        aria-label="Toggle theme"
      >
        {themeMode === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
      </button>
    </header>
  );
}
