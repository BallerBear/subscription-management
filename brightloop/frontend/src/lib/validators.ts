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

// ---- Customers (same rules as backend/app/schemas/people.py) ----
const phone = z.string().trim().regex(/^[0-9+ -]{7,15}$/, "Phone must be 7-15 digits (spaces, + and - allowed)").or(z.literal(""));
const gstin = z.string().trim().toUpperCase()
  .regex(/^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/, "GSTIN must look like 33AABCK1234F1Z5").or(z.literal(""));

export const customerSchema = z.object({
  company_name: z.string().trim().min(1, "Enter the company name"),
  contact_name: z.string().trim().min(2, "Enter the contact's full name"),
  email: emailField,
  phone,
  city: z.string().trim(),
  state: z.string().trim(),
  gstin,
});
export type CustomerValues = z.infer<typeof customerSchema>;

// ---- Staff accounts (admin only) ----
export const staffSchema = z.object({
  name: z.string().trim().min(2, "Enter the staff member's full name"),
  email: emailField,
  password: passwordField,
});
export type StaffValues = z.infer<typeof staffSchema>;

// ---- Payments: the form takes rupees, the API takes paise (converted on submit) ----
export const paymentSchema = z.object({
  method: z.enum(["CARD", "UPI", "BANK_TRANSFER", "CASH", "CHEQUE"]),
  amount: z.coerce.number({ invalid_type_error: "Enter the amount in rupees" }).positive("Enter an amount above zero"),
  paid_on: z.string().min(1, "Choose the payment date"),
  reference: z.string().trim().max(100, "Use at most 100 characters"),
});
export type PaymentValues = z.infer<typeof paymentSchema>;

// ---- Subscriptions ----
export const subscriptionSchema = z.object({
  customer_id: z.coerce.number().int().min(1, "Choose a customer"),
  plan_id: z.coerce.number().int().min(1, "Choose a plan"),
  payment_term_id: z.coerce.number().int().min(1, "Choose payment terms"),
  start_date: z.string().min(1, "Choose a start date"),
  expiry_date: z.string().min(1, "Choose an expiry date"),
  lines: z.array(z.object({
    product_id: z.coerce.number().int().min(1, "Choose a product"),
    variant_id: z.coerce.number().int().optional(),
    quantity: z.coerce.number().int().min(1, "Quantity must be at least 1"),
  })).min(1, "Add at least one product"),
}).refine((v) => v.expiry_date > v.start_date, { path: ["expiry_date"], message: "Expiry date must be after the start date" });
export type SubscriptionValues = z.infer<typeof subscriptionSchema>;
