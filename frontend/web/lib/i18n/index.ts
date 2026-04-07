"use client";

import en from "@/lib/i18n/dictionaries/en";
import es from "@/lib/i18n/dictionaries/es";
import ptBR from "@/lib/i18n/dictionaries/pt-BR";
import { AppLocale, defaultLocale, normalizeLocale } from "@/lib/i18n/config";

type Dictionary = Record<string, Record<string, string>>;

const dictionaries = {
  es,
  en,
  "pt-BR": ptBR,
} as const satisfies Record<AppLocale, Dictionary>;

type Scope = keyof Dictionary;

type ScopeKeys<T extends Scope> = keyof Dictionary[T] & string;

export function getDictionary(locale?: string): Dictionary {
  const resolved = normalizeLocale(locale) as AppLocale;
  return dictionaries[resolved] ?? dictionaries[defaultLocale];
}

export function t<T extends Scope>(locale: string | undefined, scope: T, key: ScopeKeys<T>): string {
  const dict = getDictionary(locale);
  return dict[scope][key];
}
