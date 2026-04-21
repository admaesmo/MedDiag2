"use client";

import { Activity, Gauge, HeartPulse, History, Mic, Settings } from "lucide-react";
import { useUiStore } from "@/stores/ui-store";
import { t } from "@/lib/i18n";
import { NavItem } from "@/components/molecules/nav-item";

export function Sidebar() {
  const locale = useUiStore((state) => state.locale);

  return (
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
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          <HeartPulse className="h-4 w-4" />
          <span>{t(locale, "sidebar", "atriumLabel")}</span>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">{t(locale, "sidebar", "atriumDescription")}</p>
        <div className="mt-3 flex items-center gap-2 text-primary">
          <Activity className="h-4 w-4" />
          <span className="text-sm font-semibold">{t(locale, "sidebar", "systemReady")}</span>
        </div>
      </div>
    </aside>
  );
}
