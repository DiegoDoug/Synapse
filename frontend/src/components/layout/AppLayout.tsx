import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";

import Header from "@/components/layout/Header";
import Sidebar from "@/components/layout/Sidebar";
import { useTheme } from "@/hooks/useTheme";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/store/useAppStore";

/** Responsive application shell: sidebar + header + routed content. */
export default function AppLayout() {
  useTheme(); // keep the <html> dark class in sync with the store
  const location = useLocation();
  const collapsed = useAppStore((state) => state.sidebarCollapsed);
  const setActiveRoute = useAppStore((state) => state.setActiveRoute);
  const [mobileOpen, setMobileOpen] = useState(false);

  // Track the active route and close the mobile drawer on navigation.
  useEffect(() => {
    setActiveRoute(location.pathname);
    setMobileOpen(false);
  }, [location.pathname, setActiveRoute]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Sidebar mobileOpen={mobileOpen} onCloseMobile={() => setMobileOpen(false)} />
      <div
        className={cn(
          "flex min-h-screen flex-col transition-all duration-200",
          collapsed ? "md:pl-16" : "md:pl-64",
        )}
      >
        <Header onOpenMobile={() => setMobileOpen(true)} />
        <main className="flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
