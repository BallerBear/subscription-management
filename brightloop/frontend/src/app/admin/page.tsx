"use client";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { OutstandingHero, type Kpis } from "@/components/billing/Hero";
import { InvoiceList } from "@/components/billing/InvoiceList";
import { MonthlyBars } from "@/components/billing/MonthlyBars";
import { PageHeader, Panel, PanelHeader } from "@/components/Panel";
import { Stagger, StaggerItem } from "@/components/motion";
import { previewKpis } from "@/lib/preview";
import { useQuery } from "@/lib/useQuery";
import { useUser } from "@/lib/session";

export default function AdminDashboard() {
  const user = useUser();
  const { data: kpis } = useQuery<Kpis>("/reports/kpis", previewKpis);
  return (
    <Stagger>
      <StaggerItem><PageHeader eyebrow="Admin console" title={`Good to see you, ${user.name.split(" ")[0]}.`} subtitle="Here is where the money stands today." /></StaggerItem>
      <StaggerItem><OutstandingHero kpis={kpis} /></StaggerItem>
      <StaggerItem className="mt-8 grid gap-6 lg:grid-cols-[1fr_1.4fr]">
        <Panel>
          <PanelHeader title="Collections, last six months" />
          <MonthlyBars />
        </Panel>
        <Panel className="flex flex-col justify-between p-6">
          <div>
            <p className="font-display text-2xl">Time Machine</p>
            <p className="mt-2 text-muted">Jump the system date forward and run billing. Run it twice to prove nothing is billed twice.</p>
          </div>
          <Link href="/admin/time-machine" className="link-u mt-6 inline-flex items-center gap-2 self-start text-accent">Open Time Machine <ArrowRight className="h-4 w-4" /></Link>
        </Panel>
      </StaggerItem>
      <StaggerItem className="mt-8">
        <h2 className="mb-3 text-2xl">Latest invoices</h2>
        <InvoiceList limit={6} />
      </StaggerItem>
    </Stagger>
  );
}
