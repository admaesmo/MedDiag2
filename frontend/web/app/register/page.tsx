"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Button } from "@/components/atoms/button";
import { Input } from "@/components/atoms/input";
import { registerSchema, type RegisterValues } from "@/features/auth/schema";
import { createClient } from "@/lib/supabase/client";
import { useUiStore } from "@/stores/ui-store";
import { t } from "@/lib/i18n";

export default function RegisterPage() {
  const router = useRouter();
  const locale = useUiStore((state) => state.locale);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  const translateError = (message?: string) => {
    if (!message) {
      return "";
    }
    if (message === "invalidEmail" || message === "minPassword6" || message === "minPassword8") {
      return t(locale, "auth", message);
    }
    return message;
  };

  const onRegister = async (values: RegisterValues) => {
    setError(null);
    setMessage(null);
    setIsLoading(true);

    const supabase = createClient();
    const redirectTo = `${window.location.origin}/auth/callback?next=/dashboard`;

    const { error: signUpError } = await supabase.auth.signUp({
      email: values.email,
      password: values.password,
      options: { emailRedirectTo: redirectTo },
    });

    setIsLoading(false);

    if (signUpError) {
      setError(signUpError.message);
      return;
    }

    setMessage(t(locale, "auth", "registerSuccess"));
    router.replace("/dashboard");
    router.refresh();
  };

  return (
    <section id="main-content" className="mx-auto mt-12 w-full max-w-lg rounded-3xl bg-surface-lowest p-8 shadow-ambient">
      <h1 className="text-3xl font-bold">{t(locale, "auth", "register")}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{t(locale, "auth", "registerSubtitle")}</p>

      <form onSubmit={form.handleSubmit(onRegister)} className="mt-6 space-y-4">
        <div>
          <label className="mb-1 block text-sm font-semibold text-muted-foreground" htmlFor="email">
            {t(locale, "auth", "email")}
          </label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            aria-invalid={Boolean(form.formState.errors.email)}
            aria-describedby={form.formState.errors.email ? "register-email-error" : undefined}
            {...form.register("email")}
          />
          {form.formState.errors.email ? (
            <p id="register-email-error" className="mt-1 text-xs font-semibold text-red-700" role="alert">
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
            autoComplete="new-password"
            aria-invalid={Boolean(form.formState.errors.password)}
            aria-describedby={form.formState.errors.password ? "register-password-error" : undefined}
            {...form.register("password")}
          />
          {form.formState.errors.password ? (
            <p id="register-password-error" className="mt-1 text-xs font-semibold text-red-700" role="alert">
              {translateError(form.formState.errors.password.message)}
            </p>
          ) : null}
        </div>

        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? t(locale, "auth", "submitting") : t(locale, "auth", "register")}
        </Button>
      </form>

      {error ? <p className="mt-3 text-sm font-semibold text-red-700" role="alert" aria-live="assertive">{error}</p> : null}
      {message ? <p className="mt-3 text-sm text-muted-foreground" role="status" aria-live="polite">{message}</p> : null}

      <p className="mt-4 text-sm text-muted-foreground">
        {t(locale, "auth", "hasAccount")} <Link className="font-semibold text-primary" href="/login">{t(locale, "auth", "loginHere")}</Link>
      </p>
    </section>
  );
}
