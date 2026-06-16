"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/atoms/button";
import { Card } from "@/components/atoms/card";
import { useSessionState } from "@/features/auth/use-session";
import { useAudioRecording } from "@/features/parkinson/use-audio-recording";
import {
  useVoiceSession,
  isTakeProcessed,
  isTakeFailed,
  isTakeInProgress,
} from "@/features/parkinson/use-voice-session";
import { useUiStore } from "@/stores/ui-store";
import { t } from "@/lib/i18n";

function formatElapsed(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return [hours, minutes, seconds].map((value) => String(value).padStart(2, "0")).join(":");
}

function Alert({
  variant,
  title,
  detail,
}: {
  variant: "error" | "warning" | "success";
  title: string;
  detail?: string | null;
}) {
  const styles =
    variant === "error"
      ? "border-red-200 bg-red-50 text-red-800"
      : variant === "warning"
        ? "border-amber-200 bg-amber-50 text-amber-800"
        : "border-emerald-200 bg-emerald-50 text-emerald-800";
  const Icon = variant === "success" ? CheckCircle2 : AlertTriangle;
  return (
    <div
      role={variant === "success" ? "status" : "alert"}
      className={`mx-auto mt-3 flex w-full max-w-md items-start gap-3 rounded-xl border p-4 text-left ${styles}`}
    >
      <Icon className="mt-0.5 h-5 w-5 shrink-0" />
      <div className="min-w-0">
        <p className="text-sm font-semibold">{title}</p>
        {detail ? <p className="mt-0.5 break-words text-xs opacity-90">{detail}</p> : null}
      </div>
    </div>
  );
}

export default function ParkinsonPage() {
  const router = useRouter();
  const locale = useUiStore((state) => state.locale);
  const consentAcceptedEmails = useUiStore((state) => state.parkinsonConsentAcceptedEmails);
  const addConsentEmail = useUiStore((state) => state.addParkinsonConsentEmail);
  const [consentError, setConsentError] = useState<string | null>(null);
  const [recordingForTake, setRecordingForTake] = useState<number | null>(null);
  const [confirmingRemoveTake, setConfirmingRemoveTake] = useState<number | null>(null);
  const [isGuideOpen, setIsGuideOpen] = useState(false);
  const [checks, setChecks] = useState({
    data: false,
    validation: false,
    service: false,
  });
  const firstConsentRef = useRef<HTMLInputElement>(null);
  const { accessToken, email, loading: sessionLoading } = useSessionState();
  const sessionRecording = useAudioRecording();
  const voiceSession = useVoiceSession(accessToken);

  const aggregatedFeatures = voiceSession.result?.aggregated_features;

  const biomarkerCards = [
    {
      key: "pitch_mean",
      label: t(locale, "parkinson", "biomarkerPitchMean"),
      description: t(locale, "parkinson", "biomarkerPitchMeanInfo"),
      value: aggregatedFeatures?.["MDVP:Fo(Hz)"],
      unit: "Hz",
      decimals: 2,
    },
    {
      key: "pitch_min",
      label: t(locale, "parkinson", "biomarkerPitchMin"),
      description: t(locale, "parkinson", "biomarkerPitchMinInfo"),
      value: aggregatedFeatures?.["MDVP:Flo(Hz)"],
      unit: "Hz",
      decimals: 2,
    },
    {
      key: "pitch_max",
      label: t(locale, "parkinson", "biomarkerPitchMax"),
      description: t(locale, "parkinson", "biomarkerPitchMaxInfo"),
      value: aggregatedFeatures?.["MDVP:Fhi(Hz)"],
      unit: "Hz",
      decimals: 2,
    },
    {
      key: "jitter_local",
      label: t(locale, "parkinson", "biomarkerJitterLocal"),
      description: t(locale, "parkinson", "biomarkerJitterLocalInfo"),
      value: aggregatedFeatures?.["MDVP:Jitter(%)"],
      unit: "",
      decimals: 6,
    },
    {
      key: "shimmer_local",
      label: t(locale, "parkinson", "biomarkerShimmerLocal"),
      description: t(locale, "parkinson", "biomarkerShimmerLocalInfo"),
      value: aggregatedFeatures?.["MDVP:Shimmer"],
      unit: "",
      decimals: 6,
    },
    {
      key: "hnr_mean",
      label: t(locale, "parkinson", "biomarkerHnrMean"),
      description: t(locale, "parkinson", "biomarkerHnrMeanInfo"),
      value: aggregatedFeatures?.["HNR"],
      unit: "dB",
      decimals: 2,
    },
  ];

  const consentAccepted = !sessionLoading && Boolean(email) && consentAcceptedEmails.includes(email);
  const isConsentOpen = !consentAccepted;

  useEffect(() => {
    if (isConsentOpen) {
      firstConsentRef.current?.focus();
    }
  }, [isConsentOpen]);

  // Show recording guide once per browser session after consent is accepted
  useEffect(() => {
    if (!consentAccepted) return;
    const key = `parkinson-guide-shown-${email}`;
    if (!sessionStorage.getItem(key)) {
      setIsGuideOpen(true);
      sessionStorage.setItem(key, "1");
    }
  }, [consentAccepted, email]);

  const canProceed = checks.data && checks.validation && checks.service;

  const validSessionTakes = voiceSession.session?.takes.filter((tk) => isTakeProcessed(tk.status)).length ?? 0;

  const handleContinue = () => {
    if (!canProceed) {
      setConsentError(t(locale, "parkinson", "consentRequired"));
      return;
    }

    setConsentError(null);
    if (email) {
      addConsentEmail(email);
      const key = `parkinson-guide-shown-${email}`;
      sessionStorage.setItem(key, "1");
    }
    setIsGuideOpen(true);
  };

  const recordingGuideSteps = [
    {
      title: t(locale, "parkinson", "recordingGuideStep1Title"),
      body: t(locale, "parkinson", "recordingGuideStep1Body"),
    },
    {
      title: t(locale, "parkinson", "recordingGuideStep2Title"),
      body: t(locale, "parkinson", "recordingGuideStep2Body"),
    },
    {
      title: t(locale, "parkinson", "recordingGuideStep3Title"),
      body: t(locale, "parkinson", "recordingGuideStep3Body"),
    },
    {
      title: t(locale, "parkinson", "recordingGuideStep4Title"),
      body: t(locale, "parkinson", "recordingGuideStep4Body"),
    },
  ];

  const recordingDos = [
    t(locale, "parkinson", "recordingDo1"),
    t(locale, "parkinson", "recordingDo2"),
    t(locale, "parkinson", "recordingDo3"),
  ];

  const recordingDonts = [
    t(locale, "parkinson", "recordingDont1"),
    t(locale, "parkinson", "recordingDont2"),
    t(locale, "parkinson", "recordingDont3"),
  ];

  const guidanceStatus = sessionRecording.isRecording
    ? t(locale, "parkinson", "recordingActiveHint")
    : voiceSession.addingTakeNumber !== null
      ? t(locale, "parkinson", "recordingProcessingHint")
      : t(locale, "parkinson", "recordingIdleHint");

  const sessionRecordingErrorMessage =
    sessionRecording.error === "recording_not_supported"
      ? t(locale, "parkinson", "recordingNotSupported")
      : sessionRecording.error === "microphone_permission_denied"
        ? t(locale, "parkinson", "micPermissionDenied")
        : sessionRecording.error === "audio_conversion_failed"
          ? t(locale, "parkinson", "audioConversionFailed")
          : sessionRecording.error === "recording_failed"
            ? t(locale, "parkinson", "recordingFailed")
            : null;

  return (
    <section id="main-content" className="space-y-8">
      <header>
        <h2 className="text-4xl font-extrabold text-foreground">{t(locale, "parkinson", "title")}</h2>
        <p className="mt-2 max-w-3xl text-muted-foreground">{t(locale, "parkinson", "subtitle")}</p>
      </header>

      {isConsentOpen ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-foreground/25 p-4" role="dialog" aria-modal="true" aria-labelledby="consent-title" aria-describedby="consent-description">
          <Card className="w-full max-w-xl">
            <h3 id="consent-title" className="text-2xl font-bold">{t(locale, "parkinson", "consentTitle")}</h3>
            <p id="consent-description" className="mt-2 text-sm text-muted-foreground">{t(locale, "parkinson", "consentDescription")}</p>

            <div className="mt-5 space-y-3">
              <label className="flex items-start gap-3 text-sm text-foreground">
                <input
                  ref={firstConsentRef}
                  type="checkbox"
                  checked={checks.data}
                  onChange={(event) => setChecks((prev) => ({ ...prev, data: event.target.checked }))}
                  className="mt-1 h-4 w-4"
                />
                <span>{t(locale, "parkinson", "consentData")}</span>
              </label>

              <label className="flex items-start gap-3 text-sm text-foreground">
                <input
                  type="checkbox"
                  checked={checks.validation}
                  onChange={(event) => setChecks((prev) => ({ ...prev, validation: event.target.checked }))}
                  className="mt-1 h-4 w-4"
                />
                <span>{t(locale, "parkinson", "consentValidation")}</span>
              </label>

              <label className="flex items-start gap-3 text-sm text-foreground">
                <input
                  type="checkbox"
                  checked={checks.service}
                  onChange={(event) => setChecks((prev) => ({ ...prev, service: event.target.checked }))}
                  className="mt-1 h-4 w-4"
                />
                <span>{t(locale, "parkinson", "consentService")}</span>
              </label>
            </div>

            {consentError ? (
              <p className="mt-4 text-sm font-semibold text-red-700" role="alert">
                {consentError}
              </p>
            ) : null}

            <div className="mt-6 flex gap-2">
              <Button variant="secondary" onClick={() => router.push("/dashboard")}>{t(locale, "parkinson", "decline")}</Button>
              <Button type="button" onClick={handleContinue}>{t(locale, "common", "continue")}</Button>
            </div>
          </Card>
        </div>
      ) : null}

      {isGuideOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-foreground/25 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="guide-title"
        >
          <Card className="my-auto w-full max-w-3xl">
            <div className="flex items-start justify-between gap-4">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">
                {t(locale, "parkinson", "recordingGuideEyebrow")}
              </p>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsGuideOpen(false)}
                aria-label={t(locale, "common", "close")}
              >
                ✕
              </Button>
            </div>
            <div className="mt-2 flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
              <div className="max-w-2xl">
                <h3 id="guide-title" className="text-2xl font-bold text-foreground">
                  {t(locale, "parkinson", "recordingGuideTitle")}
                </h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  {t(locale, "parkinson", "recordingGuideSubtitle")}
                </p>
              </div>
              <div className="rounded-2xl bg-primary/5 px-4 py-3 text-sm text-foreground">
                <p className="font-semibold text-primary">
                  {t(locale, "parkinson", "recordingDurationTitle")}
                </p>
                <p className="mt-1 text-muted-foreground">
                  {t(locale, "parkinson", "recordingDurationHint")}
                </p>
              </div>
            </div>

            <div className="mt-6 grid gap-4 lg:grid-cols-4">
              {recordingGuideSteps.map((step) => (
                <div key={step.title} className="rounded-2xl border border-surface-high bg-surface-lowest p-4">
                  <p className="text-sm font-semibold text-primary">{step.title}</p>
                  <p className="mt-2 text-sm text-muted-foreground">{step.body}</p>
                </div>
              ))}
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50/80 p-4">
                <p className="text-sm font-semibold text-emerald-900">
                  {t(locale, "parkinson", "recordingDoTitle")}
                </p>
                <ul className="mt-3 space-y-2 text-sm text-emerald-900/90">
                  {recordingDos.map((item) => (
                    <li key={item} className="flex gap-2">
                      <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-emerald-600" aria-hidden="true" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="rounded-2xl border border-rose-200 bg-rose-50/80 p-4">
                <p className="text-sm font-semibold text-rose-900">
                  {t(locale, "parkinson", "recordingDontTitle")}
                </p>
                <ul className="mt-3 space-y-2 text-sm text-rose-900/90">
                  {recordingDonts.map((item) => (
                    <li key={item} className="flex gap-2">
                      <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-rose-600" aria-hidden="true" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <Button onClick={() => setIsGuideOpen(false)}>
                {t(locale, "common", "close")}
              </Button>
            </div>
          </Card>
        </div>
      ) : null}

      <div className="surface-pane">
        <div
          role="button"
          tabIndex={0}
          className="mx-auto w-full max-w-5xl rounded-2xl border border-primary/10 bg-white/90 px-5 py-4 cursor-pointer transition-colors hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          onClick={() => setIsGuideOpen(true)}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setIsGuideOpen(true); } }}
        >
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">
                {t(locale, "parkinson", "recordingGuideEyebrow")}
              </p>
              <p className="mt-1 text-sm font-semibold text-foreground">
                {t(locale, "parkinson", "recordingGuideTitle")}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">{guidanceStatus}</p>
            </div>
            <span className="shrink-0 text-xs font-semibold text-primary">
              {t(locale, "parkinson", "recordingGuideOpen")} →
            </span>
          </div>
        </div>

        {/* ── Sesión multi-toma: único punto de entrada para la medición ── */}
        <Card className="mx-auto max-w-3xl border border-primary/10 bg-white/90 text-left backdrop-blur">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">
                {t(locale, "parkinson", "sessionPanelTitle")}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                {t(locale, "parkinson", "sessionPanelSubtitle")}
              </p>
            </div>
            {!voiceSession.session && accessToken && (
              <Button
                onClick={() => void voiceSession.startSession(3)}
                disabled={voiceSession.isCreating}
              >
                {voiceSession.isCreating
                  ? t(locale, "parkinson", "sessionStarting")
                  : t(locale, "parkinson", "sessionStart")}
              </Button>
            )}
          </div>

          {!accessToken && (
            <p className="mt-4 text-sm text-muted-foreground">
              {t(locale, "parkinson", "sessionAuthRequired")}
            </p>
          )}

          {voiceSession.error && (
            <p className="mt-4 text-sm font-semibold text-red-700" role="alert">
              {voiceSession.error}
            </p>
          )}

          {sessionRecordingErrorMessage && recordingForTake !== null && (
            <p className="mt-2 text-sm font-semibold text-red-700" role="alert">
              {sessionRecordingErrorMessage}
            </p>
          )}

          {voiceSession.session && (
            <div className="mt-6 space-y-4">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>Sesión #{voiceSession.session.id}</span>
                <span aria-hidden="true">·</span>
                <span className={`rounded-full px-2 py-0.5 font-semibold ${
                  voiceSession.session.status === "completed"
                    ? "bg-emerald-100 text-emerald-800"
                    : voiceSession.session.status === "failed"
                      ? "bg-red-100 text-red-800"
                      : "bg-yellow-100 text-yellow-800"
                }`}>
                  {voiceSession.session.status}
                </span>
                {voiceSession.isPolling && (
                  <span className="animate-pulse text-primary">actualizando...</span>
                )}
              </div>

              <div className="space-y-2">
                {Array.from({ length: voiceSession.session.max_takes }, (_, idx) => {
                  const takeNumber = idx + 1;
                  const existingTake = voiceSession.session?.takes.find((tk) => tk.take_number === takeNumber);
                  const isThisRecording = sessionRecording.isRecording && recordingForTake === takeNumber;
                  const isAddingThis = voiceSession.addingTakeNumber === takeNumber;
                  const isConfirmingRemove = confirmingRemoveTake === existingTake?.audio_record_id;
                  // Solo se permite borrar una toma en estado terminal de fallo.
                  // Borrar una toma aún en proceso provoca registros "processed"
                  // huérfanos (el pipeline en background termina tras el borrado).
                  const canDelete =
                    Boolean(existingTake) &&
                    isTakeFailed(existingTake!.status) &&
                    voiceSession.session?.status === "collecting";

                  return (
                    <div
                      key={takeNumber}
                      className="flex items-center justify-between rounded-xl border border-surface-high bg-surface-lowest p-3"
                    >
                      <div className="flex items-center gap-3">
                        <span className="w-16 text-sm font-semibold text-foreground">
                          {t(locale, "parkinson", "sessionTakeLabel")} {takeNumber}
                        </span>
                        {existingTake ? (
                          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                            isTakeInProgress(existingTake.status)
                              ? "bg-yellow-100 text-yellow-800"
                              : isTakeProcessed(existingTake.status)
                                ? "bg-emerald-100 text-emerald-800"
                                : "bg-red-100 text-red-800"
                          }`}>
                            {isTakeInProgress(existingTake.status)
                              ? t(locale, "parkinson", "sessionTakeProcessing")
                              : isTakeProcessed(existingTake.status)
                                ? t(locale, "parkinson", "sessionTakeProcessed")
                                : t(locale, "parkinson", "sessionTakeFailed")}
                          </span>
                        ) : (
                          <span className="rounded-full bg-surface-high px-2 py-0.5 text-xs text-muted-foreground">
                            {t(locale, "parkinson", "sessionTakePending")}
                          </span>
                        )}
                        {isThisRecording && (
                          <span className="font-mono text-xs text-primary">
                            {formatElapsed(sessionRecording.elapsedSeconds)}
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        {canDelete && (
                          isConfirmingRemove ? (
                            <div className="flex items-center gap-1">
                              <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => setConfirmingRemoveTake(null)}
                              >
                                {t(locale, "common", "cancel")}
                              </Button>
                              <Button
                                size="sm"
                                onClick={() => {
                                  void voiceSession.removeTake(existingTake!.audio_record_id);
                                  setConfirmingRemoveTake(null);
                                }}
                              >
                                {t(locale, "parkinson", "sessionTakeRemoveConfirm")}
                              </Button>
                            </div>
                          ) : (
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={() => setConfirmingRemoveTake(existingTake!.audio_record_id)}
                            >
                              {t(locale, "parkinson", "sessionTakeRemove")}
                            </Button>
                          )
                        )}

                        {!existingTake && voiceSession.session?.status === "collecting" && (
                          isThisRecording ? (
                            <Button
                              size="sm"
                              onClick={async () => {
                                const blob = await sessionRecording.stopRecording();
                                if (blob) {
                                  await voiceSession.addTake(blob, takeNumber, `take_${takeNumber}.wav`, "microphone");
                                }
                                setRecordingForTake(null);
                              }}
                            >
                              {t(locale, "parkinson", "stop")}
                            </Button>
                          ) : (
                            <>
                              <Button
                                size="sm"
                                disabled={sessionRecording.isRecording || isAddingThis}
                                onClick={async () => {
                                  setRecordingForTake(takeNumber);
                                  await sessionRecording.startRecording();
                                }}
                              >
                                {isAddingThis
                                  ? t(locale, "parkinson", "uploading")
                                  : t(locale, "parkinson", "sessionTakeRecord")}
                              </Button>
                              <div>
                                <input
                                  type="file"
                                  accept=".wav,.mp3,.ogg,.webm,.m4a,audio/*"
                                  className="hidden"
                                  id={`session-take-upload-${takeNumber}`}
                                  onChange={async (e) => {
                                    const file = e.target.files?.[0];
                                    if (!file) return;
                                    e.target.value = "";
                                    await voiceSession.addTake(file, takeNumber, file.name, "upload");
                                  }}
                                  disabled={sessionRecording.isRecording || isAddingThis}
                                />
                                <Button
                                  size="sm"
                                  variant="secondary"
                                  disabled={sessionRecording.isRecording || isAddingThis}
                                  onClick={() =>
                                    document.getElementById(`session-take-upload-${takeNumber}`)?.click()
                                  }
                                >
                                  {t(locale, "parkinson", "sessionTakeUpload")}
                                </Button>
                              </div>
                            </>
                          )
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {voiceSession.session.status === "collecting" && (
                <div className="space-y-2 pt-2">
                  {validSessionTakes < 2 && (
                    <p className="text-xs text-amber-600">
                      {t(locale, "parkinson", "sessionInsufficientTakes")}
                    </p>
                  )}
                  <Button
                    className="w-full"
                    onClick={() => void voiceSession.analyze()}
                    disabled={validSessionTakes < 2 || voiceSession.isAnalyzing || voiceSession.isPolling}
                  >
                    {voiceSession.isAnalyzing
                      ? t(locale, "parkinson", "sessionAnalyzing")
                      : t(locale, "parkinson", "sessionAnalyze")}
                  </Button>
                </div>
              )}

              {voiceSession.session.status === "failed" && (
                <div className="space-y-2 pt-2">
                  <p className="text-xs text-red-600">
                    {t(locale, "parkinson", "sessionFailedHint")}
                  </p>
                  <Button
                    className="w-full"
                    variant="secondary"
                    onClick={() => void voiceSession.reopen()}
                  >
                    {t(locale, "parkinson", "sessionReopen")}
                  </Button>
                </div>
              )}

              {voiceSession.result && (
                <div className="mt-4 space-y-4">
                  <div className="rounded-2xl border border-primary/10 bg-primary/5 p-5 space-y-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                      {t(locale, "parkinson", "sessionResultTitle")}
                    </p>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="rounded-xl bg-white/80 p-3 shadow-sm">
                        <p className="text-xs text-muted-foreground">
                          {t(locale, "parkinson", "confidenceLabel")}
                        </p>
                        <p className="mt-1 text-2xl font-bold text-foreground">
                          {(voiceSession.result.probability * 100).toFixed(1)}%
                        </p>
                      </div>
                      <div className="rounded-xl bg-white/80 p-3 shadow-sm">
                        <p className="text-xs text-muted-foreground">
                          {t(locale, "parkinson", "sessionConfidenceLabel")}
                        </p>
                        <p className="mt-1 text-2xl font-bold text-foreground">
                          {(voiceSession.result.session_confidence * 100).toFixed(1)}%
                        </p>
                      </div>
                    </div>
                    <p className="text-sm font-semibold text-foreground">
                      {voiceSession.result.message}
                    </p>
                  </div>

                  <div className="rounded-2xl border border-primary/10 bg-primary/5 p-5 text-left">
                    <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                      {t(locale, "parkinson", "biomarkerPanelTitle")}
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {t(locale, "parkinson", "biomarkerPanelHint")}
                    </p>

                    <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                      {biomarkerCards.map((item) => (
                        <div key={item.key} className="rounded-xl bg-white/80 p-4 shadow-sm">
                          <p className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
                            {t(locale, "parkinson", "measureLabel")}
                          </p>
                          <p className="mt-2 text-sm font-semibold text-foreground">{item.label}</p>
                          <p className="mt-2 text-2xl font-bold text-foreground">
                            {typeof item.value === "number"
                              ? `${item.value.toFixed(item.decimals)}${item.unit ? ` ${item.unit}` : ""}`
                              : t(locale, "common", "notAvailable")}
                          </p>
                          <p className="mt-2 text-xs text-muted-foreground" title={item.description}>
                            {item.description}
                          </p>
                        </div>
                      ))}
                    </div>

                    <div className="mt-4 rounded-xl bg-white/80 p-4 shadow-sm">
                      <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
                        {t(locale, "parkinson", "modelFeaturesTitle")}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {t(locale, "parkinson", "modelFeaturesHint")}
                      </p>
                      <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                        {Object.entries(aggregatedFeatures ?? {}).map(([key, value]) => (
                          <div key={key} className="flex items-baseline justify-between gap-2 rounded-lg bg-white/60 px-3 py-2">
                            <span className="text-xs font-semibold text-muted-foreground">{key}</span>
                            <span className="text-sm font-bold text-foreground">
                              {typeof value === "number" ? value.toFixed(4) : String(value)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  <Button variant="secondary" onClick={voiceSession.reset}>
                    {t(locale, "parkinson", "sessionReset")}
                  </Button>
                </div>
              )}

              {!voiceSession.result && (
                <div className="pt-1">
                  <Button variant="ghost" size="sm" onClick={voiceSession.reset}>
                    {t(locale, "parkinson", "sessionReset")}
                  </Button>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>

    </section>
  );
}
