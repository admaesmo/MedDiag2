"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Button } from "@/components/atoms/button";
import { Input } from "@/components/atoms/input";
import { loginSchema, type LoginValues } from "@/features/auth/schema";
import { isLocalAuthEnabled, localAuthDefaults } from "@/lib/auth-mode";
import { setLocalSession } from "@/lib/local-auth";
import { createClient } from "@/lib/supabase/client";
import { issueDevToken } from "@/lib/api";
import { useUiStore } from "@/stores/ui-store";
import { t } from "@/lib/i18n";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const locale = useUiStore((state) => state.locale);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: isLocalAuthEnabled ? localAuthDefaults.email : "",
      password: isLocalAuthEnabled ? localAuthDefaults.password : "",
    },
  });

  const nextPath = useMemo(() => searchParams.get("next") || "/dashboard", [searchParams]);

  const translateError = (message?: string) => {
    if (!message) {
      return "";
    }
    if (message === "invalidEmail" || message === "minPassword6" || message === "minPassword8") {
      return t(locale, "auth", message);
    }
    return message;
  };

  const onLogin = async (values: LoginValues) => {
    setError(null);
    setIsLoading(true);

    if (isLocalAuthEnabled) {
      if (
        values.email !== localAuthDefaults.email ||
        values.password !== localAuthDefaults.password
      ) {
        setIsLoading(false);
        setError("Credenciales locales invalidas.");
        return;
      }

      try {
        // Obtener un JWT real del backend de Render
        const tokenResponse = await issueDevToken(
          localAuthDefaults.email,
          localAuthDefaults.role,
          localAuthDefaults.displayName
        );
        setLocalSession(tokenResponse.access_token, localAuthDefaults.email);
      } catch {
        // Fallback: si el backend no está disponible, usar token simulado
        const mockToken = "dev_" + btoa(JSON.stringify({ email: localAuthDefaults.email, role: localAuthDefaults.role, ts: Date.now() }));
        setLocalSession(mockToken, localAuthDefaults.email);
      }
      setIsLoading(false);
      router.replace(nextPath);
      router.refresh();
      return;
    }

    const supabase = createClient();
    const { error: signInError } = await supabase.auth.signInWithPassword({
      email: values.email,
      password: values.password,
    });

    setIsLoading(false);

    if (signInError) {
      setError(signInError.message);
      return;
    }

    router.replace(nextPath);
    router.refresh();
  };

  const onOAuth = async (provider: "google" | "github") => {
    setError(null);
    const supabase = createClient();
    const redirectTo = `${window.location.origin}/auth/callback?next=${encodeURIComponent(nextPath)}`;

    const { error: oauthError } = await supabase.auth.signInWithOAuth({
      provider,
      options: { redirectTo },
    });

    if (oauthError) {
      setError(oauthError.message);
    }
  };

  return (
    <section id="main-content" className="mx-auto mt-12 w-full max-w-lg rounded-3xl bg-surface-lowest p-8 shadow-ambient">
      <h1 className="text-3xl font-bold">{t(locale, "auth", "login")}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{t(locale, "auth", "loginSubtitle")}</p>

      <form onSubmit={form.handleSubmit(onLogin)} className="mt-6 space-y-4">
        <div>
          <label className="mb-1 block text-sm font-semibold text-muted-foreground" htmlFor="email">
            {t(locale, "auth", "email")}
          </label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            aria-invalid={Boolean(form.formState.errors.email)}
            aria-describedby={form.formState.errors.email ? "email-error" : undefined}
            {...form.register("email")}
          />
          {form.formState.errors.email ? (
            <p id="email-error" className="mt-1 text-xs font-semibold text-red-700" role="alert">
              {translateError(form.formState.errors.email.message)}
            </p>
          ) : null}
        </div>

        <div>
          <label className="mb-1 block text-sm font-semibold text-muted-foreground" htmlFor="password">
            {t(locale, "auth", "password")}
          </label>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            aria-invalid={Boolean(form.formState.errors.password)}
            aria-describedby={form.formState.errors.password ? "password-error" : undefined}
            {...form.register("password")}
          />
          {form.formState.errors.password ? (
            <p id="password-error" className="mt-1 text-xs font-semibold text-red-700" role="alert">
              {translateError(form.formState.errors.password.message)}
            </p>
          ) : null}
        </div>

        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? t(locale, "auth", "submitting") : t(locale, "auth", "login")}
        </Button>
      </form>

      {isLocalAuthEnabled ? (
        <p className="mt-4 text-sm text-muted-foreground">
          Modo local activo. Usa <strong>{localAuthDefaults.email}</strong> / <strong>{localAuthDefaults.password}</strong>.
        </p>
      ) : (
        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => onOAuth("google")} aria-label={t(locale, "auth", "oauthGoogle")}>
            {t(locale, "auth", "oauthGoogle")}
          </Button>
          <Button variant="secondary" onClick={() => onOAuth("github")} aria-label={t(locale, "auth", "oauthGithub")}>
            {t(locale, "auth", "oauthGithub")}
          </Button>
        </div>
      )}

      {error ? <p className="mt-3 text-sm font-semibold text-red-700" role="alert" aria-live="assertive">{error}</p> : null}

      <p className="mt-4 text-sm text-muted-foreground">
        {t(locale, "auth", "noAccount")} <Link className="font-semibold text-primary" href="/register">{t(locale, "auth", "registerHere")}</Link>
      </p>
    </section>
  );
}
