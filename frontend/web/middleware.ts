import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { isLocalAuthEnabled } from "@/lib/auth-mode";
import { localAuthCookieNames } from "@/lib/local-auth-shared";
import { updateSession } from "@/lib/supabase/middleware";

export async function middleware(request: NextRequest) {
  if (isLocalAuthEnabled) {
    const pathname = request.nextUrl.pathname;
    const token = request.cookies.get(localAuthCookieNames.accessToken)?.value;
    const isAuthRoute = pathname.startsWith("/login") || pathname.startsWith("/register");
    const isPrivateRoute =
      pathname.startsWith("/dashboard") ||
      pathname.startsWith("/parkinson") ||
      pathname.startsWith("/history") ||
      pathname.startsWith("/settings");

    if (!token && isPrivateRoute) {
      const url = request.nextUrl.clone();
      url.pathname = "/login";
      url.searchParams.set("next", pathname);
      return NextResponse.redirect(url);
    }

    if (token && isAuthRoute) {
      const url = request.nextUrl.clone();
      url.pathname = "/dashboard";
      url.searchParams.delete("next");
      return NextResponse.redirect(url);
    }

    return NextResponse.next();
  }

  return updateSession(request);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
