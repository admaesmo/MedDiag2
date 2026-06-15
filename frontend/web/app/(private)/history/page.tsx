"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Button } from "@/components/atoms/button";
import { Card } from "@/components/atoms/card";
import { useSessionState } from "@/features/auth/use-session";
import { getDiagnosisHistory, getMyAudio } from "@/lib/api";
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

function isReadyStatus(status: string) {
  return status === "processed" || status === "transcribed";
}

function translateAudioStatus(locale: string, status: string) {
  const normalized = status.toLowerCase();
  if (normalized === "processing") return t(locale, "common", "processing");
  if (normalized === "processed" || normalized === "transcribed") return t(locale, "common", "ready");
  if (normalized === "uploaded") return t(locale, "common", "uploaded");
  if (normalized === "failed") return t(locale, "common", "failed");
  return status;
}

export default function HistoryPage() {
  const router = useRouter();
  const locale = useUiStore((state) => state.locale);
  const { accessToken } = useSessionState();
  const historyQuery = useQuery({
    queryKey: ["history", "full"],
    enabled: Boolean(accessToken),
    queryFn: () => getDiagnosisHistory(accessToken as string, 50),
  });
  const audioQuery = useQuery({
    queryKey: ["audio", "me", "history"],
    enabled: Boolean(accessToken),
    queryFn: () => getMyAudio(accessToken as string),
    refetchInterval: (query) => {
      const hasProcessing = query.state.data?.items?.some((item) => item.status === "processing");
      return hasProcessing ? 2000 : false;
    },
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

      <Card className="overflow-auto p-0">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">{t(locale, "history", "audioCaption")}</caption>
          <thead className="bg-surface-low">
            <tr className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
              <th className="px-4 py-3" scope="col">{t(locale, "common", "id")}</th>
              <th className="px-4 py-3" scope="col">{t(locale, "history", "audioFile")}</th>
              <th className="px-4 py-3" scope="col">{t(locale, "common", "status")}</th>
              <th className="px-4 py-3" scope="col">{t(locale, "history", "actions")}</th>
            </tr>
          </thead>
          <tbody>
            {audioQuery.data?.items?.map((audio, idx) => {
              const ready = audio.is_ready_for_inference ?? isReadyStatus(audio.status);
              const processing = audio.status === "processing";
              return (
                <tr key={audio.id} className="border-t border-surface-low">
                  <th className="px-4 py-3 font-medium" scope="row">#{idx + 1}</th>
                  <td className="px-4 py-3">{audio.original_filename ?? "audio"}</td>
                  <td className="px-4 py-3">{translateAudioStatus(locale, audio.status)}</td>
                  <td className="px-4 py-3">
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={!ready || processing}
                      onClick={() => router.push(`/parkinson?audio=${audio.id}`)}
                    >
                      {t(locale, "parkinson", "runInference")}
                    </Button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {audioQuery.isLoading ? <p className="p-4 text-sm text-muted-foreground" role="status" aria-live="polite">{t(locale, "common", "loading")}</p> : null}
        {audioQuery.isError ? <p className="p-4 text-sm font-semibold text-red-700" role="alert">{t(locale, "history", "audioLoadError")}</p> : null}
      </Card>
    </section>
  );
}
