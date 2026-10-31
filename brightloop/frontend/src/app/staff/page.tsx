"use client";
import { Check, Play } from "lucide-react";
import { useState } from "react";
import { InvoiceList } from "@/components/billing/InvoiceList";
import { Button } from "@/components/Button";
import { PageHeader, Panel } from "@/components/Panel";
import { CountUp, Stagger, StaggerItem } from "@/components/motion";
import { apiRequest } from "@/lib/api";
import { PREVIEW } from "@/lib/preview";
import { useUser } from "@/lib/session";

// Staff home is a work queue, not a report: what needs doing today.
export default function StaffToday() {
  const user = useUser();
  const [drafts, setDrafts] = useState(5);
  const [busy, setBusy] = useState(false);

  async function confirmAll() {
    setBusy(true);
    try { await apiRequest("/invoices/confirm-drafts", { method: "POST" }); setDrafts(0); }
    catch { if (PREVIEW) { await new Promise((r) => setTimeout(r, 600)); setDrafts(0); } }
    setBusy(false);
  }

  return (
    <Stagger>
      <StaggerItem><PageHeader eyebrow="Staff workspace" title={`Today, ${user.name.split(" ")[0]}.`} subtitle="What needs your attention." /></StaggerItem>
      <StaggerItem className="grid gap-6 md:grid-cols-2">
        <Panel className="p-6">
          <p className="text-xs uppercase tracking-[0.14em] text-muted">Drafts to confirm</p>
          <p className="num mt-3 text-5xl"><CountUp value={drafts} key={drafts} /></p>
          <Button className="mt-6" variant="secondary" loading={busy} disabled={drafts === 0} icon={<Check className="h-4 w-4" />} onClick={confirmAll}>
            {drafts === 0 ? "All confirmed" : "Confirm all drafts"}
          </Button>
        </Panel>
        <Panel className="p-6">
          <p className="text-xs uppercase tracking-[0.14em] text-muted">Billing</p>
          <p className="mt-3 font-display text-2xl">Create this period&apos;s invoices.</p>
          <p className="mt-1 text-sm text-muted">Safe to run any time; already-billed periods are skipped.</p>
          <Button className="mt-5" icon={<Play className="h-4 w-4" />} onClick={() => apiRequest("/billing/run", { method: "POST", body: "{}" }).catch(() => {})}>Run billing</Button>
        </Panel>
      </StaggerItem>
      <StaggerItem className="mt-8">
        <h2 className="mb-3 text-2xl">Recent invoices</h2>
        <InvoiceList limit={6} />
      </StaggerItem>
    </Stagger>
  );
}
