"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { convertAudioBlobToWav } from "@/features/parkinson/audio-blob-to-wav";

const MIME_CANDIDATES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4",
  "audio/ogg;codecs=opus",
  "audio/ogg",
];

function pickSupportedMimeType(): string {
  if (typeof MediaRecorder === "undefined") {
    return "";
  }

  for (const mimeType of MIME_CANDIDATES) {
    if (MediaRecorder.isTypeSupported(mimeType)) {
      return mimeType;
    }
  }

  return "";
}

export type AudioRecordingState = {
  isSupported: boolean;
  isRecording: boolean;
  elapsedSeconds: number;
  audioBlob: Blob | null;
  audioMimeType: string;
  error: string | null;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<Blob | null>;
  resetRecording: () => void;
};

export function useAudioRecording(): AudioRecordingState {
  const [isRecording, setIsRecording] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);

  const audioMimeType = useMemo(() => pickSupportedMimeType(), []);
  const isSupported = typeof navigator !== "undefined" && typeof MediaRecorder !== "undefined";

  const stopTracks = useCallback(() => {
    if (streamRef.current) {
      for (const track of streamRef.current.getTracks()) {
        track.stop();
      }
    }
    streamRef.current = null;
  }, []);

  const stopTimer = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const resetRecording = useCallback(() => {
    setAudioBlob(null);
    setError(null);
    setElapsedSeconds(0);
  }, []);

  const startRecording = useCallback(async () => {
    if (!isSupported) {
      setError("recording_not_supported");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      streamRef.current = stream;
      chunksRef.current = [];
      setAudioBlob(null);
      setElapsedSeconds(0);
      setError(null);

      const recorder = audioMimeType
        ? new MediaRecorder(stream, { mimeType: audioMimeType })
        : new MediaRecorder(stream);

      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstart = () => {
        setIsRecording(true);
        stopTimer();
        timerRef.current = window.setInterval(() => {
          setElapsedSeconds((seconds) => seconds + 1);
        }, 1000);
      };

      recorder.onerror = () => {
        setError("recording_failed");
      };

      recorder.onstop = () => {
        setIsRecording(false);
        stopTimer();
        stopTracks();
      };

      recorder.start(500);
    } catch {
      setError("microphone_permission_denied");
      setIsRecording(false);
      stopTimer();
      stopTracks();
    }
  }, [audioMimeType, isSupported, stopTimer, stopTracks]);

  const stopRecording = useCallback(async (): Promise<Blob | null> => {
    const recorder = mediaRecorderRef.current;

    if (!recorder) {
      return audioBlob;
    }

    if (recorder.state !== "recording") {
      return audioBlob;
    }

    await new Promise<void>((resolve) => {
      recorder.addEventListener(
        "stop",
        () => {
          resolve();
        },
        { once: true },
      );
      recorder.stop();
    });

    const rawBlob = new Blob(chunksRef.current, {
      type: recorder.mimeType || audioMimeType || "audio/webm",
    });

    if (rawBlob.size === 0) {
      setAudioBlob(null);
      return null;
    }

    try {
      const normalizedBlob = await convertAudioBlobToWav(rawBlob);
      setAudioBlob(normalizedBlob);
      setError(null);
      return normalizedBlob;
    } catch {
      setAudioBlob(null);
      setError("audio_conversion_failed");
      return null;
    }
  }, [audioBlob, audioMimeType]);

  useEffect(() => {
    return () => {
      stopTimer();
      stopTracks();
      if (mediaRecorderRef.current?.state === "recording") {
        mediaRecorderRef.current.stop();
      }
    };
  }, [stopTimer, stopTracks]);

  return {
    isSupported,
    isRecording,
    elapsedSeconds,
    audioBlob,
    audioMimeType,
    error,
    startRecording,
    stopRecording,
    resetRecording,
  };
}
