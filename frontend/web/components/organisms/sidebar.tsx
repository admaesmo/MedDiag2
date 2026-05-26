"use client";

import { Activity, Gauge, HeartPulse, History, Mic, Settings, X } from "lucide-react";
import { useUiStore } from "@/stores/ui-store";
import { t } from "@/lib/i18n";
import { NavItem } from "@/components/molecules/nav-item";

export function Sidebar() {
  const locale = useUiStore((state) => state.locale);
  const sidebarOpen = useUiStore((state) => state.sidebarOpen);
  const setSidebarOpen = useUiStore((state) => state.setSidebarOpen);

  const closeSidebar = () => setSidebarOpen(false);

  return (
    <>
      <aside className="hidden w-72 shrink-0 flex-col bg-surface-low px-4 py-8 lg:flex">
        <div className="mb-8 px-4">
          <p className="font-headline text-lg font-bold text-foreground">{t(locale, "sidebar", "title")}</p>
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{t(locale, "sidebar", "subtitle")}</p>
        </div>

        <nav className="space-y-2" aria-label={t(locale, "common", "primaryNavigation")}>
          <NavItem href="/dashboard" label={t(locale, "nav", "dashboard")} icon={Gauge} />
          <NavItem href="/parkinson" label={t(locale, "nav", "parkinson")} icon={Mic} />
          <NavItem href="/history" label={t(locale, "nav", "history")} icon={History} />
          <NavItem href="/settings" label={t(locale, "nav", "settings")} icon={Settings} />
        </nav>

        <div className="mt-auto rounded-2xl bg-surface-lowest p-4 shadow-ambient">
          <div className="flex items-center gap-2 text-primary">
            <Activity className="h-4 w-4" />
            <span className="text-sm font-semibold">{t(locale, "sidebar", "systemReady")}</span>
          </div>
        </div>
      </aside>

      <div className={`fixed inset-0 z-40 lg:hidden ${sidebarOpen ? "pointer-events-auto" : "pointer-events-none"}`} aria-hidden={!sidebarOpen}>
        <button
          type="button"
          className={`absolute inset-0 bg-foreground/35 transition-opacity ${sidebarOpen ? "opacity-100" : "opacity-0"}`}
          aria-label={t(locale, "common", "close")}
          onClick={closeSidebar}
          tabIndex={sidebarOpen ? 0 : -1}
        />

        <aside className={`absolute left-0 top-0 flex h-full w-[84%] max-w-xs flex-col bg-surface-low px-4 py-6 shadow-2xl transition-transform duration-200 ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}`}>
          <div className="mb-8 flex items-start justify-between gap-4 px-2">
            <div>
              <p className="font-headline text-lg font-bold text-foreground">{t(locale, "sidebar", "title")}</p>
              <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{t(locale, "sidebar", "subtitle")}</p>
            </div>
            <button
              type="button"
              className="rounded-xl p-2 text-muted-foreground hover:bg-surface-high"
              onClick={closeSidebar}
              aria-label={t(locale, "common", "close")}
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <nav className="space-y-2" aria-label={t(locale, "common", "primaryNavigation")}>
            <NavItem href="/dashboard" label={t(locale, "nav", "dashboard")} icon={Gauge} onClick={closeSidebar} />
            <NavItem href="/parkinson" label={t(locale, "nav", "parkinson")} icon={Mic} onClick={closeSidebar} />
            <NavItem href="/history" label={t(locale, "nav", "history")} icon={History} onClick={closeSidebar} />
            <NavItem href="/settings" label={t(locale, "nav", "settings")} icon={Settings} onClick={closeSidebar} />
          </nav>

          <div className="mt-auto rounded-2xl bg-surface-lowest p-4 shadow-ambient">
            <div className="flex items-center gap-2 text-primary">
              <Activity className="h-4 w-4" />
              <span className="text-sm font-semibold">{t(locale, "sidebar", "systemReady")}</span>
            </div>
          </div>
        </aside>
      </div>
    </>
  );
}
