"use client";

import { useEffect, useState } from "react";
import { isLocalAuthEnabled } from "@/lib/auth-mode";
import { getLocalSession } from "@/lib/local-auth";
import { createClient, isSupabaseConfigured } from "@/lib/supabase/client";

type SessionState = {
  accessToken: string | null;
  email: string;
  loading: boolean;
};

export function useSessionState(): SessionState {
  const [state, setState] = useState<SessionState>({
    accessToken: null,
    email: "",
    loading: true,
  });

  useEffect(() => {
    if (isLocalAuthEnabled) {
      const syncLocalState = () => {
        const localSession = getLocalSession();
        setState({
          accessToken: localSession.accessToken,
          email: localSession.email,
          loading: false,
        });
      };

      syncLocalState();
      window.addEventListener("storage", syncLocalState);
      return () => {
        window.removeEventListener("storage", syncLocalState);
      };
    }

    if (!isSupabaseConfigured()) {
      setState({ accessToken: null, email: "", loading: false });
      return;
    }

    const supabase = createClient();

    supabase.auth.getSession().then(({ data }) => {
      setState({
        accessToken: data.session?.access_token ?? null,
        email: data.session?.user.email ?? "",
        loading: false,
      });
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setState({
        accessToken: session?.access_token ?? null,
        email: session?.user.email ?? "",
        loading: false,
      });
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  return state;
}
