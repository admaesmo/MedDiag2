"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Mic, Play } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/atoms/button";
import { Card } from "@/components/atoms/card";
import { useSessionState } from "@/features/auth/use-session";
import { useAudioRecording } from "@/features/parkinson/use-audio-recording";
import { useParkinsonPrediction } from "@/features/parkinson/mutations";
import { useVoiceSession } from "@/features/parkinson/use-voice-session";
import {
  extractVoiceBiomarkersMultipart,
  getAudioFeatures,
  getMyAudio,
  isMockApiEnabled,
  type VoiceBiomarkerExtractionResponse,
  uploadAudioMultipart,
} from "@/lib/api";
import { useUiStore } from "@/stores/ui-store";
import { t } from "@/lib/i18n";

function formatElapsed(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return [hours, minutes, seconds].map((value) => String(value).padStart(2, "0")).join(":");
}

export default function ParkinsonPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const locale = useUiStore((state) => state.locale);
  const consentAccepted = useUiStore((state) => state.parkinsonConsentAccepted);
  const setConsentAccepted = useUiStore((state) => state.setParkinsonConsentAccepted);
  const [isUploadingAudio, setIsUploadingAudio] = useState(false);
  const [isExtractingBiomarkers, setIsExtractingBiomarkers] = useState(false);
  const [audioUploadMessage, setAudioUploadMessage] = useState<string | null>(null);
  const [audioUploadError, setAudioUploadError] = useState<string | null>(null);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [biomarkerMessage, setBiomarkerMessage] = useState<string | null>(null);
  const [biomarkerError, setBiomarkerError] = useState<string | null>(null);
  const [biomarkerResponse, setBiomarkerResponse] = useState<VoiceBiomarkerExtractionResponse | null>(null);
  const [previewFeatures, setPreviewFeatures] = useState<Record<string, number> | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [previewConsentChecked, setPreviewConsentChecked] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [consentError, setConsentError] = useState<string | null>(null);
  const [recordingForTake, setRecordingForTake] = useState<number | null>(null);
  const [confirmingRemoveTake, setConfirmingRemoveTake] = useState<number | null>(null);
  const [isGuideOpen, setIsGuideOpen] = useState(consentAccepted);
  const [checks, setChecks] = useState({
    data: false,
    validation: false,
    service: false,
  });
  const firstConsentRef = useRef<HTMLInputElement>(null);
  const { accessToken, email } = useSessionState();
  const recording = useAudioRecording();
  const sessionRecording = useAudioRecording();
  const prediction = useParkinsonPrediction(accessToken, email);
  const voiceSession = useVoiceSession(accessToken);
  const mockApiEnabled = isMockApiEnabled();
  const audioQuery = useQuery({
    queryKey: ["audio", "me", "parkinson"],
    enabled: Boolean(accessToken) && !mockApiEnabled,
    queryFn: () => getMyAudio(accessToken as string),
    refetchInterval: (query) => {
      const hasProcessing = query.state.data?.items?.some((item) => item.status === "processing");
      return hasProcessing ? 2000 : false;
    },
  });
  const latestAudio = audioQuery.data?.items?.[0] ?? null;
  const isAudioReady = Boolean(
    latestAudio &&
      (latestAudio.is_ready_for_inference ?? ["processed", "transcribed"].includes(latestAudio.status)),
  );
  const isAudioProcessing = latestAudio?.status === "processing";
  const canRunInference = mockApiEnabled || (Boolean(accessToken) && isAudioReady && !isAudioProcessing);
  const elapsedLabel = formatElapsed(recording.elapsedSeconds);

  const biomarkerCards = [
    {
      key: "pitch_mean",
      label: t(locale, "parkinson", "biomarkerPitchMean"),
      description: t(locale, "parkinson", "biomarkerPitchMeanInfo"),
      value: biomarkerResponse?.biomarkers.pitch_mean,
      unit: "Hz",
      decimals: 2,
    },
    {
      key: "pitch_min",
      label: t(locale, "parkinson", "biomarkerPitchMin"),
      description: t(locale, "parkinson", "biomarkerPitchMinInfo"),
      value: biomarkerResponse?.biomarkers.pitch_min,
      unit: "Hz",
      decimals: 2,
    },
    {
      key: "pitch_max",
      label: t(locale, "parkinson", "biomarkerPitchMax"),
      description: t(locale, "parkinson", "biomarkerPitchMaxInfo"),
      value: biomarkerResponse?.biomarkers.pitch_max,
      unit: "Hz",
      decimals: 2,
    },
    {
      key: "jitter_local",
      label: t(locale, "parkinson", "biomarkerJitterLocal"),
      description: t(locale, "parkinson", "biomarkerJitterLocalInfo"),
      value: biomarkerResponse?.biomarkers.jitter_local,
      unit: "",
      decimals: 6,
    },
    {
      key: "shimmer_local",
      label: t(locale, "parkinson", "biomarkerShimmerLocal"),
      description: t(locale, "parkinson", "biomarkerShimmerLocalInfo"),
      value: biomarkerResponse?.biomarkers.shimmer_local,
      unit: "",
      decimals: 6,
    },
    {
      key: "hnr_mean",
      label: t(locale, "parkinson", "biomarkerHnrMean"),
      description: t(locale, "parkinson", "biomarkerHnrMeanInfo"),
      value: biomarkerResponse?.biomarkers.hnr_mean,
      unit: "dB",
      decimals: 2,
    },
  ];

  const isConsentOpen = !consentAccepted;

  useEffect(() => {
    if (isConsentOpen) {
      firstConsentRef.current?.focus();
    }
  }, [isConsentOpen]);

  const canProceed = checks.data && checks.validation && checks.service;

  const validSessionTakes = voiceSession.session?.takes.filter((tk) => tk.status === "processed").length ?? 0;
  const activePrediction = prediction.data ?? null;
  const result = useMemo(() => {
    if (!activePrediction) {
      return null;
    }
    return `${(activePrediction.probability * 100).toFixed(2)}%`;
  }, [activePrediction]);

  const handleContinue = () => {
    if (!canProceed) {
      setConsentError(t(locale, "parkinson", "consentRequired"));
      return;
    }

    setConsentError(null);
    setConsentAccepted(true);
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

  const guidanceStatus = recording.isRecording
    ? t(locale, "parkinson", "recordingActiveHint")
    : isExtractingBiomarkers || isUploadingAudio || isUploadingFile
      ? t(locale, "parkinson", "recordingProcessingHint")
      : t(locale, "parkinson", "recordingIdleHint");

  // ── Helper: upload del blob después de autorización ──
  const uploadBlobAfterConsent = async (
    blob: Blob,
    fileName: string,
    sourceType: string,
  ) => {
    if (!accessToken && !mockApiEnabled) {
      setAudioUploadError(t(locale, "parkinson", "authRequiredForUpload"));
      return;
    }

    try {
      setIsUploadingAudio(true);
      const response = await uploadAudioMultipart(accessToken ?? "", blob, fileName, {
        sourceType,
        languageCode: locale.split("-")[0],
      });
      setAudioUploadMessage(`${t(locale, "parkinson", "uploadSuccess")}: #${response.audio_id}`);
      queryClient.invalidateQueries({ queryKey: ["audio", "me"] });
      queryClient.invalidateQueries({ queryKey: ["audio", "me", "parkinson"] });
    } catch {
      setAudioUploadMessage(null);
      setAudioUploadError(t(locale, "parkinson", "uploadError"));
    } finally {
      setIsUploadingAudio(false);
    }
  };

  // ── Handle: grabar audio ──
  const handleRecordButtonClick = async () => {
    if (isConsentOpen || isUploadingAudio || isExtractingBiomarkers) {
      return;
    }

    if (!recording.isRecording) {
      setAudioUploadMessage(null);
      setAudioUploadError(null);
      setBiomarkerMessage(null);
      setBiomarkerError(null);
      setBiomarkerResponse(null);
      prediction.reset();
      recording.resetRecording();
      await recording.startRecording();
      return;
    }

    const audioBlob = await recording.stopRecording();
    if (!audioBlob || audioBlob.size === 0) {
      setAudioUploadError(t(locale, "parkinson", "noAudioCaptured"));
      return;
    }

    setBiomarkerError(null);
    setBiomarkerMessage(null);
    setAudioUploadError(null);
    setAudioUploadMessage(null);
    prediction.reset();

    const extension = audioBlob.type.includes("webm")
      ? "webm"
      : audioBlob.type.includes("mp4")
        ? "m4a"
        : audioBlob.type.includes("ogg")
          ? "ogg"
          : "wav";
    const uploadFileName = `parkinson-sample.${extension}`;

    // 1. Extraer biomarcadores
    let biomarkers: VoiceBiomarkerExtractionResponse;
    try {
      setIsExtractingBiomarkers(true);
      biomarkers = await extractVoiceBiomarkersMultipart(audioBlob, uploadFileName);
      setBiomarkerResponse(biomarkers);
      setBiomarkerMessage(t(locale, "parkinson", "biomarkerSuccess"));
    } catch (error) {
      setBiomarkerResponse(null);
      setBiomarkerMessage(null);
      setBiomarkerError(
        error instanceof Error ? error.message : t(locale, "parkinson", "biomarkerExtractError"),
      );
      setIsExtractingBiomarkers(false);
      return;
    } finally {
      setIsExtractingBiomarkers(false);
    }

    // 2. Mostrar modal de pre-análisis con los features completos
    const features = biomarkers.parkinson_model_input.features;
    setPreviewFeatures(features);
    setPreviewConsentChecked(false);
    setPreviewError(null);
    setIsPreviewOpen(true);

    // Guardamos en una ref para que handleConfirmInference lo use
    pendingRecordRef.current = { blob: audioBlob, fileName: uploadFileName, sourceType: "microphone" };
  };

  // Ref para pasar datos de grabación/upload al confirmar
  const pendingRecordRef = useRef<{ blob: Blob; fileName: string; sourceType: string } | null>(null);
  const pendingUploadRef = useRef<{ file: File; fileName: string } | null>(null);

  // ── Handle: subir archivo ──
  const handleFileSelected = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Reset file input so the same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }

    // Validate file type
    const validTypes = ["audio/wav", "audio/mp3", "audio/mpeg", "audio/ogg", "audio/webm", "audio/mp4", "audio/x-m4a", "audio/x-wav"];
    const isWav = file.name.toLowerCase().endsWith(".wav");
    const isMp3 = file.name.toLowerCase().endsWith(".mp3");
    const isOgg = file.name.toLowerCase().endsWith(".ogg");
    const isWebm = file.name.toLowerCase().endsWith(".webm");
    const isM4a = file.name.toLowerCase().endsWith(".m4a");
    if (!isWav && !isMp3 && !isOgg && !isWebm && !isM4a && !validTypes.includes(file.type)) {
      setAudioUploadError(t(locale, "parkinson", "invalidFileType"));
      return;
    }

    // Validate file size (25 MB max)
    const maxSize = 25 * 1024 * 1024;
    if (file.size > maxSize) {
      setAudioUploadError(t(locale, "parkinson", "fileTooLarge"));
      return;
    }

    setAudioUploadError(null);
    setAudioUploadMessage(null);
    setBiomarkerError(null);
    setBiomarkerMessage(null);
    setBiomarkerResponse(null);
    prediction.reset();

    const extension = file.name.split(".").pop() || "wav";
    const uploadFileName = `uploaded-${Date.now()}.${extension}`;

    // 1. Extraer biomarcadores
    let biomarkers: VoiceBiomarkerExtractionResponse;
    try {
      setIsUploadingFile(true);
      biomarkers = await extractVoiceBiomarkersMultipart(file, uploadFileName);
      setBiomarkerResponse(biomarkers);
      setBiomarkerMessage(t(locale, "parkinson", "biomarkerSuccess"));
    } catch (error) {
      setBiomarkerResponse(null);
      setBiomarkerMessage(null);
      setBiomarkerError(
        error instanceof Error ? error.message : t(locale, "parkinson", "biomarkerExtractError"),
      );
      setIsUploadingFile(false);
      return;
    } finally {
      setIsUploadingFile(false);
    }

    // 2. Mostrar modal de pre-análisis
    const features = biomarkers.parkinson_model_input.features;
    setPreviewFeatures(features);
    setPreviewConsentChecked(false);
    setPreviewError(null);
    setIsPreviewOpen(true);

    // Guardamos ref para subir después si confirma
    pendingUploadRef.current = { file, fileName: uploadFileName };
  };

  const recordingErrorMessage =
    recording.error === "recording_not_supported"
      ? t(locale, "parkinson", "recordingNotSupported")
      : recording.error === "microphone_permission_denied"
        ? t(locale, "parkinson", "micPermissionDenied")
        : recording.error === "audio_conversion_failed"
          ? t(locale, "parkinson", "audioConversionFailed")
        : recording.error === "recording_failed"
          ? t(locale, "parkinson", "recordingFailed")
          : null;

  // ── Handle: botón "Run Inference" (desde audio ya subido) ──
  const handleInferenceClick = async () => {
    if (!accessToken) {
      setAudioUploadError(t(locale, "parkinson", "authRequiredForUpload"));
      return;
    }

    if (!latestAudio) {
      setAudioUploadError(t(locale, "parkinson", "noAudioForInference"));
      return;
    }

    if (!isAudioReady || isAudioProcessing) {
      setAudioUploadError(t(locale, "parkinson", "audioStillProcessing"));
      return;
    }

    try {
      setAudioUploadError(null);
      setPreviewError(null);
      setPreviewConsentChecked(false);
      setIsLoadingPreview(true);
      const response = await getAudioFeatures(accessToken, latestAudio.id);
      setPreviewFeatures(response.features);
      setIsPreviewOpen(true);
    } catch {
      setAudioUploadError(t(locale, "parkinson", "featureLoadError"));
    } finally {
      setIsLoadingPreview(false);
    }
  };

  // ── Handle: confirmar inferencia desde el modal ──
  const handleConfirmInference = () => {
    if (!previewFeatures) {
      setPreviewError(t(locale, "parkinson", "previewNoFeatures"));
      return;
    }

    if (!previewConsentChecked) {
      setPreviewError(t(locale, "parkinson", "previewConsentRequired"));
      return;
    }

    setPreviewError(null);

    // Ejecutar inferencia
    prediction.mutate(previewFeatures);

    // Si hay una grabación pendiente por subir, subirla
    if (pendingRecordRef.current) {
      const { blob, fileName, sourceType } = pendingRecordRef.current;
      uploadBlobAfterConsent(blob, fileName, sourceType);
      pendingRecordRef.current = null;
    }

    // Si hay un archivo pendiente por subir, subirlo
    if (pendingUploadRef.current) {
      const { file, fileName } = pendingUploadRef.current;
      if (accessToken || mockApiEnabled) {
        (async () => {
          try {
            setIsUploadingFile(true);
            const response = await uploadAudioMultipart(accessToken ?? "", file, fileName, {
              sourceType: "upload",
              languageCode: locale.split("-")[0],
            });
            setAudioUploadMessage(`${t(locale, "parkinson", "uploadAudioSuccess")}: #${response.audio_id}`);
            queryClient.invalidateQueries({ queryKey: ["audio", "me"] });
            queryClient.invalidateQueries({ queryKey: ["audio", "me", "parkinson"] });
          } catch {
            setAudioUploadMessage(null);
            setAudioUploadError(t(locale, "parkinson", "uploadAudioError"));
          } finally {
            setIsUploadingFile(false);
          }
        })();
      }
      pendingUploadRef.current = null;
    }

    setIsPreviewOpen(false);
  };

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

      {isPreviewOpen ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-foreground/25 p-4" role="dialog" aria-modal="true" aria-labelledby="preview-title">
          <Card className="w-full max-w-3xl">
            <h3 id="preview-title" className="text-2xl font-bold">{t(locale, "parkinson", "previewTitle")}</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              {t(locale, "parkinson", "previewDescription")}
            </p>

            <div className="mt-4 max-h-80 overflow-y-auto rounded-xl border border-primary/10 bg-primary/5 p-3">
              <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                {Object.entries(previewFeatures ?? {}).map(([key, value]) => (
                  <div key={key} className="flex items-baseline justify-between gap-2 rounded-lg bg-white/80 px-3 py-2">
                    <span className="text-xs font-semibold text-muted-foreground">{key}</span>
                    <span className="text-sm font-bold text-foreground">
                      {typeof value === "number" ? value.toFixed(6) : String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <label className="mt-4 flex items-start gap-3 text-sm text-foreground">
              <input
                type="checkbox"
                checked={previewConsentChecked}
                onChange={(event) => setPreviewConsentChecked(event.target.checked)}
                className="mt-1 h-4 w-4"
              />
              <span>{t(locale, "parkinson", "previewConsentLabel")}</span>
            </label>

            {previewError ? (
              <p className="mt-3 text-sm font-semibold text-red-700" role="alert">
                {previewError}
              </p>
            ) : null}

            <div className="mt-6 flex gap-2">
              <Button
                variant="secondary"
                onClick={() => {
                  setIsPreviewOpen(false);
                  setPreviewConsentChecked(false);
                  setPreviewError(null);
                  pendingRecordRef.current = null;
                  pendingUploadRef.current = null;
                }}
              >
                {t(locale, "parkinson", "previewCancel")}
              </Button>
              <Button type="button" onClick={handleConfirmInference} disabled={prediction.isPending}>
                {prediction.isPending ? t(locale, "parkinson", "previewLoading") : t(locale, "parkinson", "previewConfirm")}
              </Button>
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

        <Card className="mx-auto max-w-3xl bg-white/90 text-center backdrop-blur">
          <div className="relative mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-primary text-white">
            {recording.isRecording ? <span className="absolute inset-0 rounded-2xl bg-primary/30 animate-pulse-ring" aria-hidden="true" /> : null}
            <Mic className="relative h-9 w-9" />
          </div>

          <h3 className="text-3xl font-bold">{t(locale, "parkinson", "recordTitle")}</h3>
          <p className="mt-2 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">{t(locale, "parkinson", "recordSubtitle")}</p>

          <div className="mx-auto mt-8 flex w-full max-w-md items-end justify-center gap-1 rounded-xl bg-primary/5 p-4">
            {[18, 36, 28, 54, 24, 44, 38, 50, 26, 32].map((height, index) => (
              <span key={`audio-bar-${index}`} className="w-1 rounded-full bg-primary/65" style={{ height }} />
            ))}
          </div>

          <div className="mt-8 flex flex-col items-center gap-4 sm:flex-row sm:flex-wrap sm:justify-center">
            <div className="flex items-center gap-3">
              <Button
                size="lg"
                onClick={handleRecordButtonClick}
                disabled={isConsentOpen || isUploadingAudio || isExtractingBiomarkers || isUploadingFile}
              >
                <Play className="mr-2 h-4 w-4" />
                {isExtractingBiomarkers
                  ? t(locale, "parkinson", "extractingBiomarkers")
                  : isUploadingAudio
                  ? t(locale, "parkinson", "uploading")
                  : recording.isRecording
                    ? t(locale, "parkinson", "stop")
                    : t(locale, "parkinson", "start")}
              </Button>
              <Button
                variant="secondary"
                size="lg"
                onClick={handleInferenceClick}
                disabled={!canRunInference || prediction.isPending || isConsentOpen || isLoadingPreview}
              >
                {prediction.isPending
                  ? t(locale, "parkinson", "processing")
                  : isLoadingPreview
                    ? t(locale, "parkinson", "previewLoading")
                    : isAudioProcessing
                    ? t(locale, "parkinson", "audioProcessing")
                    : t(locale, "parkinson", "runInference")}
              </Button>
            </div>
            <div className="flex items-center gap-2">
              <input
                ref={fileInputRef}
                type="file"
                accept=".wav,.mp3,.ogg,.webm,.m4a,audio/*"
                className="hidden"
                onChange={handleFileSelected}
              />
              <Button
                variant="ghost"
                size="lg"
                onClick={() => fileInputRef.current?.click()}
                disabled={isConsentOpen || isUploadingFile || recording.isRecording}
              >
                {isUploadingFile
                  ? t(locale, "parkinson", "uploading")
                  : t(locale, "parkinson", "uploadAudioFile")}
              </Button>
            </div>
          </div>

          {!mockApiEnabled && latestAudio ? (
            <p className="mt-2 text-xs text-muted-foreground" role="status" aria-live="polite">
              {isAudioProcessing
                ? t(locale, "parkinson", "audioStillProcessing")
                : isAudioReady
                  ? t(locale, "parkinson", "audioReadyForInference")
                  : t(locale, "parkinson", "noAudioForInference")}
            </p>
          ) : null}

          <p className="mt-4 text-sm text-muted-foreground">
            {t(locale, "parkinson", "elapsed")}: <span className="font-headline text-lg text-foreground">{elapsedLabel}</span>
          </p>

          <div aria-live="polite" className="mt-6 min-h-[28px] text-sm font-semibold text-primary">
            {result ? (
              <div>
                <p>{`${t(locale, "parkinson", "confidenceLabel")}: ${result}`}</p>
                {activePrediction?.message ? (
                  <p className="mt-1 text-xs font-medium text-muted-foreground">
                    {activePrediction.message}
                  </p>
                ) : null}
              </div>
            ) : null}
            {prediction.isError ? t(locale, "parkinson", "inferenceError") : null}
          </div>

          {recordingErrorMessage ? (
            <p className="mt-3 text-sm font-semibold text-red-700" role="alert">
              {recordingErrorMessage}
            </p>
          ) : null}

          {biomarkerError ? (
            <p className="mt-2 text-sm font-semibold text-red-700" role="alert">
              {biomarkerError}
            </p>
          ) : null}

          {biomarkerMessage ? (
            <p className="mt-2 text-sm font-semibold text-emerald-700" role="status">
              {biomarkerMessage}
            </p>
          ) : null}

          {audioUploadError ? (
            <p className="mt-2 text-sm font-semibold text-red-700" role="alert">
              {audioUploadError}
            </p>
          ) : null}

          {audioUploadMessage ? (
            <p className="mt-2 text-sm font-semibold text-emerald-700" role="status">
              {audioUploadMessage}
            </p>
          ) : null}

          {biomarkerResponse ? (
            <div className="mt-8 rounded-2xl border border-primary/10 bg-primary/5 p-5 text-left">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                    {t(locale, "parkinson", "biomarkerPanelTitle")}
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {t(locale, "parkinson", "biomarkerPanelHint")}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                    {t(locale, "parkinson", "biomarkerMetadataLabel")}
                  </p>
                  <p className="mt-1 text-sm text-foreground">
                    {biomarkerResponse.audio.sample_rate_hz} Hz | {biomarkerResponse.audio.channels} ch | {biomarkerResponse.audio.normalized_format.toUpperCase()} | {biomarkerResponse.audio.duration_seconds.toFixed(2)} s
                  </p>
                </div>
              </div>

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
                  {t(locale, "parkinson", "directModelResultLabel")}
                </p>
                <p className="mt-2 text-sm text-foreground">
                  {t(locale, "common", "model")}: {biomarkerResponse.parkinson_model_input.model_name}
                </p>
                <p className="mt-1 text-sm text-foreground">
                  {t(locale, "parkinson", "modelVectorCoverageLabel")}: {biomarkerResponse.parkinson_model_input.feature_count}/
                  {biomarkerResponse.parkinson_model_input.required_feature_count}
                </p>
                <p className="mt-2 text-sm font-semibold text-foreground">
                  {`${t(locale, "parkinson", "confidenceLabel")}: ${(biomarkerResponse.parkinson_inference.probability * 100).toFixed(2)}%`}
                </p>
                <p className="mt-1 text-sm text-foreground">
                  {biomarkerResponse.parkinson_inference.message}
                </p>
                <p className="mt-2 text-xs text-muted-foreground">
                  {biomarkerResponse.parkinson_model_input.note}
                </p>
                <p className="mt-2 text-xs text-muted-foreground">
                  {biomarkerResponse.parkinson_model_bridge.note}
                </p>
              </div>

              <div className="mt-4 rounded-xl bg-white/80 p-4 shadow-sm">
                <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
                  {t(locale, "parkinson", "modelFeaturesTitle")}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {t(locale, "parkinson", "modelFeaturesHint")}
                </p>
                <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                  {Object.entries(biomarkerResponse.parkinson_model_input.features).map(([key, value]) => (
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
          ) : null}
        </Card>

        {/* ── Sesión multi-toma ── */}
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

          {sessionRecording.error === "microphone_permission_denied" && recordingForTake !== null && (
            <p className="mt-2 text-sm font-semibold text-red-700" role="alert">
              {t(locale, "parkinson", "micPermissionDenied")}
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
                  const canDelete =
                    Boolean(existingTake) &&
                    existingTake?.status !== "processed" &&
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
                            existingTake.status === "processing"
                              ? "bg-yellow-100 text-yellow-800"
                              : existingTake.status === "processed"
                                ? "bg-emerald-100 text-emerald-800"
                                : "bg-red-100 text-red-800"
                          }`}>
                            {existingTake.status === "processing"
                              ? t(locale, "parkinson", "sessionTakeProcessing")
                              : existingTake.status === "processed"
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

              {voiceSession.result && (
                <div className="mt-4 rounded-2xl border border-primary/10 bg-primary/5 p-5 space-y-3">
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
