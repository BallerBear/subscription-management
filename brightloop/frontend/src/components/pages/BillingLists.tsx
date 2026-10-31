"use client";
import Link from "next/link";
import { PageHeader } from "../Panel";
import { Reveal } from "../motion";
import { DataList } from "./DataList";
import { formatDate, formatMoney } from "@/lib/money";
import { useBase } from "@/lib/useBase";

type Payment = { id: number; invoice_id: number; invoice_number: string; company_name: string; method: string; amount: number; paid_on: string; reference: string | null };
type Overdue = { id: number; number: string; company_name: string; due_date: string; days_past_due: number; balance: number };

const methodLabel = (m: string) => m.replace("_", " ").toLowerCase().replace(/^\w/, (c) => c.toUpperCase());

export function PaymentsPage() {
  const base = useBase();
  return (
    <Reveal>
      <PageHeader eyebrow="Payments" title="Payments" subtitle="Money received, newest first. Record a payment from the invoice itself." />
      <DataList<Payment> path="/payments" emptyTitle="No payments yet" emptyBody="Open a confirmed invoice and choose Record payment."
        columns={[
          { header: "Paid on", numeric: true, cell: (r) => formatDate(r.paid_on) },
          { header: "Invoice", cell: (r) => <Link href={`${base}/invoices/${r.invoice_id}`} className="num link-u text-accent">{r.invoice_number}</Link> },
          { header: "Customer", cell: (r) => r.company_name },
          { header: "Method", cell: (r) => methodLabel(r.method) },
          { header: "Reference", cell: (r) => <span className="num text-xs text-muted">{r.reference ?? "-"}</span> },
          { header: "Amount", numeric: true, cell: (r) => formatMoney(r.amount) },
        ]}
      />
    </Reveal>
  );
}

export function OverduePage() {
  const base = useBase();
  return (
    <Reveal>
      <PageHeader eyebrow="Collections" title="Overdue invoices" subtitle="Most overdue first. Overdue is worked out from the system date, so the Time Machine moves it." />
      <DataList<Overdue> path="/reports/overdue" emptyTitle="No invoices are overdue. Nice." emptyBody="When one slips past its due date it will show up here."
        columns={[
          { header: "Invoice", cell: (r) => <Link href={`${base}/invoices/${r.id}`} className="num link-u text-accent">{r.number}</Link> },
          { header: "Customer", cell: (r) => r.company_name },
          { header: "Due", numeric: true, cell: (r) => formatDate(r.due_date) },
          { header: "Days overdue", numeric: true, cell: (r) => <span className="text-danger">{r.days_past_due}</span> },
          { header: "Balance", numeric: true, cell: (r) => formatMoney(r.balance) },
        ]}
      />
    </Reveal>
  );
}
