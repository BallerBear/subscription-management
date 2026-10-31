"use client";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { InvoiceList } from "@/components/billing/InvoiceList";
import { PageHeader, Panel } from "@/components/Panel";
import { CountUp, Stagger, StaggerItem } from "@/components/motion";
import { StatusDot } from "@/components/StatusDot";
import { formatDate } from "@/lib/money";
import { useUser } from "@/lib/session";

export default function PortalHome() {
  const user = useUser();
  return (
    <Stagger>
      <StaggerItem><PageHeader eyebrow="Your account" title={`Hello, ${user.name.split(" ")[0]}.`} subtitle="Your subscriptions and invoices, all in one place." /></StaggerItem>
      <StaggerItem className="grid gap-6 md:grid-cols-2">
        <Panel className="p-6">
          <p className="text-xs uppercase tracking-[0.14em] text-muted">Amount due</p>
          <p className="num mt-3 text-5xl"><CountUp value={449700} money /></p>
          <p className="mt-3 text-sm text-muted">Next due <span className="num text-ink">{formatDate("2026-11-14")}</span></p>
          <Link href="/portal/invoices" className="link-u mt-5 inline-flex items-center gap-2 text-accent">View invoices <ArrowRight className="h-4 w-4" /></Link>
        </Panel>
        <Panel className="p-6">
          <p className="text-xs uppercase tracking-[0.14em] text-muted">Your subscription</p>
          <p className="mt-3 font-display text-2xl">Business Suite, monthly</p>
          <div className="mt-2"><StatusDot status="ACTIVE" /></div>
          <p className="mt-3 text-sm text-muted">Renews <span className="num text-ink">{formatDate("2026-11-01")}</span></p>
        </Panel>
      </StaggerItem>
      <StaggerItem className="mt-10">
        <h2 className="mb-3 text-2xl">Recent invoices</h2>
        <InvoiceList portal limit={5} />
      </StaggerItem>
    </Stagger>
  );
}
