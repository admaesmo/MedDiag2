import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import { isLocalAuthEnabled } from "@/lib/auth-mode";
import { localAuthCookieNames } from "@/lib/local-auth-shared";
import { createClient } from "@/lib/supabase/server";
import { PrivateShell } from "@/components/templates/private-shell";

export default async function PrivateLayout({ children }: { children: React.ReactNode }) {
  if (isLocalAuthEnabled) {
    const cookieStore = await cookies();
    const accessToken = cookieStore.get(localAuthCookieNames.accessToken)?.value;
    const email = cookieStore.get(localAuthCookieNames.email)?.value ?? "";

    if (!accessToken) {
      redirect("/login");
    }

    return <PrivateShell userEmail={email}>{children}</PrivateShell>;
  }

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  return <PrivateShell userEmail={user.email ?? ""}>{children}</PrivateShell>;
}
