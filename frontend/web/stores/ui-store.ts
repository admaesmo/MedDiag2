"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { AppLocale, defaultLocale } from "@/lib/i18n/config";

type UiState = {
  locale: AppLocale;
  sidebarOpen: boolean;
  parkinsonConsentAccepted: boolean;
  setLocale: (locale: AppLocale) => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setParkinsonConsentAccepted: (accepted: boolean) => void;
};

export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      locale: defaultLocale,
      sidebarOpen: true,
      parkinsonConsentAccepted: false,
      setLocale: (locale) => set({ locale }),
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setParkinsonConsentAccepted: (accepted) => set({ parkinsonConsentAccepted: accepted }),
    }),
    {
      name: "meddiag-ui-store",
      partialize: (state) => ({
        locale: state.locale,
        parkinsonConsentAccepted: state.parkinsonConsentAccepted,
      }),
    },
  ),
);
