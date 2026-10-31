"use client";
import { PageHeader } from "../Panel";
import { Reveal } from "../motion";
import { DataList, type Filter } from "./DataList";

type Row = {
  id: number; table_name: string; row_id: number; action: string; changed_at: string; changed_by_name: string | null;
  old_data: Record<string, unknown> | null; new_data: Record<string, unknown> | null;
};
const filters: readonly Filter[] = [["", "All"], ["table_name=taxes", "Taxes"], ["table_name=products", "Products"], ["table_name=plans", "Plans"], ["table_name=discounts", "Discounts"]];

// What changed, in words: "price, name" for an UPDATE; the row's name for an INSERT.
function summary(r: Row): string {
  if (r.action === "UPDATE" && r.old_data && r.new_data) {
    const keys = Object.keys(r.new_data).filter((k) => k !== "updated_at" && JSON.stringify(r.old_data![k]) !== JSON.stringify(r.new_data![k]));
    return keys.length ? `Changed ${keys.join(", ")}` : "No visible change";
  }
  const d = r.new_data ?? r.old_data;
  return d && typeof d.name === "string" ? d.name : "";
}

export function AuditPage() {
  return (
    <Reveal>
      <PageHeader eyebrow="Admin only" title="Audit log" subtitle="Who changed the catalog, and when. The database writes these rows itself." />
      <DataList<Row> path="/audit" filters={filters} emptyTitle="Nothing recorded yet" emptyBody="Catalog changes will appear here."
        columns={[
          { header: "When", numeric: true, cell: (r) => new Date(r.changed_at).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" }) },
          { header: "Who", cell: (r) => r.changed_by_name ?? <span className="text-muted">System</span> },
          { header: "Table", cell: (r) => <span className="num text-xs">{r.table_name} #{r.row_id}</span> },
          { header: "Action", cell: (r) => <span className="capitalize">{r.action.toLowerCase()}</span> },
          { header: "Detail", cell: (r) => summary(r) },
        ]}
      />
    </Reveal>
  );
}
