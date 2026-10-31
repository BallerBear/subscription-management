"use client";
import { useState } from "react";
import { Search } from "lucide-react";
import { Panel } from "../Panel";
import { Table, type Column } from "../Table";
import { StatusDot } from "../StatusDot";
import { EmptyState, ErrorState, TableSkeleton } from "../States";
import { formatDate, formatMoney } from "@/lib/money";
import { previewInvoices, type InvoiceRow } from "@/lib/preview";
import { useQuery } from "@/lib/useQuery";
import { cn } from "@/lib/cn";

type Page = { items: InvoiceRow[]; total: number; page: number; page_size: number };
const filters = [["", "All"], ["DRAFT", "Draft"], ["CONFIRMED", "Confirmed"], ["PAID", "Paid"], ["overdue", "Overdue"]] as const;

/** Shared by admin, staff and (with `portal`) the customer's own invoices. */
export function InvoiceList({ portal = false, limit }: { portal?: boolean; limit?: number }) {
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("");

  // query string is built from filters; the server paginates + filters
  const params = new URLSearchParams({ page: "1", page_size: String(limit ?? 25) });
  if (q) params.set("q", q);
  if (filter === "overdue") params.set("overdue", "true");
  else if (filter) params.set("status", filter);
  const base = portal ? "/portal/invoices" : "/invoices";

  // sample used only in preview mode when the endpoint isn't built yet
  const sample: Page = (() => {
    const items = previewInvoices.filter((r) =>
      (!q || (r.company_name + r.number).toLowerCase().includes(q.toLowerCase())) &&
      (!filter || (filter === "overdue" ? r.is_overdue : r.status === filter)));
    return { items: items.slice(0, limit ?? 25), total: items.length, page: 1, page_size: limit ?? 25 };
  })();

  const { data, error, loading, refetch } = useQuery<Page>(`${base}?${params}`, sample);

  const columns: Column<InvoiceRow>[] = [
    { header: "Invoice", cell: (r) => <span className="num font-medium">{r.number}</span> },
    ...(portal ? [] : [{ header: "Customer", cell: (r: InvoiceRow) => r.company_name }]),
    { header: "Status", cell: (r) => <StatusDot status={r.is_overdue ? "OVERDUE" : r.status} /> },
    { header: "Due", numeric: true, cell: (r) => formatDate(r.due_date) },
    { header: "Total", numeric: true, cell: (r) => formatMoney(r.total) },
    { header: "Balance", numeric: true, cell: (r) => <span className={cn(r.balance === 0 && "text-muted")}>{formatMoney(r.balance)}</span> },
  ];

  return (
    <Panel>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-3">
        <div role="tablist" aria-label="Filter by status" className="flex gap-1">
          {filters.map(([val, label]) => (
            <button key={val} role="tab" aria-selected={filter === val} onClick={() => setFilter(val)}
              className={cn("rounded px-3 py-1.5 text-sm transition-colors", filter === val ? "bg-ink text-surface" : "text-muted hover:bg-ink/5 hover:text-ink")}>
              {label}
            </button>
          ))}
        </div>
        {!limit && (
          <label className="relative">
            <span className="sr-only">Search invoices</span>
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search customer or number"
              className="h-9 w-64 rounded border border-line bg-paper pl-9 pr-3 text-sm transition-colors focus:border-accent focus:outline-none" />
          </label>
        )}
      </div>
      {loading && !data ? <TableSkeleton cols={portal ? 5 : 6} /> :
        error ? <ErrorState message={error} onRetry={refetch} /> :
        data && data.items.length === 0 ? <EmptyState title="No invoices match" body="Try a different filter, or clear the search." /> :
        data && <Table columns={columns} rows={data.items} key={filter + q} />}
      {data && data.items.length > 0 && (
        <p className="num border-t border-line px-5 py-3 text-xs text-muted">Showing {data.items.length} of {data.total}</p>
      )}
    </Panel>
  );
}
