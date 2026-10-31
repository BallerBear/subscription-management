"use client";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { InvoiceList } from "@/components/billing/InvoiceList";
import { PageHeader, Panel } from "@/components/Panel";
import { CountUp, Stagger, StaggerItem } from "@/components/motion";
import { StatusDot } from "@/components/StatusDot";
import { formatDate } from "@/lib/money";
import { useUser } from "@/lib/session";
import { useQuery } from "@/lib/useQuery";

export default function PortalHome() {
  const user = useUser();
  const { data } = useQuery<{ amount_due: number; next_due: string | null; overdue_count: number;
    subscription: { id: number; number: string; status: string; next_billing_date: string | null; plan_name: string; billing_period: string } | null }>("/portal/summary");
  return (
    <Stagger>
      <StaggerItem><PageHeader eyebrow="Your account" title={`Hello, ${user.name.split(" ")[0]}.`} subtitle="Your subscriptions and invoices, all in one place." /></StaggerItem>
      <StaggerItem className="grid gap-6 md:grid-cols-2">
        <Panel className="p-6">
          <p className="text-xs uppercase tracking-[0.14em] text-muted">Amount due</p>
          <p className="num mt-3 text-5xl"><CountUp key={data?.amount_due ?? 0} value={data?.amount_due ?? 0} money /></p>
          <p className="mt-3 text-sm text-muted">{data?.next_due ? <>Oldest due <span className="num text-ink">{formatDate(data.next_due)}</span>{data.overdue_count > 0 && <span className="text-danger">, {data.overdue_count} overdue</span>}</> : "You are all paid up."}</p>
          <Link href="/portal/invoices" className="link-u mt-5 inline-flex items-center gap-2 text-accent">View invoices <ArrowRight className="h-4 w-4" /></Link>
        </Panel>
        <Panel className="p-6">
          <p className="text-xs uppercase tracking-[0.14em] text-muted">Your subscription</p>
          {data?.subscription ? <>
            <Link href={`/portal/subscriptions/${data.subscription.id}`} className="link-u mt-3 inline-block font-display text-2xl">{data.subscription.plan_name}</Link>
            <div className="mt-2"><StatusDot status={data.subscription.status} /></div>
            {data.subscription.next_billing_date && <p className="mt-3 text-sm text-muted">Next invoice <span className="num text-ink">{formatDate(data.subscription.next_billing_date)}</span></p>}
          </> : <p className="mt-3 text-muted">No active subscription yet.</p>}
        </Panel>
      </StaggerItem>
      <StaggerItem className="mt-10">
        <h2 className="mb-3 text-2xl">Recent invoices</h2>
        <InvoiceList portal limit={5} />
      </StaggerItem>
    </Stagger>
  );
}
