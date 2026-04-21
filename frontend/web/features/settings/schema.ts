import { z } from "zod";

export const settingsSchema = z.object({
  displayName: z.string().min(2, "displayNameMin"),
  locale: z.enum(["es", "en", "pt-BR"]),
});

export type SettingsFormValues = z.infer<typeof settingsSchema>;
