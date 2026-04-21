"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Mic, Play } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/atoms/button";
import { Card } from "@/components/atoms/card";
import { Input } from "@/components/atoms/input";
import { useSessionState } from "@/features/auth/use-session";
import { useAudioRecording } from "@/features/parkinson/use-audio-recording";
import { parkinsonTestFeaturePreset, useParkinsonPrediction } from "@/features/parkinson/mutations";
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

const editableFeatureKeys = [
  "MDVP:RAP",
  "MDVP:PPQ",
  "Jitter:DDP",
  "MDVP:Shimmer(dB)",
  "Shimmer:APQ3",
  "Shimmer:APQ5",
  "MDVP:APQ",
  "Shimmer:DDA",
  "NHR",
  "HNR",
  "RPDE",
  "DFA",
  "D2",
  "PPE",
] as const;

type EditableFeatureKey = (typeof editableFeatureKeys)[number];

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
  const [biomarkerMessage, setBiomarkerMessage] = useState<string | null>(null);
  const [biomarkerError, setBiomarkerError] = useState<string | null>(null);
  const [biomarkerResponse, setBiomarkerResponse] = useState<VoiceBiomarkerExtractionResponse | null>(null);
  const [consentError, setConsentError] = useState<string | null>(null);
  const [checks, setChecks] = useState({
    data: false,
    validation: false,
    service: false,
  });
  const [testFeatureValues, setTestFeatureValues] = useState<Record<EditableFeatureKey, number>>({
    ...parkinsonTestFeaturePreset,
  });
  const [jsonEditorValue, setJsonEditorValue] = useState(
    JSON.stringify(parkinsonTestFeaturePreset, null, 2),
  );
  const [jsonEditorMessage, setJsonEditorMessage] = useState<string | null>(null);
  const [jsonEditorError, setJsonEditorError] = useState<string | null>(null);
  const firstConsentRef = useRef<HTMLInputElement>(null);
  const { accessToken, email } = useSessionState();
  const recording = useAudioRecording();
  const prediction = useParkinsonPrediction(accessToken, email);
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
  const showTestPanel = mockApiEnabled || process.env.NODE_ENV !== "production";
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

  const updateFeatureValue = (key: EditableFeatureKey, value: string) => {
    const parsed = Number(value);
    setTestFeatureValues((prev) => ({
      ...prev,
      [key]: Number.isFinite(parsed) ? parsed : prev[key],
    }));
  };

  const applyJsonValues = () => {
    try {
      const parsed = JSON.parse(jsonEditorValue) as Partial<Record<EditableFeatureKey, unknown>>;
      const next = { ...testFeatureValues };

      for (const key of editableFeatureKeys) {
        if (parsed[key] === undefined) {
          continue;
        }

        const num = Number(parsed[key]);
        if (!Number.isFinite(num)) {
          throw new Error("invalid");
        }

        next[key] = num;
      }

      setTestFeatureValues(next);
      setJsonEditorError(null);
      setJsonEditorMessage(t(locale, "parkinson", "jsonApplied"));
    } catch {
      setJsonEditorMessage(null);
      setJsonEditorError(t(locale, "parkinson", "jsonInvalid"));
    }
  };

  useEffect(() => {
    setJsonEditorValue(JSON.stringify(testFeatureValues, null, 2));
  }, [testFeatureValues]);

  const result = useMemo(() => {
    if (!prediction.data) {
      return null;
    }
    return `${(prediction.data.probability * 100).toFixed(2)}%`;
  }, [prediction.data]);

  const handleContinue = () => {
    if (!canProceed) {
      setConsentError(t(locale, "parkinson", "consentRequired"));
      return;
    }

    setConsentError(null);
    setConsentAccepted(true);
  };

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

    const extension = audioBlob.type.includes("webm")
      ? "webm"
      : audioBlob.type.includes("mp4")
        ? "m4a"
        : audioBlob.type.includes("ogg")
          ? "ogg"
          : "wav";
    const uploadFileName = `parkinson-sample.${extension}`;

    try {
      setIsExtractingBiomarkers(true);
      const biomarkers = await extractVoiceBiomarkersMultipart(audioBlob, uploadFileName);
      setBiomarkerResponse(biomarkers);
      setBiomarkerMessage(t(locale, "parkinson", "biomarkerSuccess"));
    } catch (error) {
      setBiomarkerResponse(null);
      setBiomarkerMessage(null);
      setBiomarkerError(
        error instanceof Error ? error.message : t(locale, "parkinson", "biomarkerExtractError"),
      );
    } finally {
      setIsExtractingBiomarkers(false);
    }

    if (!accessToken && !mockApiEnabled) {
      setAudioUploadError(t(locale, "parkinson", "authRequiredForUpload"));
      return;
    }

    try {
      setIsUploadingAudio(true);

      const response = await uploadAudioMultipart(accessToken ?? "", audioBlob, uploadFileName, {
        sourceType: "microphone",
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

  const recordingErrorMessage =
    recording.error === "recording_not_supported"
      ? t(locale, "parkinson", "recordingNotSupported")
      : recording.error === "microphone_permission_denied"
        ? t(locale, "parkinson", "micPermissionDenied")
        : recording.error === "recording_failed"
          ? t(locale, "parkinson", "recordingFailed")
          : null;

    const handleInferenceClick = async () => {
      if (mockApiEnabled) {
        prediction.mutate(testFeatureValues);
        return;
      }

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
        const response = await getAudioFeatures(accessToken, latestAudio.id);
        prediction.mutate(response.features);
      } catch {
        setAudioUploadError(t(locale, "parkinson", "featureLoadError"));
      }
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
              <Button onClick={handleContinue}>{t(locale, "common", "continue")}</Button>
            </div>
          </Card>
        </div>
      ) : null}

      <div className="surface-pane">
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

          <div className="mt-8 flex items-center justify-center gap-3">
            <Button
              size="lg"
              onClick={handleRecordButtonClick}
              disabled={isConsentOpen || isUploadingAudio || isExtractingBiomarkers}
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
              disabled={!canRunInference || prediction.isPending || isConsentOpen}
            >
              {prediction.isPending
                ? t(locale, "parkinson", "processing")
                : isAudioProcessing
                  ? t(locale, "parkinson", "audioProcessing")
                  : t(locale, "parkinson", "runInference")}
            </Button>
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
            {result ? `${t(locale, "parkinson", "confidenceLabel")}: ${result}` : null}
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
        </Card>
      </div>

      {showTestPanel ? (
      <Card>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h3 className="text-xl font-bold text-foreground">{t(locale, "parkinson", "testValuesTitle")}</h3>
            <p className="text-sm text-muted-foreground">{t(locale, "parkinson", "testValuesSubtitle")}</p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              setTestFeatureValues({ ...parkinsonTestFeaturePreset });
              setJsonEditorMessage(null);
              setJsonEditorError(null);
            }}
          >
            {t(locale, "parkinson", "restorePreset")}
          </Button>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {editableFeatureKeys.map((key) => (
            <label key={key} className="space-y-1">
              <span className="block text-xs font-semibold uppercase tracking-[0.1em] text-muted-foreground">{key}</span>
              <Input
                type="number"
                step="any"
                value={testFeatureValues[key]}
                onChange={(event) => updateFeatureValue(key, event.target.value)}
                aria-label={key}
              />
            </label>
          ))}
        </div>

        <div className="mt-6 space-y-2">
          <h4 className="text-sm font-semibold text-foreground">{t(locale, "parkinson", "testValuesJsonTitle")}</h4>
          <p className="text-xs text-muted-foreground">{t(locale, "parkinson", "testValuesJsonSubtitle")}</p>
          <textarea
            className="ghost-border min-h-[220px] w-full rounded-xl bg-surface-low p-3 text-xs text-foreground focus-visible:bg-surface-lowest focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
            value={jsonEditorValue}
            onChange={(event) => {
              setJsonEditorValue(event.target.value);
              setJsonEditorMessage(null);
              setJsonEditorError(null);
            }}
            aria-label={t(locale, "parkinson", "testValuesJsonTitle")}
            spellCheck={false}
          />
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" onClick={applyJsonValues}>
              {t(locale, "parkinson", "applyJson")}
            </Button>
            {jsonEditorMessage ? <p className="text-xs text-emerald-700">{jsonEditorMessage}</p> : null}
            {jsonEditorError ? <p className="text-xs font-semibold text-red-700">{jsonEditorError}</p> : null}
          </div>
        </div>
      </Card>
      ) : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {biomarkerCards.map((item) => (
          <Card key={item.key} className="p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">{t(locale, "parkinson", "measureLabel")}</p>
            <p className="mt-2 text-base font-semibold text-foreground">{item.label}</p>
            <p className="mt-3 text-2xl font-bold text-foreground">
              {typeof item.value === "number"
                ? `${item.value.toFixed(item.decimals)}${item.unit ? ` ${item.unit}` : ""}`
                : t(locale, "common", "notAvailable")}
            </p>
            <p className="mt-2 text-xs text-muted-foreground" title={item.description}>
              {item.description}
            </p>
          </Card>
        ))}
      </section>

      {biomarkerResponse ? (
        <Card className="p-4">
          <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
            {t(locale, "parkinson", "biomarkerMetadataLabel")}
          </p>
          <p className="mt-2 text-sm text-foreground">
            {biomarkerResponse.audio.sample_rate_hz} Hz | {biomarkerResponse.audio.channels} ch | {biomarkerResponse.audio.normalized_format.toUpperCase()} | {biomarkerResponse.audio.duration_seconds.toFixed(2)} s
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            {biomarkerResponse.parkinson_model_bridge.note}
          </p>
        </Card>
      ) : null}
    </section>
  );
}
