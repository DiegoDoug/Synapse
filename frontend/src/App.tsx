import { Navigate, Route, Routes } from "react-router-dom";

import DashboardPage from "@/pages/DashboardPage";
import SettingsPage from "@/pages/SettingsPage";

/**
 * App shell — routing only.
 * The layout (Step 5) and page content (Step 6) are added in later steps.
 */
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/settings" element={<SettingsPage />} />
    </Routes>
  );
}
