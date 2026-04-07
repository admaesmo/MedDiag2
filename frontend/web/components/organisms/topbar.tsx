"use client";

import { Bell, Search, Settings } from "lucide-react";
import { useUiStore } from "@/stores/ui-store";
import { supportedLocales } from "@/lib/i18n/config";
import { t } from "@/lib/i18n";
import { Input } from "@/components/atoms/input";
import { LogoutButton } from "@/components/logout-button";

export function Topbar({ userEmail }: { userEmail: string }) {
  const locale = useUiStore((state) => state.locale);
  const setLocale = useUiStore((state) => state.setLocale);

  return (
    <header className="sticky top-0 z-20 flex h-20 items-center justify-between bg-surface-low px-4 lg:px-8">
      <div className="flex items-center gap-6">
        <h1 className="font-headline text-2xl font-extrabold text-primary">{t(locale, "common", "appName")}</h1>
        <div className="relative hidden w-80 lg:block">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            aria-label={t(locale, "common", "searchPlaceholder")}
            className="pl-10"
            placeholder={t(locale, "common", "searchPlaceholder")}
          />
        </div>
      </div>

      <div className="flex items-center gap-2 lg:gap-3">
        <select
          value={locale}
          onChange={(event) => setLocale(event.target.value as (typeof supportedLocales)[number])}
          className="ghost-border rounded-lg bg-surface-lowest px-2 py-2 text-xs font-semibold text-foreground"
          aria-label={t(locale, "common", "localeSelector")}
        >
          {supportedLocales.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>

        <button
          type="button"
          className="rounded-xl p-2 text-muted-foreground hover:bg-surface-high"
          aria-label={t(locale, "common", "notifications")}
        >
          <Bell className="h-4 w-4" />
        </button>
        <button
          type="button"
          className="rounded-xl p-2 text-muted-foreground hover:bg-surface-high"
          aria-label={t(locale, "common", "actions")}
        >
          <Settings className="h-4 w-4" />
        </button>

        <div
          className="hidden rounded-full bg-surface-lowest px-3 py-1.5 text-xs font-semibold text-muted-foreground lg:block"
          aria-label={t(locale, "common", "userEmail")}
        >
          {userEmail}
        </div>
        <LogoutButton />
      </div>
    </header>
  );
}
