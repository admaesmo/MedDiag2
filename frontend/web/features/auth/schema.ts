import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("invalidEmail"),
  password: z.string().min(6, "minPassword6"),
});

export const registerSchema = loginSchema.extend({
  password: z.string().min(8, "minPassword8"),
});

export type LoginValues = z.infer<typeof loginSchema>;
export type RegisterValues = z.infer<typeof registerSchema>;
