const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const mockFlag = (process.env.NEXT_PUBLIC_USE_MOCK_API || "").trim().toLowerCase();
const useMockApi = mockFlag === "true" || mockFlag === "1" || mockFlag === "yes" || mockFlag === "on";

export function isMockApiEnabled(): boolean {
  return useMockApi;
}

export type AudioStatus = "uploaded" | "processing" | "processed" | "transcribed" | "failed" | "archived";

export type AudioRecordOut = {
  id: number;
  uuid: string;
  user_id: number;
  source_type: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  duration_seconds?: number | null;
  status: AudioStatus;
  language_code: string | null;
  transcript_text?: string | null;
  notes: string | null;
  is_ready_for_inference?: boolean;
  processing_error?: string | null;
  created_at: string;
  updated_at?: string;
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
    user_id: 12,
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
    user_id: 12,
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

// Audio Processing API functions

export type AudioProcessingRequest = {
  audio_id: number;
  process_immediately?: boolean;
};

export type AudioProcessingResponse = {
  audio_record_id: number;
  status: string;
  features?: Record<string, number>;
  diagnosis_id?: number;
  prediction?: string;
  probability?: number;
  message?: string;
  error?: string;
};

export type BatchProcessingRequest = {
  limit?: number;
  process_all?: boolean;
};

export type BatchProcessingResult = {
  audio_record_id: number;
  status: string;
  error?: string;
  features?: Record<string, number>;
  diagnosis_id?: number;
};

export type BatchProcessingResponse = {
  results: BatchProcessingResult[];
  total_processed: number;
  successful: number;
  failed: number;
};

export type AudioAnalysisSummary = {
  total_audio_records: number;
  status_counts: Record<string, number>;
  recent_diagnoses: Array<{
    id: number;
    generated_at: string;
    status: string;
    description: string;
  }>;
  processed_features_summary: Array<{
    audio_id: number;
    created_at: string;
    fundamental_frequency: number;
    jitter: number;
    shimmer: number;
    hnr: number;
  }>;
};

export async function processAudio(
  accessToken: string,
  audioId: number,
  processImmediately: boolean = true
): Promise<AudioProcessingResponse> {
  if (useMockApi) {
    await delay(1200);
    const probability = 0.15 + Math.random() * 0.2;
    return {
      audio_record_id: audioId,
      status: "success",
      features: {
        "MDVP:Fo(Hz)": 120 + Math.random() * 30,
        "MDVP:Jitter(%)": 0.005 + Math.random() * 0.01,
        "MDVP:Shimmer": 0.03 + Math.random() * 0.02,
        "HNR": 20 + Math.random() * 5,
      },
      diagnosis_id: Math.round(Math.random() * 1000),
      prediction: probability >= 0.5 ? "positive" : "negative",
      probability,
      message: probability >= 0.5 
        ? "Possible Parkinson's detected with moderate confidence." 
        : "No significant Parkinson's indicators detected.",
    };
  }

  return apiRequest<AudioProcessingResponse>(
    `/audio/${audioId}/process`,
    accessToken,
    {
      method: "POST",
      body: JSON.stringify({
        audio_id: audioId,
        process_immediately: processImmediately,
      }),
    }
  );
}

export async function batchProcessAudio(
  accessToken: string,
  limit: number = 10,
  processAll: boolean = false
): Promise<BatchProcessingResponse> {
  if (useMockApi) {
    await delay(1500);
    const results: BatchProcessingResult[] = [];
    const count = processAll ? 5 : Math.min(limit, 5);
    
    for (let i = 0; i < count; i++) {
      const success = Math.random() > 0.3;
      results.push({
        audio_record_id: 100 + i,
        status: success ? "success" : "failed",
        error: success ? undefined : "Mock processing error",
        features: success ? {
          "MDVP:Fo(Hz)": 120 + Math.random() * 30,
          "MDVP:Jitter(%)": 0.005 + Math.random() * 0.01,
        } : undefined,
        diagnosis_id: success ? Math.round(Math.random() * 1000) : undefined,
      });
    }
    
    return {
      results,
      total_processed: count,
      successful: results.filter(r => r.status === "success").length,
      failed: results.filter(r => r.status === "failed").length,
    };
  }

  return apiRequest<BatchProcessingResponse>(
    "/audio/batch-process",
    accessToken,
    {
      method: "POST",
      body: JSON.stringify({
        limit,
        process_all: processAll,
      }),
    }
  );
}

export async function getAudioAnalysisSummary(
  accessToken: string
): Promise<AudioAnalysisSummary> {
  if (useMockApi) {
    await delay(800);
    return {
      total_audio_records: 12,
      status_counts: {
        uploaded: 3,
        processing: 2,
        processed: 6,
        failed: 1,
      },
      recent_diagnoses: [
        {
          id: 1,
          generated_at: new Date(Date.now() - 3600000).toISOString(),
          status: "pending",
          description: "Parkinson's analysis based on voice recording",
        },
        {
          id: 2,
          generated_at: new Date(Date.now() - 7200000).toISOString(),
          status: "confirmed",
          description: "No significant Parkinson's indicators detected",
        },
      ],
      processed_features_summary: [
        {
          audio_id: 101,
          created_at: new Date(Date.now() - 86400000).toISOString(),
          fundamental_frequency: 125.4,
          jitter: 0.008,
          shimmer: 0.045,
          hnr: 22.1,
        },
        {
          audio_id: 102,
          created_at: new Date(Date.now() - 172800000).toISOString(),
          fundamental_frequency: 118.7,
          jitter: 0.012,
          shimmer: 0.052,
          hnr: 19.8,
        },
      ],
    };
  }

  return apiRequest<AudioAnalysisSummary>(
    "/audio/analysis/summary",
    accessToken,
    { method: "GET" }
  );
}

export async function getAudioFeatures(
  accessToken: string,
  audioId: number
): Promise<{ audio_id: number; features: Record<string, number> }> {
  if (useMockApi) {
    await delay(600);
    return {
      audio_id: audioId,
      features: {
        "MDVP:Fo(Hz)": 120 + Math.random() * 30,
        "MDVP:Fhi(Hz)": 150 + Math.random() * 40,
        "MDVP:Flo(Hz)": 80 + Math.random() * 20,
        "MDVP:Jitter(%)": 0.005 + Math.random() * 0.01,
        "MDVP:Jitter(Abs)": 0.00005 + Math.random() * 0.00002,
        "MDVP:RAP": 0.003 + Math.random() * 0.002,
        "MDVP:PPQ": 0.004 + Math.random() * 0.003,
        "Jitter:DDP": 0.009 + Math.random() * 0.004,
        "MDVP:Shimmer": 0.03 + Math.random() * 0.02,
        "MDVP:Shimmer(dB)": 0.4 + Math.random() * 0.1,
        "Shimmer:APQ3": 0.02 + Math.random() * 0.01,
        "Shimmer:APQ5": 0.03 + Math.random() * 0.02,
        "MDVP:APQ": 0.025 + Math.random() * 0.015,
        "Shimmer:DDA": 0.06 + Math.random() * 0.03,
        "NHR": 0.02 + Math.random() * 0.01,
        "HNR": 20 + Math.random() * 5,
        "RPDE": 0.4 + Math.random() * 0.2,
        "DFA": 0.8 + Math.random() * 0.2,
        "spread1": -5.0 + Math.random() * 2.0,
        "spread2": 0.2 + Math.random() * 0.1,
        "D2": 2.3 + Math.random() * 0.5,
        "PPE": 0.25 + Math.random() * 0.1,
      },
    };
  }

  return apiRequest<{ audio_id: number; features: Record<string, number> }>(
    `/audio/${audioId}/features`,
    accessToken,
    { method: "GET" }
  );
}
