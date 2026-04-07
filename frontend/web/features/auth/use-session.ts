"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

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
