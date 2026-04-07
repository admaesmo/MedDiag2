import { ReactNode } from "react";
import { Sidebar } from "@/components/organisms/sidebar";
import { Topbar } from "@/components/organisms/topbar";

export function PrivateShell({ children, userEmail }: { children: ReactNode; userEmail: string }) {
  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <Sidebar />
      <div className="flex min-h-screen flex-1 flex-col">
        <Topbar userEmail={userEmail} />
        <main id="main-content" className="flex-1 px-4 py-6 lg:px-8 lg:py-10">
          {children}
        </main>
      </div>
    </div>
  );
}
