"use client";
import { useEffect, useState, type ReactNode } from "react";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";
import { Panel } from "../Panel";
import { Table, type Column } from "../Table";
import { EmptyState, ErrorState, TableSkeleton } from "../States";
import { useQuery } from "@/lib/useQuery";
import { cn } from "@/lib/cn";

type Page<T> = { items: T[]; total: number; page: number; page_size: number };
/** [query-string, label], e.g. ["status=DRAFT", "Draft"] or ["", "All"]. */
export type Filter = readonly [string, string];

type Props<T> = {
  path: string;                 // API list endpoint, e.g. "/customers"
  columns: Column<T>[];
  filters?: readonly Filter[];
  searchLabel?: string;         // shows a search box when set
  emptyTitle: string;
  emptyBody?: string;
  pageSize?: number;
  compact?: boolean;            // dashboard widget: no search, no pager
  refreshKey?: number;          // bump to refetch after a create
  toolbar?: ReactNode;
};

/**
 * The one list every screen reuses: server-side paging + search + filter tabs,
 * with loading skeleton, designed empty state and error state with retry.
 * The server does the filtering; this only builds the query string.
 */
export function DataList<T extends { id: number | string }>({
  path, columns, filters, searchLabel, emptyTitle, emptyBody, pageSize = 25, compact, refreshKey = 0, toolbar,
}: Props<T>) {
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  const [filter, setFilter] = useState(filters?.[0]?.[0] ?? "");
  const [page, setPage] = useState(1);

  // wait for a pause in typing before asking the server (one request, not one per key)
  useEffect(() => {
    const t = setTimeout(() => { setDebounced(q); setPage(1); }, 300);
    return () => clearTimeout(t);
  }, [q]);

  const params = new URLSearchParams(filter);
  params.set("page", String(page));
  params.set("page_size", String(pageSize));
  if (debounced) params.set("q", debounced);
  if (refreshKey) params.set("_r", String(refreshKey));

  const { data, error, loading, refetch } = useQuery<Page<T>>(`${path}?${params}`);
  const from = data ? (data.page - 1) * data.page_size + 1 : 0;
  const to = data ? from + data.items.length - 1 : 0;

  return (
    <Panel>
      {(filters || searchLabel || toolbar) && (
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-3">
          {filters ? (
            <div role="tablist" aria-label="Filter" className="flex flex-wrap gap-1">
              {filters.map(([val, label]) => (
                <button key={val || "all"} role="tab" aria-selected={filter === val}
                  onClick={() => { setFilter(val); setPage(1); }}
                  className={cn("rounded px-3 py-1.5 text-sm transition-colors",
                    filter === val ? "bg-ink text-surface" : "text-muted hover:bg-ink/5 hover:text-ink")}>
                  {label}
                </button>
              ))}
            </div>
          ) : <span />}
          <div className="flex items-center gap-3">
            {searchLabel && !compact && (
              <label className="relative">
                <span className="sr-only">{searchLabel}</span>
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
                <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={searchLabel}
                  className="h-9 w-64 rounded border border-line bg-paper pl-9 pr-3 text-sm transition-colors focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20" />
              </label>
            )}
            {toolbar}
          </div>
        </div>
      )}

      {loading && !data ? <TableSkeleton cols={columns.length} /> :
        error ? <ErrorState message={error} onRetry={refetch} /> :
        data && data.items.length === 0 ? <EmptyState title={emptyTitle} body={emptyBody} /> :
        data && <Table columns={columns} rows={data.items} key={`${filter}|${debounced}|${page}`} />}

      {data && data.items.length > 0 && !compact && (
        <div className="flex items-center justify-between border-t border-line px-5 py-3 text-xs text-muted">
          <p className="num">Showing {from}–{to} of {data.total}</p>
          <div className="flex gap-1">
            <button aria-label="Previous page" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}
              className="rounded border border-line p-1.5 hover:border-ink disabled:cursor-not-allowed disabled:opacity-40"><ChevronLeft className="h-4 w-4" /></button>
            <button aria-label="Next page" disabled={to >= data.total} onClick={() => setPage((p) => p + 1)}
              className="rounded border border-line p-1.5 hover:border-ink disabled:cursor-not-allowed disabled:opacity-40"><ChevronRight className="h-4 w-4" /></button>
          </div>
        </div>
      )}
    </Panel>
  );
}
