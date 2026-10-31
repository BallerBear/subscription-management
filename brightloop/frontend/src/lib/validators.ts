import { z } from "zod";

export function parseWithSchema<T>(schema: z.ZodType<T>, value: unknown): T {
  return schema.parse(value);
}

// Same rules as the server (Pydantic): messages say exactly what to fix.
export const emailField = z.string().trim().min(1, "Enter your email").email("Entered email is invalid");

export const passwordField = z
  .string()
  .min(9, "Password must be more than 8 characters")
  .max(72, "Password must be 72 characters or fewer")
  .regex(/[A-Z]/, "Add at least one uppercase letter")
  .regex(/[a-z]/, "Add at least one lowercase letter")
  .regex(/[^A-Za-z0-9]/, "Add at least one special character");

export const loginSchema = z.object({
  email: emailField,
  password: z.string().min(1, "Enter your password"),
});
export type LoginValues = z.infer<typeof loginSchema>;

export const signupSchema = z.object({
  name: z.string().trim().min(2, "Enter your full name"),
  company_name: z.string().trim().min(2, "Enter your company name"),
  email: emailField,
  password: passwordField,
});
export type SignupValues = z.infer<typeof signupSchema>;
