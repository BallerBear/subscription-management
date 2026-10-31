"use client";
import Link from "next/link";
import { DataList, type Filter } from "../pages/DataList";
import type { Column } from "../Table";
import { StatusDot } from "../StatusDot";
import { formatDate, formatMoney } from "@/lib/money";
import type { InvoiceRow } from "@/lib/preview";
import { useBase } from "@/lib/useBase";
import { cn } from "@/lib/cn";

const filters: readonly Filter[] = [
  ["", "All"], ["status=DRAFT", "Draft"], ["status=CONFIRMED", "Confirmed"], ["status=PAID", "Paid"], ["overdue=true", "Overdue"],
];
const portalFilters: readonly Filter[] = [["", "All"], ["status=CONFIRMED", "Confirmed"], ["status=PAID", "Paid"], ["overdue=true", "Overdue"]];

/** Shared by admin, staff and (with `portal`) the customer's own invoices. */
export function InvoiceList({ portal = false, limit }: { portal?: boolean; limit?: number }) {
  const base = useBase();

  const columns: Column<InvoiceRow>[] = [
    { header: "Invoice", cell: (r) => <Link href={`${base}/invoices/${r.id}`} className="num link-u font-medium text-accent">{r.number}</Link> },
    ...(portal ? [] : [{ header: "Customer", cell: (r: InvoiceRow) => r.company_name }]),
    { header: "Status", cell: (r) => <StatusDot status={r.is_overdue ? "OVERDUE" : r.status} /> },
    { header: "Due", numeric: true, cell: (r) => formatDate(r.due_date) },
    { header: "Total", numeric: true, cell: (r) => formatMoney(r.total) },
    { header: "Balance", numeric: true, cell: (r) => <span className={cn(r.balance === 0 && "text-muted")}>{formatMoney(r.balance)}</span> },
  ];

  return (
    <DataList<InvoiceRow>
      path={portal ? "/portal/invoices" : "/invoices"}
      columns={columns}
      filters={limit ? undefined : portal ? portalFilters : filters}
      searchLabel={portal ? undefined : "Search customer or number"}
      pageSize={limit ?? 25}
      compact={!!limit}
      emptyTitle="No invoices match"
      emptyBody="Try a different filter, or clear the search."
    />
  );
}
