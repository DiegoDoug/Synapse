import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { type ThemeMode, useAppStore } from "@/store/useAppStore";

const themeOptions: { value: ThemeMode; label: string }[] = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
];

/** Settings route — appearance controls (Stage 1 scope). */
export default function SettingsPage() {
  const themeMode = useAppStore((state) => state.themeMode);
  const setThemeMode = useAppStore((state) => state.setThemeMode);

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
    </div>
  );
}
