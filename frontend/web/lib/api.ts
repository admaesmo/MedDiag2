const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const mockFlag = (process.env.NEXT_PUBLIC_USE_MOCK_API || "").trim().toLowerCase();
const useMockApi = mockFlag === "true" || mockFlag === "1" || mockFlag === "yes" || mockFlag === "on";

export function isMockApiEnabled(): boolean {
  return useMockApi;
}

export type AudioStatus = "uploaded" | "processing" | "transcribed" | "failed";

export type AudioRecordOut = {
  id: number;
  uuid: string;
  source_type: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  status: AudioStatus;
  language_code: string | null;
  notes: string | null;
  created_at: string;
};

export type AudioListResponse = {
  items: AudioRecordOut[];
  total: number;
};

export type UserOut = {
  id: number;
  email: string;
  display_name: string | null;
  auth_provider: string;
  is_active: boolean;
  roles: string[];
};

export type DiagnosisHistoryItem = {
  id: number;
  generated_at: string;
  status: "pending" | "confirmed" | "discarded";
  final_description: string;
  user_name: string;
  user_email: string;
  disease_name: string;
  disease_code: "DIAB" | "HEART" | "PARK";
  probability: number;
};

export type PredictionPayload = {
  patient: {
    name: string;
    email?: string;
  };
  features: Record<string, number>;
};

export type PredictionResponse = {
  disease_code: string;
  prediction: number;
  probability: number;
  message: string;
};

export type AudioUploadResponse = {
  audio_id: number;
  uuid: string;
  status: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  created_at: string;
};

const mockUser: UserOut = {
  id: 12,
  email: "clinician@meddiag.local",
  display_name: "Dr. Alvarez",
  auth_provider: "supabase",
  is_active: true,
  roles: ["doctor"],
};

const mockAudio: AudioRecordOut[] = [
  {
    id: 101,
    uuid: "ab4ec347-2118-4dcf-b223-362f2eebf112",
    source_type: "recording",
    original_filename: "voice-sample-101.webm",
    mime_type: "audio/webm",
    file_size_bytes: 145120,
    status: "transcribed",
    language_code: "es",
    notes: "Stable baseline",
    created_at: new Date(Date.now() - 3600_000).toISOString(),
  },
  {
    id: 102,
    uuid: "0d90ab6d-74e8-4ce2-a5fa-2ebfe09179d8",
    source_type: "upload",
    original_filename: "voice-followup-102.wav",
    mime_type: "audio/wav",
    file_size_bytes: 208110,
    status: "processing",
    language_code: "en",
    notes: null,
    created_at: new Date(Date.now() - 12_600_000).toISOString(),
  },
];

const mockHistory: DiagnosisHistoryItem[] = [
  {
    id: 1,
    generated_at: new Date(Date.now() - 1000 * 60 * 20).toISOString(),
    status: "confirmed",
    final_description: "Paciente estable con variabilidad leve.",
    user_name: "Ana Ramirez",
    user_email: "ana@demo.dev",
    disease_name: "Parkinson",
    disease_code: "PARK",
    probability: 0.118,
  },
  {
    id: 2,
    generated_at: new Date(Date.now() - 1000 * 60 * 90).toISOString(),
    status: "pending",
    final_description: "Resultado en revisión por especialista.",
    user_name: "Luis Ortega",
    user_email: "luis@demo.dev",
    disease_name: "Heart Disease",
    disease_code: "HEART",
    probability: 0.671,
  },
];

function delay(ms = 260) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

async function apiRequest<T>(path: string, accessToken?: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function getMe(accessToken: string): Promise<UserOut> {
  if (useMockApi) {
    await delay();
    return mockUser;
  }

  return apiRequest<UserOut>("/auth/me", accessToken, { method: "GET" });
}

export async function getMyAudio(accessToken: string): Promise<AudioListResponse> {
  if (useMockApi) {
    await delay();
    return { items: mockAudio, total: mockAudio.length };
  }

  return apiRequest<AudioListResponse>("/audio/me", accessToken, { method: "GET" });
}

export async function getAudioById(id: number, accessToken: string): Promise<AudioRecordOut> {
  if (useMockApi) {
    await delay();
    const item = mockAudio.find((audio) => audio.id === id);
    if (!item) {
      throw new Error("Audio record not found");
    }
    return item;
  }

  return apiRequest<AudioRecordOut>(`/audio/${id}`, accessToken, { method: "GET" });
}

export async function uploadAudio(accessToken: string): Promise<{ audio_id: number; status: string }> {
  if (useMockApi) {
    await delay(420);
    return { audio_id: Math.round(Math.random() * 1000), status: "uploaded" };
  }

  throw new Error("uploadAudio requires a Blob payload");
}

export async function uploadAudioMultipart(
  accessToken: string,
  audioBlob: Blob,
  fileName: string,
  options?: {
    sourceType?: string;
    languageCode?: string;
    notes?: string;
  },
): Promise<AudioUploadResponse> {
  if (useMockApi) {
    await delay(420);
    return {
      audio_id: Math.round(Math.random() * 1000),
      uuid: crypto.randomUUID(),
      status: "uploaded",
      original_filename: fileName,
      mime_type: audioBlob.type || "audio/webm",
      file_size_bytes: audioBlob.size,
      created_at: new Date().toISOString(),
    };
  }

  const formData = new FormData();
  formData.append("file", audioBlob, fileName);
  formData.append("source_type", options?.sourceType ?? "microphone");

  if (options?.languageCode) {
    formData.append("language_code", options.languageCode);
  }
  if (options?.notes) {
    formData.append("notes", options.notes);
  }

  const response = await fetch(`${apiBaseUrl}/audio/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: formData,
    cache: "no-store",
  });

  if (!response.ok) {
    let detail = `Upload failed: ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        detail = payload.detail;
      }
    } catch {
      // Keep generic message if response body is not JSON.
    }
    throw new Error(detail);
  }

  return response.json() as Promise<AudioUploadResponse>;
}

export async function getDiagnosisHistory(accessToken: string, limit = 50): Promise<DiagnosisHistoryItem[]> {
  if (useMockApi) {
    await delay();
    return mockHistory.slice(0, limit);
  }

  return apiRequest<DiagnosisHistoryItem[]>(`/diagnoses/history?limit=${limit}`, accessToken, { method: "GET" });
}

export async function predictParkinson(
  accessToken: string | null,
  payload: PredictionPayload,
): Promise<PredictionResponse> {
  if (useMockApi) {
    await delay(680);
    const probability = 0.12 + Math.random() * 0.15;
    return {
      disease_code: "PARK",
      prediction: probability >= 0.5 ? 1 : 0,
      probability,
      message:
        probability >= 0.5
          ? "Possible Parkinson pattern detected. Specialist review suggested."
          : "No strong Parkinson pattern detected.",
    };
  }

  return apiRequest<PredictionResponse>("/predict/parkinson", accessToken ?? undefined, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
