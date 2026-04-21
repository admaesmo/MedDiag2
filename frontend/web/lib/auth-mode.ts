export const isLocalAuthEnabled = process.env.NEXT_PUBLIC_AUTH_MODE === "local";

export const localAuthDefaults = {
  email: process.env.NEXT_PUBLIC_LOCAL_AUTH_EMAIL || "demo@meddiag.local",
  password: process.env.NEXT_PUBLIC_LOCAL_AUTH_PASSWORD || "meddiag123",
  role: process.env.NEXT_PUBLIC_LOCAL_AUTH_ROLE || "patient",
  displayName: process.env.NEXT_PUBLIC_LOCAL_AUTH_DISPLAY_NAME || "Demo Local",
};
