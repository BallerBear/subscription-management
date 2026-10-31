"use client";
import { InvoiceList } from "@/components/billing/InvoiceList";
import { PageHeader } from "@/components/Panel";
import { Reveal } from "@/components/motion";

export default function AdminInvoices() {
  return (
    <Reveal>
      <PageHeader eyebrow="Billing" title="Invoices" subtitle="Confirm, send and chase every invoice." />
      <InvoiceList />
    </Reveal>
  );
}
