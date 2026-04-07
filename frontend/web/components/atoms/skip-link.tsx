"use client";

import { useUiStore } from "@/stores/ui-store";
import { t } from "@/lib/i18n";

export function SkipLink() {
  const locale = useUiStore((state) => state.locale);

  return (
    <a
      href="#main-content"
      className="sr-only z-50 rounded-md bg-surface-lowest px-3 py-2 text-foreground focus:not-sr-only focus:fixed focus:left-4 focus:top-4"
    >
      {t(locale, "common", "skipToContent")}
    </a>
  );
}
