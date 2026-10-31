// PREVIEW MODE: while the backend endpoints are still stubs, the UI falls back
// to the sample data below. Turn on with NEXT_PUBLIC_UI_PREVIEW=1 in frontend/.env.local.
// With it off, nothing here is used and every call goes to the real API.
export const PREVIEW = process.env.NEXT_PUBLIC_UI_PREVIEW === "1";

export type Role = "ADMIN" | "STAFF" | "CUSTOMER";
export type SessionUser = { id: number; name: string; email: string; role: Role };

export const homeFor = (role: Role) => ({ ADMIN: "/admin", STAFF: "/staff", CUSTOMER: "/portal" })[role];

export const previewUsers: Record<Role, SessionUser> = {
  ADMIN: { id: 1, name: "Meera Iyer", email: "admin@example.com", role: "ADMIN" },
  STAFF: { id: 2, name: "Rohan Desai", email: "staff@example.com", role: "STAFF" },
  CUSTOMER: { id: 3, name: "Kavya Nair", email: "customer@example.com", role: "CUSTOMER" },
};

export type InvoiceRow = {
  id: number; number: string; company_name: string; status: string;
  issue_date: string; due_date: string; total: number; balance: number; is_overdue: boolean; days_past_due: number;
};

const co = ["Kaveri Textiles", "Anand Logistics", "Sundaram Foods", "Pearl Diagnostics", "Nilgiri Tea Co.", "Orchid Interiors",
  "Vega Auto Parts", "Marina Exports", "Lotus Learning", "Ashoka Builders", "Tidal Analytics", "Banyan Pharma"];
const sts = ["PAID", "CONFIRMED", "PAID", "CONFIRMED", "DRAFT", "PAID"];

export const previewInvoices: InvoiceRow[] = co.map((company_name, i) => {
  const total = 149900 * (1 + (i % 4)) + i * 3700;
  const status = sts[i % sts.length];
  const overdue = status === "CONFIRMED" && i % 2 === 1;
  const day = 3 + i * 2;
  return {
    id: 1000 + i, number: `INV-${String(481 - i).padStart(6, "0")}`, company_name, status,
    issue_date: `2026-10-${String(day).padStart(2, "0")}`,
    due_date: `2026-${overdue ? "10" : "11"}-${String(Math.min(28, day + 14)).padStart(2, "0")}`,
    total, balance: status === "PAID" ? 0 : total, is_overdue: overdue, days_past_due: overdue ? 4 + i : 0,
  };
});

export const previewKpis = {
  active_subscriptions: 287, mrr: 48215000, collected_this_month: 31840000,
  outstanding: 12476000, overdue_invoices: 14, overdue_amount: 3892500, as_of: "2026-10-31",
};

export const previewMonthly = [
  { m: "May", v: 24100000 }, { m: "Jun", v: 27300000 }, { m: "Jul", v: 29800000 },
  { m: "Aug", v: 28400000 }, { m: "Sep", v: 33100000 }, { m: "Oct", v: 31840000 },
];
