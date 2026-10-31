"use client";
import Link from "next/link";
import { Plus } from "lucide-react";
import { buttonLikeLink } from "./links";
import { PageHeader } from "../Panel";
import { Reveal } from "../motion";
import { StatusDot } from "../StatusDot";
import { DataList, type Filter } from "./DataList";
import { formatDate, formatMoney } from "@/lib/money";
import { useBase } from "@/lib/useBase";

export type SubRow = {
  id: number; number: string; status: string; company_name: string; plan_name: string; billing_period: string;
  next_billing_date: string | null; expiry_date: string; recurring_amount: number;
};
const filters: readonly Filter[] = [
  ["", "All"], ["status=DRAFT", "Draft"], ["status=QUOTATION", "Quotation"], ["status=CONFIRMED", "Confirmed"],
  ["status=ACTIVE", "Active"], ["status=PAUSED", "Paused"], ["status=CLOSED", "Closed"],
];
const per = (p: string) => p.toLowerCase().replace(/ly$/, "").replace("dai", "day");

export function SubscriptionColumns(base: string) {
  return [
    { header: "Number", cell: (r: SubRow) => <Link href={`${base}/subscriptions/${r.id}`} className="num link-u font-medium text-accent">{r.number}</Link> },
    { header: "Customer", cell: (r: SubRow) => r.company_name },
    { header: "Plan", cell: (r: SubRow) => r.plan_name },
    { header: "Status", cell: (r: SubRow) => <StatusDot status={r.status} /> },
    { header: "Next bill", numeric: true, cell: (r: SubRow) => (r.next_billing_date ? formatDate(r.next_billing_date) : "-") },
    { header: "Recurring (ex tax)", numeric: true, cell: (r: SubRow) => <>{formatMoney(r.recurring_amount)}<span className="text-muted"> /{per(r.billing_period)}</span></> },
  ];
}

export function SubscriptionsPage() {
  const base = useBase();
  return (
    <Reveal>
      <PageHeader eyebrow="Subscriptions" title="Subscriptions" subtitle="From quotation to active. Each status change is checked by the database."
        action={<Link href={`${base}/subscriptions/new`} className={buttonLikeLink}><Plus className="h-4 w-4" />New subscription</Link>} />
      <DataList<SubRow> path="/subscriptions" filters={filters} searchLabel="Search number or customer"
        columns={SubscriptionColumns(base)} emptyTitle="No subscriptions here" emptyBody="Try another status, or create a new subscription." />
    </Reveal>
  );
}

export function PortalSubscriptionsPage() {
  const base = useBase();
  return (
    <Reveal>
      <PageHeader eyebrow="Your account" title="My subscriptions" subtitle="What you are subscribed to and when it renews." />
      <DataList<SubRow> path="/portal/subscriptions" columns={SubscriptionColumns(base).filter((c) => c.header !== "Customer")}
        emptyTitle="No subscriptions yet" emptyBody="When Brightloop sets one up for you, it will appear here." />
    </Reveal>
  );
}
