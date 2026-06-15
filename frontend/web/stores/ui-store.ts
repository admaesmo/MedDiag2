"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { AppLocale, defaultLocale } from "@/lib/i18n/config";

type UiState = {
  locale: AppLocale;
  sidebarOpen: boolean;
  parkinsonConsentAcceptedEmails: string[];
  setLocale: (locale: AppLocale) => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  addParkinsonConsentEmail: (email: string) => void;
};

export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      locale: defaultLocale,
      sidebarOpen: true,
      parkinsonConsentAcceptedEmails: [],
      setLocale: (locale) => set({ locale }),
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      addParkinsonConsentEmail: (email) =>
        set((state) => ({
          parkinsonConsentAcceptedEmails: state.parkinsonConsentAcceptedEmails.includes(email)
            ? state.parkinsonConsentAcceptedEmails
            : [...state.parkinsonConsentAcceptedEmails, email],
        })),
    }),
    {
      name: "meddiag-ui-store",
      skipHydration: true,
      partialize: (state) => ({
        locale: state.locale,
        parkinsonConsentAcceptedEmails: state.parkinsonConsentAcceptedEmails,
      }),
    },
  ),
);
