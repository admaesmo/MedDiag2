"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useState } from "react";
import { Button } from "@/components/atoms/button";
import { Card } from "@/components/atoms/card";
import { Input } from "@/components/atoms/input";
import { useUiStore } from "@/stores/ui-store";
import { SettingsFormValues, settingsSchema } from "@/features/settings/schema";
import { t } from "@/lib/i18n";

export default function SettingsPage() {
  const locale = useUiStore((state) => state.locale);
  const setLocale = useUiStore((state) => state.setLocale);
  const [savedMessageVisible, setSavedMessageVisible] = useState(false);

  const translateError = (message?: string) => {
    if (!message) {
      return "";
    }
    return t(locale, "auth", message as "displayNameMin");
  };

  const form = useForm<SettingsFormValues>({
    resolver: zodResolver(settingsSchema),
    defaultValues: {
      displayName: "",
      locale,
    },
  });

  return (
    <section id="main-content" className="space-y-6">
      <header>
        <h2 className="text-4xl font-extrabold">{t(locale, "settings", "title")}</h2>
        <p className="mt-2 text-muted-foreground">{t(locale, "settings", "subtitle")}</p>
      </header>

      <Card className="max-w-2xl">
        <form
          className="space-y-4"
          onSubmit={form.handleSubmit((values) => {
            setLocale(values.locale);
            setSavedMessageVisible(true);
          })}
          aria-describedby="settings-form-status"
        >
          <div>
            <label className="mb-1 block text-sm font-semibold text-muted-foreground" htmlFor="displayName">
              {t(locale, "settings", "displayName")}
            </label>
            <Input
              id="displayName"
              aria-invalid={Boolean(form.formState.errors.displayName)}
              aria-describedby={form.formState.errors.displayName ? "displayName-error" : undefined}
              {...form.register("displayName")}
            />
            {form.formState.errors.displayName ? (
              <p id="displayName-error" className="mt-1 text-xs font-semibold text-red-700" role="alert">
                {translateError(form.formState.errors.displayName.message)}
              </p>
            ) : null}
          </div>

          <div>
            <label className="mb-1 block text-sm font-semibold text-muted-foreground" htmlFor="locale">
              {t(locale, "settings", "language")}
            </label>
            <select
              id="locale"
              className="ghost-border h-11 w-full rounded-xl bg-surface-low px-3 text-sm"
              aria-label={t(locale, "settings", "language")}
              {...form.register("locale")}
            >
              <option value="es">{t(locale, "settings", "localeEs")}</option>
              <option value="en">{t(locale, "settings", "localeEn")}</option>
              <option value="pt-BR">{t(locale, "settings", "localePt")}</option>
            </select>
          </div>

          <Button type="submit">{t(locale, "settings", "save")}</Button>
        </form>

        <p id="settings-form-status" className="mt-3 text-sm text-muted-foreground" aria-live="polite" role="status">
          {savedMessageVisible ? t(locale, "settings", "saved") : ""}
        </p>
      </Card>
    </section>
  );
}
