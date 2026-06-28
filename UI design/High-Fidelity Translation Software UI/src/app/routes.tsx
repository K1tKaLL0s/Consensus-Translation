import { createBrowserRouter, Outlet } from "react-router";
import { Layout } from "./components/Layout";
import { MainWorkspace } from "./pages/MainWorkspace";
import { History } from "./pages/History";
import { TranslationDetail } from "./pages/TranslationDetail";
import { Settings } from "./pages/Settings";
import { ApiConfig } from "./pages/ApiConfig";
import { TermbaseManagement } from "./pages/TermbaseManagement";
import { ExportTermbase } from "./pages/ExportTermbase";
import { DataPrivacy } from "./pages/DataPrivacy";
import { AppearanceSettings } from "./pages/AppearanceSettings";
import { LearningMode } from "./pages/LearningMode";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Layout,
    children: [
      { index: true, Component: MainWorkspace },
      { path: "learning", Component: LearningMode },
      { path: "history", Component: History },
      { path: "history/:id", Component: TranslationDetail },
      { path: "settings", Component: Settings },
      { path: "settings/api", Component: ApiConfig },
      { path: "settings/termbase", Component: TermbaseManagement },
      { path: "settings/termbase/export", Component: ExportTermbase },
      { path: "settings/privacy", Component: DataPrivacy },
      { path: "settings/appearance", Component: AppearanceSettings },
    ],
  },
]);
