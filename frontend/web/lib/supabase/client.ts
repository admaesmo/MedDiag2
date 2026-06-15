import { createBrowserClient } from "@supabase/ssr";
import { isLocalAuthEnabled } from "@/lib/auth-mode";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey =
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY ||
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

export function isSupabaseConfigured(): boolean {
  return !isLocalAuthEnabled && Boolean(supabaseUrl) && Boolean(supabaseKey);
}

export function createClient() {
  if (!isSupabaseConfigured()) {
    throw new Error("Supabase is not configured or local auth mode is active.");
  }
  return createBrowserClient(supabaseUrl!, supabaseKey!);
}
