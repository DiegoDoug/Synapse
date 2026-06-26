import {
  Bell,
  Bot,
  FileText,
  LayoutDashboard,
  Settings,
  Sparkles,
  Zap,
} from "lucide-react";
import { NavLink } from "react-router-dom";

import { useNotificationCounts } from "@/features/notifications/useNotifications";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/store/useAppStore";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/assistant", label: "Assistant", icon: Sparkles },
  { to: "/agents", label: "Agents", icon: Bot },
  { to: "/documents", label: "Knowledge", icon: FileText },
  { to: "/notifications", label: "Notifications", icon: Bell },
  { to: "/settings", label: "Settings", icon: Settings },
];

interface SidebarProps {
  /** Whether the off-canvas drawer is open on mobile. */
  mobileOpen: boolean;
  /** Close the mobile drawer (overlay tap / navigation). */
  onCloseMobile: () => void;
}

/** Collapsible left navigation. Off-canvas drawer on mobile, fixed rail on desktop. */
export default function Sidebar({ mobileOpen, onCloseMobile }: SidebarProps) {
  const collapsed = useAppStore((state) => state.sidebarCollapsed);
  const { data: counts } = useNotificationCounts();
  const unread = counts?.unread ?? 0;

  return (
    <>
      {/* Mobile overlay */}
      <div
        className={cn(
          "fixed inset-0 z-40 bg-black/50 md:hidden",
          mobileOpen ? "block" : "hidden",
        )}
        onClick={onCloseMobile}
        aria-hidden="true"
      />

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-card transition-all duration-200",
          collapsed ? "md:w-16" : "md:w-64",
          mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
        )}
      >
        {/* Brand */}
        <div className="flex h-14 items-center gap-2 border-b border-border px-4">
          <Zap className="h-5 w-5 shrink-0 text-primary" />
          <span className={cn("font-semibold tracking-tight", collapsed && "md:hidden")}>
            Synapse
          </span>
        </div>

        {/* Navigation */}
        <nav className="flex flex-1 flex-col gap-1 p-2">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={onCloseMobile}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  "hover:bg-accent hover:text-accent-foreground",
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground",
                  collapsed && "md:justify-center md:px-0",
                )
              }
            >
              <span className="relative shrink-0">
                <Icon className="h-4 w-4" />
                {to === "/notifications" && unread > 0 && collapsed && (
                  <span className="absolute -right-1 -top-1 hidden h-2 w-2 rounded-full bg-primary md:block" />
                )}
              </span>
              <span className={cn("flex-1", collapsed && "md:hidden")}>{label}</span>
              {to === "/notifications" && unread > 0 && (
                <span
                  className={cn(
                    "ml-auto inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1.5 text-xs font-semibold text-primary-foreground",
                    collapsed && "md:hidden",
                  )}
                >
                  {unread > 99 ? "99+" : unread}
                </span>
              )}
            </NavLink>
          ))}
        </nav>
      </aside>
    </>
  );
}
