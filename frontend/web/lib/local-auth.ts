"use client";

import { localAuthCookieNames } from "@/lib/local-auth-shared";

const ACCESS_TOKEN_KEY = localAuthCookieNames.accessToken;
const EMAIL_KEY = localAuthCookieNames.email;

export function setLocalSession(accessToken: string, email: string) {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(EMAIL_KEY, email);
  document.cookie = `${ACCESS_TOKEN_KEY}=${encodeURIComponent(accessToken)}; Path=/; Max-Age=28800; SameSite=Lax`;
  document.cookie = `${EMAIL_KEY}=${encodeURIComponent(email)}; Path=/; Max-Age=28800; SameSite=Lax`;
}

export function clearLocalSession() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(EMAIL_KEY);
  document.cookie = `${ACCESS_TOKEN_KEY}=; Path=/; Max-Age=0; SameSite=Lax`;
  document.cookie = `${EMAIL_KEY}=; Path=/; Max-Age=0; SameSite=Lax`;
}

export function getLocalSession() {
  return {
    accessToken: localStorage.getItem(ACCESS_TOKEN_KEY),
    email: localStorage.getItem(EMAIL_KEY) || "",
  };
}
