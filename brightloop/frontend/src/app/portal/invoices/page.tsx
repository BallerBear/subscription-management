"use client";
import { InvoiceList } from "@/components/billing/InvoiceList";
import { PageHeader } from "@/components/Panel";
import { Reveal } from "@/components/motion";

export default function PortalInvoices() {
  return (
    <Reveal>
      <PageHeader eyebrow="Your account" title="My invoices" />
      <InvoiceList portal />
    </Reveal>
  );
}
