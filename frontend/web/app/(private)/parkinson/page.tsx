"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Mic, Play } from "lucide-react";
import { Button } from "@/components/atoms/button";
import { Card } from "@/components/atoms/card";
import { Input } from "@/components/atoms/input";
import { useSessionState } from "@/features/auth/use-session";
import { useAudioRecording } from "@/features/parkinson/use-audio-recording";
import { parkinsonTestFeaturePreset, useParkinsonPrediction } from "@/features/parkinson/mutations";
import { isMockApiEnabled, uploadAudioMultipart } from "@/lib/api";
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
  const locale = useUiStore((state) => state.locale);
  const consentAccepted = useUiStore((state) => state.parkinsonConsentAccepted);
  const setConsentAccepted = useUiStore((state) => state.setParkinsonConsentAccepted);
  const [isUploadingAudio, setIsUploadingAudio] = useState(false);
  const [audioUploadMessage, setAudioUploadMessage] = useState<string | null>(null);
  const [audioUploadError, setAudioUploadError] = useState<string | null>(null);
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
  const showTestPanel = mockApiEnabled || process.env.NODE_ENV !== "production";
  const canRunInference = mockApiEnabled || Boolean(accessToken);
  const elapsedLabel = formatElapsed(recording.elapsedSeconds);

  const measures = [
    t(locale, "parkinson", "m1"),
    t(locale, "parkinson", "m2"),
    t(locale, "parkinson", "m3"),
    t(locale, "parkinson", "m4"),
    t(locale, "parkinson", "m5"),
    t(locale, "parkinson", "m6"),
    t(locale, "parkinson", "m7"),
    t(locale, "parkinson", "m8"),
  ];

  const measureDescriptions = [
    t(locale, "parkinson", "m1Info"),
    t(locale, "parkinson", "m2Info"),
    t(locale, "parkinson", "m3Info"),
    t(locale, "parkinson", "m4Info"),
    t(locale, "parkinson", "m5Info"),
    t(locale, "parkinson", "m6Info"),
    t(locale, "parkinson", "m7Info"),
    t(locale, "parkinson", "m8Info"),
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
    if (isConsentOpen || isUploadingAudio) {
      return;
    }

    if (!recording.isRecording) {
      setAudioUploadMessage(null);
      setAudioUploadError(null);
      recording.resetRecording();
      await recording.startRecording();
      return;
    }

    const audioBlob = await recording.stopRecording();
    if (!audioBlob || audioBlob.size === 0) {
      setAudioUploadError(t(locale, "parkinson", "noAudioCaptured"));
      return;
    }

    if (!accessToken && !mockApiEnabled) {
      setAudioUploadError(t(locale, "parkinson", "authRequiredForUpload"));
      return;
    }

    try {
      setIsUploadingAudio(true);
      setAudioUploadError(null);

      const extension = audioBlob.type.includes("webm")
        ? "webm"
        : audioBlob.type.includes("mp4")
          ? "m4a"
          : audioBlob.type.includes("ogg")
            ? "ogg"
            : "wav";

      const response = await uploadAudioMultipart(accessToken ?? "", audioBlob, `parkinson-sample.${extension}`, {
        sourceType: "microphone",
        languageCode: locale.split("-")[0],
      });

      setAudioUploadMessage(`${t(locale, "parkinson", "uploadSuccess")}: #${response.audio_id}`);
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
              disabled={isConsentOpen || isUploadingAudio}
            >
              <Play className="mr-2 h-4 w-4" />
              {isUploadingAudio
                ? t(locale, "parkinson", "uploading")
                : recording.isRecording
                  ? t(locale, "parkinson", "stop")
                  : t(locale, "parkinson", "start")}
            </Button>
            <Button
              variant="secondary"
              size="lg"
              onClick={() => prediction.mutate(testFeatureValues)}
              disabled={!canRunInference || prediction.isPending || isConsentOpen}
            >
              {prediction.isPending ? t(locale, "parkinson", "processing") : t(locale, "parkinson", "runInference")}
            </Button>
          </div>

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
        {measures.map((item, index) => (
          <Card key={item} className="p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">{t(locale, "parkinson", "measureLabel")}</p>
            <p className="mt-2 text-base font-semibold text-foreground">{item}</p>
            <p className="mt-2 text-xs text-muted-foreground" title={measureDescriptions[index]}>
              {measureDescriptions[index]}
            </p>
          </Card>
        ))}
      </section>
    </section>
  );
}
