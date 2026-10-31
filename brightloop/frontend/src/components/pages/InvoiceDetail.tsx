"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useForm, type Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Printer, Send, Wallet } from "lucide-react";
import { Button } from "../Button";
import { Input, Select } from "../Field";
import { Reveal } from "../motion";
import { StatusDot } from "../StatusDot";
import { ErrorState, Skeleton } from "../States";
import { ApiError, apiRequest } from "@/lib/api";
import { formatDate, formatMoney } from "@/lib/money";
import { useBase } from "@/lib/useBase";
import { useQuery } from "@/lib/useQuery";
import { paymentSchema, type PaymentValues } from "@/lib/validators";

type Line = { id: number; description: string; quantity: number; unit_price: number; discount_amount: number; tax_name: string; tax_rate_bps: number; line_subtotal: number; tax_amount: number; line_total: number };
type Detail = {
  id: number; number: string; status: string; company_name: string; contact_name: string; email: string; phone: string | null;
  address_line: string | null; city: string | null; state: string | null; postal_code: string | null; country: string; gstin: string | null;
  subscription_number: string; period_start: string; period_end: string; issue_date: string; due_date: string; sent_at: string | null;
  subtotal: number; discount_total: number; tax_total: number; total: number; amount_paid: number; balance: number;
  is_overdue: boolean; days_past_due: number; lines: Line[];
  payments: { id: number; method: string; amount: number; paid_on: string; reference: string | null }[];
  transitions: { to_status: string; action_label: string }[];
};

const METHODS: [string, string][] = [["UPI", "UPI"], ["CARD", "Card"], ["BANK_TRANSFER", "Bank transfer"], ["CASH", "Cash"], ["CHEQUE", "Cheque"]];
const methodLabel = (m: string) => METHODS.find(([v]) => v === m)?.[1] ?? m;

function PaymentForm({ invoice, today, onDone }: { invoice: Detail; today: string; onDone: () => void }) {
  const [formError, setFormError] = useState("");
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<PaymentValues>({
    resolver: zodResolver(paymentSchema) as Resolver<PaymentValues>, mode: "onBlur",
    defaultValues: { method: "UPI", amount: invoice.balance / 100, paid_on: today, reference: "" },
  });
  async function onSubmit(v: PaymentValues) {
    setFormError("");
    try {
      await apiRequest(`/invoices/${invoice.id}/payments`, {
        method: "POST",
        // the form is in rupees; the API (and the database) only ever see whole paise
        body: JSON.stringify({ ...v, amount: Math.round(v.amount * 100), reference: v.reference || null }),
      });
      onDone();
    } catch (e) {
      if (e instanceof ApiError && e.fields && Object.keys(e.fields).length) {
        Object.entries(e.fields).forEach(([f, message]) => setError(f as keyof PaymentValues, { message }));
      }
      setFormError(e instanceof Error ? e.message : "Could not record the payment.");
    }
  }
  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="no-print hairline mb-8 grid gap-4 rounded-md bg-surface p-5 md:grid-cols-4">
      <Select label="Method" error={errors.method?.message} {...register("method")}>{METHODS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select>
      <Input label="Amount (₹)" type="number" step="0.01" error={errors.amount?.message} {...register("amount")} />
      <Input label="Paid on" type="date" max={today} error={errors.paid_on?.message} {...register("paid_on")} />
      <Input label="Reference" hint="Optional" error={errors.reference?.message} {...register("reference")} />
      <div className="flex items-center justify-end gap-3 md:col-span-4">
        {formError && <p role="alert" className="mr-auto text-sm text-danger">{formError}</p>}
        <Button type="button" variant="ghost" onClick={onDone}>Cancel</Button>
        <Button type="submit" loading={isSubmitting}>Record payment</Button>
      </div>
    </form>
  );
}

/** Staff see actions; customers (portal) see the same print-ready paper, read only. */
export function InvoiceDetail({ portal = false }: { portal?: boolean }) {
  const { id } = useParams<{ id: string }>();
  const base = useBase();
  const { data: inv, error, loading, refetch } = useQuery<Detail>(portal ? `/portal/invoices/${id}` : `/invoices/${id}`);
  const clock = useQuery<{ today: string }>(portal ? null : "/clock");
  const [paying, setPaying] = useState(false);
  const [busy, setBusy] = useState("");
  const [actionError, setActionError] = useState("");
  const [note, setNote] = useState("");

  async function act(key: string, path: string, body?: object) {
    setBusy(key); setActionError(""); setNote("");
    try { await apiRequest(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }); if (key === "send") setNote("Marked as sent."); refetch(); }
    catch (e) { setActionError(e instanceof Error ? e.message : "That didn't work."); }
    setBusy("");
  }

  if (error) return <ErrorState message={error} onRetry={refetch} />;
  if (loading && !inv) return <Skeleton className="h-[40rem] w-full" />;
  if (!inv) return null;
  const address = [inv.address_line, inv.city, inv.state, inv.postal_code].filter(Boolean).join(", ");

  return (
    <Reveal>
      <div className="no-print mb-6 flex flex-wrap items-center justify-between gap-3">
        <Link href={`${base}/invoices`} className="inline-flex items-center gap-2 text-sm text-muted hover:text-ink"><ArrowLeft className="h-4 w-4" />All invoices</Link>
        <div className="flex flex-wrap gap-2">
          {!portal && inv.transitions.map((t) => (
            <Button key={t.to_status} variant={t.to_status === "CANCELLED" ? "danger" : "primary"} loading={busy === t.to_status}
              onClick={() => act(t.to_status, `/invoices/${id}/transition`, { to_status: t.to_status })}>{t.action_label}</Button>
          ))}
          {!portal && inv.status === "CONFIRMED" && inv.balance > 0 && !paying && clock.data && (
            <Button icon={<Wallet className="h-4 w-4" />} onClick={() => setPaying(true)}>Record payment</Button>)}
          {!portal && (inv.status === "CONFIRMED" || inv.status === "PAID") && (
            <Button variant="secondary" icon={<Send className="h-4 w-4" />} loading={busy === "send"} onClick={() => act("send", `/invoices/${id}/send`)}>
              {inv.sent_at ? "Send again" : "Send"}</Button>)}
          <Button variant="secondary" icon={<Printer className="h-4 w-4" />} onClick={() => window.print()}>Print</Button>
        </div>
      </div>
      {actionError && <p role="alert" className="no-print mb-4 rounded border border-danger/30 bg-danger/5 px-4 py-3 text-sm text-danger">{actionError}</p>}
      {note && <p className="no-print mb-4 text-sm text-accent">{note}</p>}
      {paying && clock.data && <PaymentForm invoice={inv} today={clock.data.today} onDone={() => { setPaying(false); refetch(); }} />}

      {/* The paper: this is what prints. */}
      <article className="hairline mx-auto max-w-3xl rounded-md bg-surface p-8 md:p-12 print:border-0 print:p-0">
        <header className="flex flex-wrap items-start justify-between gap-6 border-b border-line pb-6">
          <div>
            <p className="font-display text-2xl">Brightloop Software</p>
            <p className="mt-1 text-sm text-muted">Subscription invoice</p>
          </div>
          <div className="text-right">
            <p className="num text-2xl font-medium">{inv.number}</p>
            <div className="mt-1 flex justify-end"><StatusDot status={inv.is_overdue ? "OVERDUE" : inv.status} /></div>
          </div>
        </header>

        <section className="grid gap-6 border-b border-line py-6 text-sm sm:grid-cols-2">
          <div>
            <p className="mb-1 text-xs uppercase tracking-[0.14em] text-muted">Billed to</p>
            <p className="font-medium">{inv.company_name}</p>
            <p>{inv.contact_name}</p>
            {address && <p className="text-muted">{address}</p>}
            {inv.gstin && <p className="num mt-1 text-xs">GSTIN {inv.gstin}</p>}
          </div>
          <dl className="space-y-1 sm:text-right">
            {([["Issued", formatDate(inv.issue_date)], ["Due", formatDate(inv.due_date)],
               ["Period", `${formatDate(inv.period_start)} – ${formatDate(inv.period_end)}`], ["Subscription", inv.subscription_number]] as const).map(([k, v]) => (
              <div key={k} className="flex justify-between gap-6 sm:justify-end"><dt className="text-muted">{k}</dt><dd className="num min-w-32">{v}</dd></div>
            ))}
          </dl>
        </section>

        <table className="mt-6 w-full text-sm">
          <thead><tr className="border-b border-line text-left text-xs uppercase tracking-wider text-muted">
            <th className="py-2 font-medium">Description</th><th className="py-2 text-right font-medium">Qty</th>
            <th className="py-2 text-right font-medium">Rate</th><th className="py-2 text-right font-medium">Discount</th>
            <th className="py-2 text-right font-medium">Tax</th><th className="py-2 text-right font-medium">Amount</th></tr></thead>
          <tbody>
            {inv.lines.map((l) => (
              <tr key={l.id} className="border-b border-line/70">
                <td className="py-3 pr-3">{l.description}</td>
                <td className="num py-3 text-right">{l.quantity}</td>
                <td className="num py-3 text-right">{formatMoney(l.unit_price)}</td>
                <td className="num py-3 text-right text-muted">{l.discount_amount ? `-${formatMoney(l.discount_amount)}` : "-"}</td>
                <td className="num py-3 text-right text-muted">{l.tax_rate_bps / 100}%</td>
                <td className="num py-3 text-right">{formatMoney(l.line_subtotal - l.discount_amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <dl className="num ml-auto mt-6 w-full max-w-xs space-y-1.5 text-sm">
          <div className="flex justify-between"><dt className="text-muted">Subtotal</dt><dd>{formatMoney(inv.subtotal)}</dd></div>
          {inv.discount_total > 0 && <div className="flex justify-between"><dt className="text-muted">Discounts</dt><dd>-{formatMoney(inv.discount_total)}</dd></div>}
          <div className="flex justify-between"><dt className="text-muted">Tax</dt><dd>{formatMoney(inv.tax_total)}</dd></div>
          <div className="flex justify-between border-t border-line pt-2 text-lg font-medium"><dt>Total</dt><dd>{formatMoney(inv.total)}</dd></div>
          <div className="flex justify-between"><dt className="text-muted">Paid</dt><dd>{formatMoney(inv.amount_paid)}</dd></div>
          <div className={`flex justify-between text-base font-medium ${inv.balance > 0 && inv.is_overdue ? "text-danger" : ""}`}><dt>Balance due</dt><dd>{formatMoney(inv.balance)}</dd></div>
          {inv.is_overdue && <p className="text-right text-xs text-danger">{inv.days_past_due} days overdue</p>}
        </dl>

        {inv.payments.length > 0 && (
          <section className="mt-8 border-t border-line pt-5 text-sm">
            <p className="mb-2 text-xs uppercase tracking-[0.14em] text-muted">Payments received</p>
            {inv.payments.map((p) => (
              <div key={p.id} className="flex justify-between py-1">
                <span><span className="num">{formatDate(p.paid_on)}</span> · {methodLabel(p.method)}{p.reference && <span className="num text-xs text-muted"> · {p.reference}</span>}</span>
                <span className="num">{formatMoney(p.amount)}</span>
              </div>
            ))}
          </section>
        )}
      </article>
    </Reveal>
  );
}
