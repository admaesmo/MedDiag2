"use client";

import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/atoms/card";
import { useSessionState } from "@/features/auth/use-session";
import { getDiagnosisHistory } from "@/lib/api";
import { useUiStore } from "@/stores/ui-store";
import { t } from "@/lib/i18n";

function translateResult(locale: string, result?: string) {
  if (result === "positive") {
    return t(locale, "history", "resultPositive");
  }
  if (result === "negative") {
    return t(locale, "history", "resultNegative");
  }
  return t(locale, "common", "notAvailable");
}

function formatModelLabel(diseaseName: string, diseaseCode: string) {
  return diseaseName?.trim() ? diseaseName : diseaseCode;
}

export default function HistoryPage() {
  const locale = useUiStore((state) => state.locale);
  const { accessToken } = useSessionState();
  const historyQuery = useQuery({
    queryKey: ["history", "full"],
    enabled: Boolean(accessToken),
    queryFn: () => getDiagnosisHistory(accessToken as string, 50),
  });

  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-4xl font-extrabold">{t(locale, "history", "title")}</h2>
        <p className="mt-2 text-muted-foreground">{t(locale, "history", "subtitle")}</p>
      </header>

      <Card className="overflow-auto p-0">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">{t(locale, "history", "caption")}</caption>
          <thead className="bg-surface-low">
            <tr className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
              <th className="px-4 py-3" scope="col">{t(locale, "common", "id")}</th>
              <th className="px-4 py-3" scope="col">{t(locale, "common", "userEmail")}</th>
              <th className="px-4 py-3" scope="col">{t(locale, "common", "model")}</th>
              <th className="px-4 py-3" scope="col">{t(locale, "history", "audioFile")}</th>
              <th className="px-4 py-3" scope="col">{t(locale, "common", "status")}</th>
              <th className="px-4 py-3" scope="col">{t(locale, "common", "probability")}</th>
            </tr>
          </thead>
          <tbody>
            {historyQuery.data?.map((item, idx) => (
              <tr key={item.id} className="border-t border-surface-low">
                <th className="px-4 py-3 font-medium" scope="row">#{idx + 1}</th>
                <td className="px-4 py-3">{item.user_email}</td>
                <td className="px-4 py-3">{formatModelLabel(item.disease_name, item.disease_code)}</td>
                <td className="px-4 py-3">{item.audio_filename ?? t(locale, "common", "notAvailable")}</td>
                <td className="px-4 py-3">
                  <span className={item.result === "positive" ? "font-semibold text-red-700" : item.result === "negative" ? "font-semibold text-emerald-700" : ""}>
                    {translateResult(locale, item.result)}
                  </span>
                </td>
                <td className="px-4 py-3 text-primary">{(item.probability * 100).toFixed(2)}%</td>
              </tr>
            ))}
          </tbody>
        </table>

        {historyQuery.isLoading ? <p className="p-4 text-sm text-muted-foreground" role="status" aria-live="polite">{t(locale, "common", "loading")}</p> : null}
        {historyQuery.isError ? <p className="p-4 text-sm font-semibold text-red-700" role="alert">{t(locale, "history", "loadError")}</p> : null}
      </Card>
    </section>
  );
}
