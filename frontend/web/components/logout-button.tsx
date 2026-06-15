"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { isLocalAuthEnabled } from "@/lib/auth-mode";
import { clearLocalSession } from "@/lib/local-auth";
import { useUiStore } from "@/stores/ui-store";
import { t } from "@/lib/i18n";
import { Button } from "@/components/atoms/button";

export function LogoutButton() {
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const locale = useUiStore((state) => state.locale);

  const onLogout = async () => {
    setIsLoading(true);
    if (isLocalAuthEnabled) {
      clearLocalSession();
      router.replace("/login");
      return;
    }
    const { createClient, isSupabaseConfigured } = await import("@/lib/supabase/client");
    if (isSupabaseConfigured()) {
      const supabase = createClient();
      await supabase.auth.signOut();
    }
    router.replace("/login");
  };

  return (
    <Button variant="secondary" size="sm" onClick={onLogout} disabled={isLoading}>
      {isLoading ? t(locale, "common", "loading") : t(locale, "nav", "logout")}
    </Button>
  );
}
