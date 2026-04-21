"use client";

import { useQuery } from "@tanstack/react-query";
import { getDiagnosisHistory, getMyAudio } from "@/lib/api";

export function useDashboardData(accessToken: string | null) {
  const audioQuery = useQuery({
    queryKey: ["audio", "me"],
    enabled: Boolean(accessToken),
    queryFn: () => getMyAudio(accessToken as string),
  });

  const historyQuery = useQuery({
    queryKey: ["diagnosis", "history", 5],
    enabled: Boolean(accessToken),
    queryFn: () => getDiagnosisHistory(accessToken as string, 5),
  });

  return { audioQuery, historyQuery };
}
