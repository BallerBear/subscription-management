import { z } from "zod";

export type Errors = Record<string, string>;

// These mirror the CHECK constraints in the database.
export const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
export const PHONE_RE = /^[0-9+ -]{7,15}$/;
export const GSTIN_RE = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/;

export const emailSchema = z
  .string()
  .trim()
  .toLowerCase()
  .regex(EMAIL_RE, "Enter a valid email address");

export const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, "Enter your password"),
});

export const signupSchema = z.object({
  name: z.string().trim().min(2, "Enter your full name").max(100, "Use at most 100 characters"),
  email: emailSchema,
  company_name: z.string().trim().min(1, "Enter your company name").max(150, "Use at most 150 characters"),
  password: z.string().min(8, "Use at least 8 characters").max(72, "Use at most 72 characters"),
});

export const phoneSchema = z.string().trim().regex(PHONE_RE, "Enter a valid phone number");
export const gstinSchema = z
  .string()
  .trim()
  .toUpperCase()
  .regex(GSTIN_RE, "Enter a valid 15-character GSTIN");

/** Run a schema and get either clean data or one message per field. */
export function validate<S extends z.ZodTypeAny>(
  schema: S,
  data: unknown,
): { ok: true; data: z.infer<S> } | { ok: false; errors: Errors } {
  const result = schema.safeParse(data);
  if (result.success) return { ok: true, data: result.data };
  const errors: Errors = {};
  for (const issue of result.error.issues) {
    const key = issue.path.join(".") || "_";
    if (!(key in errors)) errors[key] = issue.message;
  }
  return { ok: false, errors };
}
