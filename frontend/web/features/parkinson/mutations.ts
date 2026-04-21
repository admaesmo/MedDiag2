"use client";

import { useMutation } from "@tanstack/react-query";
import { predictParkinson } from "@/lib/api";

const defaultFeatures = {
  "MDVP:Fo(Hz)": 119.992,
  "MDVP:Fhi(Hz)": 157.302,
  "MDVP:Flo(Hz)": 74.997,
  "MDVP:Jitter(%)": 0.00784,
  "MDVP:Jitter(Abs)": 0.00007,
  "MDVP:RAP": 0.0037,
  "MDVP:PPQ": 0.00554,
  "Jitter:DDP": 0.01109,
  "MDVP:Shimmer": 0.04374,
  "MDVP:Shimmer(dB)": 0.426,
  "Shimmer:APQ3": 0.02182,
  "Shimmer:APQ5": 0.0313,
  "MDVP:APQ": 0.02971,
  "Shimmer:DDA": 0.06545,
  "NHR": 0.02211,
  "HNR": 21.033,
  "RPDE": 0.414783,
  "DFA": 0.815285,
  "spread1": -4.813031,
  "spread2": 0.266482,
  "D2": 2.301442,
  "PPE": 0.284654,
};

export const parkinsonTestFeaturePreset = {
  "MDVP:RAP": 0.0037,
  "MDVP:PPQ": 0.00554,
  "Jitter:DDP": 0.01109,
  "MDVP:Shimmer(dB)": 0.426,
  "Shimmer:APQ3": 0.02182,
  "Shimmer:APQ5": 0.0313,
  "MDVP:APQ": 0.02971,
  "Shimmer:DDA": 0.06545,
  "NHR": 0.02211,
  "HNR": 21.033,
  "RPDE": 0.414783,
  "DFA": 0.815285,
  "D2": 2.301442,
  "PPE": 0.284654,
} as const;

export function useParkinsonPrediction(accessToken: string | null, email: string) {
  return useMutation({
    mutationFn: (featureOverrides?: Partial<typeof defaultFeatures>) => {
      const payload = {
        patient: {
          name: email || "Patient Session",
          email,
        },
        features: {
          ...defaultFeatures,
          ...featureOverrides,
        },
      };
      console.log("[PARKINSON] Sending payload:", JSON.stringify(payload, null, 2));
      return predictParkinson(accessToken as string, payload);
    },
  });
}
