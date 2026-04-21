import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import { isLocalAuthEnabled } from "@/lib/auth-mode";
import { localAuthCookieNames } from "@/lib/local-auth-shared";
import { createClient } from "@/lib/supabase/server";

export default async function HomePage() {
  if (isLocalAuthEnabled) {
    const cookieStore = await cookies();
    const token = cookieStore.get(localAuthCookieNames.accessToken)?.value;
    redirect(token ? "/dashboard" : "/login");
  }

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  redirect(user ? "/dashboard" : "/login");
}
