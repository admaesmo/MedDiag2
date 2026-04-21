export const supportedLocales = ["es", "en", "pt-BR"] as const;

export type AppLocale = (typeof supportedLocales)[number];

export const defaultLocale: AppLocale = "es";

export function normalizeLocale(value?: string | null): AppLocale {
  if (!value) {
    return defaultLocale;
  }

  const found = supportedLocales.find((locale) => locale.toLowerCase() === value.toLowerCase());
  return found ?? defaultLocale;
}
