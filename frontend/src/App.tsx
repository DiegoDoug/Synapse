import { Navigate, Route, Routes } from "react-router-dom";

import AppLayout from "@/components/layout/AppLayout";
import AssistantPage from "@/pages/AssistantPage";
import DashboardPage from "@/pages/DashboardPage";
import NotificationsPage from "@/pages/NotificationsPage";
import SettingsPage from "@/pages/SettingsPage";

/** Application routes wrapped in the responsive layout shell. */
export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/assistant" element={<AssistantPage />} />
        <Route path="/notifications" element={<NotificationsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
