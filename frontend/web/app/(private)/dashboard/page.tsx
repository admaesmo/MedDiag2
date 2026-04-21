"use client";

import Link from "next/link";
import { Activity, HeartPulse, Mic } from "lucide-react";
import { Badge } from "@/components/atoms/badge";
import { Button } from "@/components/atoms/button";
import { Card } from "@/components/atoms/card";
import { useSessionState } from "@/features/auth/use-session";
import { useDashboardData } from "@/features/dashboard/queries";
import { useUiStore } from "@/stores/ui-store";
import { t } from "@/lib/i18n";

function DiagnosticCard({
  locale,
  title,
  variables,
  muted,
  href,
  icon,
}: {
  locale: string;
  title: string;
  variables: string;
  muted?: boolean;
  href: string;
  icon: React.ReactNode;
}) {
  return (
    <Card className={muted ? "opacity-80" : ""}>
      <div className="flex items-start justify-between">
        <div className="rounded-xl bg-surface-low p-3 text-primary">{icon}</div>
        <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">{variables}</span>
      </div>
      <h3 className="mt-5 text-xl font-bold text-foreground">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground">{t(locale, "dashboard", "cardDescription")}</p>
      <div className="mt-6 flex items-center justify-between">
        {muted ? <Badge label={t(locale, "dashboard", "soonBadge")} variant="muted" /> : <Badge label={t(locale, "dashboard", "active")} variant="success" />}
        {muted ? (
          <Button variant="secondary" size="sm" disabled aria-disabled="true">
            {t(locale, "dashboard", "locked")}
          </Button>
        ) : (
          <Link href={href} aria-label={`${t(locale, "dashboard", "open")} ${title}`}>
            <Button variant="primary" size="sm">{t(locale, "dashboard", "open")}</Button>
          </Link>
        )}
      </div>
    </Card>
  );
}

function translateStatus(locale: string, status: string) {
  const normalized = status.toLowerCase();
  if (normalized === "pending") {
    return t(locale, "common", "pending");
  }
  if (normalized === "confirmed") {
    return t(locale, "common", "confirmed");
  }
  if (normalized === "discarded") {
    return t(locale, "common", "discarded");
  }
  return status;
}

export default function DashboardPage() {
  const locale = useUiStore((state) => state.locale);
  const { accessToken, loading } = useSessionState();
  const { audioQuery, historyQuery } = useDashboardData(accessToken);

  return (
    <section className="space-y-10">
      <header>
        <h2 className="text-4xl font-extrabold text-foreground">{t(locale, "dashboard", "title")}</h2>
        <p className="mt-2 max-w-2xl text-muted-foreground">{t(locale, "dashboard", "subtitle")}</p>
      </header>

      <section className="grid gap-6 xl:grid-cols-3">
        <DiagnosticCard locale={locale} title={t(locale, "dashboard", "diabetesTitle")} variables={t(locale, "dashboard", "vars8")} muted href="/dashboard" icon={<Activity className="h-6 w-6" />} />
        <DiagnosticCard locale={locale} title={t(locale, "dashboard", "cardiovascularTitle")} variables={t(locale, "dashboard", "vars13")} muted href="/dashboard" icon={<HeartPulse className="h-6 w-6" />} />
        <DiagnosticCard locale={locale} title={t(locale, "dashboard", "parkinsonTitle")} variables={t(locale, "dashboard", "vars22")} href="/parkinson" icon={<Mic className="h-6 w-6" />} />
      </section>

      <section className="surface-pane">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-2xl font-bold">{t(locale, "dashboard", "recentHistory")}</h3>
          <Link className="text-sm font-semibold text-primary hover:text-primary-strong" href="/history">
            {t(locale, "common", "viewAll")}
          </Link>
        </div>

        {loading || audioQuery.isLoading || historyQuery.isLoading ? (
          <p className="text-sm text-muted-foreground" role="status" aria-live="polite">{t(locale, "common", "loading")}</p>
        ) : null}

        {audioQuery.isError || historyQuery.isError ? (
          <p className="text-sm font-semibold text-red-700" role="alert" aria-live="assertive">
            {t(locale, "common", "error")}: {(audioQuery.error as Error)?.message || (historyQuery.error as Error)?.message}
          </p>
        ) : null}

        {!historyQuery.isLoading && historyQuery.data?.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t(locale, "common", "empty")}</p>
        ) : null}

        {historyQuery.data?.length ? (
          <div className="overflow-hidden rounded-2xl bg-surface-lowest">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">{t(locale, "dashboard", "historyCaption")}</caption>
              <thead>
                <tr className="text-[11px] uppercase tracking-[0.1em] text-muted-foreground">
                  <th className="px-5 py-3" scope="col">{t(locale, "common", "patient")}</th>
                  <th className="px-5 py-3" scope="col">{t(locale, "common", "model")}</th>
                  <th className="px-5 py-3" scope="col">{t(locale, "common", "status")}</th>
                  <th className="px-5 py-3" scope="col">{t(locale, "common", "confidence")}</th>
                </tr>
              </thead>
              <tbody>
                {historyQuery.data.map((item) => (
                  <tr key={item.id} className="border-t border-white/30 text-foreground">
                    <th className="px-5 py-4 font-medium" scope="row">{item.user_name}</th>
                    <td className="px-5 py-4">{item.disease_name}</td>
                    <td className="px-5 py-4">{translateStatus(locale, item.status)}</td>
                    <td className="px-5 py-4 font-semibold text-primary">{(item.probability * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </section>
  );
}
