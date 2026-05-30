"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import {
  VoiceSessionOut,
  SessionAnalysisResult,
  createVoiceSession,
  addSessionTake,
  getVoiceSession,
  analyzeVoiceSession,
  removeSessionTake,
} from "@/lib/api";

const POLLING_INTERVAL_MS = 2000;
const POLLING_TIMEOUT_MS = 60000;

export type VoiceSessionHook = {
  session: VoiceSessionOut | null;
  result: SessionAnalysisResult | null;
  isCreating: boolean;
  addingTakeNumber: number | null;
  isAnalyzing: boolean;
  isPolling: boolean;
  error: string | null;
  startSession: (maxTakes?: number) => Promise<void>;
  addTake: (blob: Blob, takeNumber: number, fileName: string, sourceType?: string) => Promise<void>;
  removeTake: (takeId: number) => Promise<void>;
  analyze: () => Promise<void>;
  reset: () => void;
};

export function useVoiceSession(accessToken: string | null): VoiceSessionHook {
  const [session, setSession] = useState<VoiceSessionOut | null>(null);
  const [result, setResult] = useState<SessionAnalysisResult | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [addingTakeNumber, setAddingTakeNumber] = useState<number | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pollingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isPollingRef = useRef(false);
  const pollingStartTimeRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (pollingTimeoutRef.current) clearTimeout(pollingTimeoutRef.current);
    };
  }, []);

  const stopPolling = useCallback(() => {
    if (pollingTimeoutRef.current) {
      clearTimeout(pollingTimeoutRef.current);
      pollingTimeoutRef.current = null;
    }
    isPollingRef.current = false;
    setIsPolling(false);
    pollingStartTimeRef.current = null;
  }, []);

  const refreshSession = useCallback(async (sessionId: number): Promise<VoiceSessionOut | null> => {
    if (!accessToken) return null;
    try {
      const updated = await getVoiceSession(accessToken, sessionId);
      setSession(updated);
      return updated;
    } catch {
      setError("Error al actualizar la sesión");
      return null;
    }
  }, [accessToken]);

  const startPolling = useCallback((sessionId: number) => {
    if (!accessToken) return;
    stopPolling();
    isPollingRef.current = true;
    setIsPolling(true);
    pollingStartTimeRef.current = Date.now();

    const poll = async () => {
      if (!isPollingRef.current) return;

      if (
        pollingStartTimeRef.current !== null &&
        Date.now() - pollingStartTimeRef.current > POLLING_TIMEOUT_MS
      ) {
        setError("El procesamiento de las tomas ha excedido el tiempo límite.");
        stopPolling();
        return;
      }

      try {
        const currentSession = await getVoiceSession(accessToken!, sessionId);
        setSession(currentSession);

        const hasProcessing = currentSession.takes.some((tk) => tk.status === "processing");
        if (hasProcessing && isPollingRef.current) {
          pollingTimeoutRef.current = setTimeout(poll, POLLING_INTERVAL_MS);
        } else {
          stopPolling();
        }
      } catch {
        setError("Error durante la verificación del estado de las tomas");
        stopPolling();
      }
    };

    void poll();
  }, [accessToken, stopPolling]);

  const startSession = useCallback(async (maxTakes = 3) => {
    if (!accessToken) {
      setError("Debes iniciar sesión para usar el análisis multi-toma");
      return;
    }
    setIsCreating(true);
    setError(null);
    try {
      const newSession = await createVoiceSession(accessToken, maxTakes);
      setSession(newSession);
      setResult(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al crear la sesión");
    } finally {
      setIsCreating(false);
    }
  }, [accessToken]);

  const addTake = useCallback(async (
    blob: Blob,
    takeNumber: number,
    fileName: string,
    sourceType = "microphone",
  ) => {
    if (!accessToken || !session) {
      setError("No hay sesión activa");
      return;
    }
    setAddingTakeNumber(takeNumber);
    setError(null);
    try {
      await addSessionTake(accessToken, session.id, blob, fileName, sourceType);
      const updated = await refreshSession(session.id);
      if (updated && updated.takes.some((tk) => tk.status === "processing")) {
        startPolling(session.id);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al subir la toma");
    } finally {
      setAddingTakeNumber(null);
    }
  }, [accessToken, session, refreshSession, startPolling]);

  const removeTake = useCallback(async (takeId: number) => {
    if (!accessToken || !session) return;
    setError(null);
    try {
      await removeSessionTake(accessToken, session.id, takeId);
      const updated = await refreshSession(session.id);
      if (updated && !updated.takes.some((tk) => tk.status === "processing")) {
        stopPolling();
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al eliminar la toma");
    }
  }, [accessToken, session, refreshSession, stopPolling]);

  const analyze = useCallback(async () => {
    if (!accessToken || !session) return;
    setIsAnalyzing(true);
    setError(null);
    try {
      const analysisResult = await analyzeVoiceSession(accessToken, session.id);
      setResult(analysisResult);
      await refreshSession(session.id);
      stopPolling();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al analizar la sesión");
    } finally {
      setIsAnalyzing(false);
    }
  }, [accessToken, session, refreshSession, stopPolling]);

  const reset = useCallback(() => {
    stopPolling();
    setSession(null);
    setResult(null);
    setAddingTakeNumber(null);
    setIsCreating(false);
    setIsAnalyzing(false);
    setError(null);
  }, [stopPolling]);

  return {
    session,
    result,
    isCreating,
    addingTakeNumber,
    isAnalyzing,
    isPolling,
    error,
    startSession,
    addTake,
    removeTake,
    analyze,
    reset,
  };
}
