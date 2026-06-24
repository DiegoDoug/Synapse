import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useTelegramStatus } from "@/features/notifications/useNotifications";
import { cn } from "@/lib/utils";
import { type ThemeMode, useAppStore } from "@/store/useAppStore";

const themeOptions: { value: ThemeMode; label: string }[] = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
];

/** Settings route — appearance controls and Telegram delivery status. */
export default function SettingsPage() {
  const themeMode = useAppStore((state) => state.themeMode);
  const setThemeMode = useAppStore((state) => state.setThemeMode);
  const telegram = useTelegramStatus();
  const ready = Boolean(
    telegram.data?.configured && telegram.data?.chat_configured,
  );

  return (
    <div className="max-w-2xl space-y-6 p-4 md:p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">Manage your preferences.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
          <CardDescription>Choose your preferred color theme.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="inline-flex rounded-md border border-border p-1">
            {themeOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => setThemeMode(option.value)}
                className={cn(
                  "rounded px-4 py-1.5 text-sm font-medium transition-colors",
                  themeMode === option.value
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Telegram notifications</CardTitle>
          <CardDescription>
            Deliver reminders, alerts, and daily summaries to your phone.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "inline-block h-2.5 w-2.5 rounded-full",
                ready ? "bg-emerald-500" : "bg-muted-foreground/40",
              )}
            />
            <span className="text-sm font-medium">
              {ready ? "Connected" : "Not configured"}
            </span>
          </div>
          {!ready && (
            <p className="text-sm text-muted-foreground">
              Set <code>TELEGRAM_BOT_TOKEN</code> and{" "}
              <code>TELEGRAM_DEFAULT_CHAT_ID</code> in the backend environment,
              then restart the server. The bot also responds to{" "}
              <code>/help</code>, <code>/summary</code>, and{" "}
              <code>/unread</code>.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
