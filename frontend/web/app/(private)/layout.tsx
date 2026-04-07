import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { PrivateShell } from "@/components/templates/private-shell";

export default async function PrivateLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  return <PrivateShell userEmail={user.email ?? ""}>{children}</PrivateShell>;
}
