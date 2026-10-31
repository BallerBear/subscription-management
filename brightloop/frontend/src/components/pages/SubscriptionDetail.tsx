"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { Button } from "../Button";
import { Select } from "../Field";
import { PageHeader, Panel, PanelHeader } from "../Panel";
import { Reveal } from "../motion";
import { StatusDot } from "../StatusDot";
import { ErrorState, Skeleton } from "../States";
import { Table } from "../Table";
import { apiRequest } from "@/lib/api";
import { formatDate, formatMoney } from "@/lib/money";
import { useBase } from "@/lib/useBase";
import { useQuery } from "@/lib/useQuery";

type Line = { id: number; description: string; quantity: number; unit_price: number; tax_name: string; tax_rate_bps: number; line_subtotal: number; line_tax: number };
type Detail = {
  id: number; number: string; status: string; company_name: string; plan_name: string; billing_period: string; payment_term: string;
  start_date: string; expiry_date: string; next_billing_date: string | null;
  lines: Line[]; events: { id?: number; from_status: string | null; to_status: string; changed_at: string; changed_by_name: string | null }[];
  discounts: { id: number; name: string; type: string; value: number }[]; transitions: { to_status: string; action_label: string }[];
};

const discountText = (d: { type: string; value: number }) => (d.type === "PERCENT" ? `${d.value / 100}% off` : `${formatMoney(d.value)} off`);

export function SubscriptionDetail({ portal = false }: { portal?: boolean }) {
  const { id } = useParams<{ id: string }>();
  const base = useBase();
  const { data, error, loading, refetch } = useQuery<Detail>(portal ? `/portal/subscriptions/${id}` : `/subscriptions/${id}`);
  const lookups = useQuery<{ discounts: { id: number; name: string; type: string; value: number }[] }>(portal ? null : "/lookups");
  const [busy, setBusy] = useState("");
  const [actionError, setActionError] = useState("");
  const [pick, setPick] = useState("");

  async function act(key: string, path: string, init: RequestInit) {
    setBusy(key); setActionError("");
    try { await apiRequest(path, init); refetch(); setPick(""); }
    catch (e) { setActionError(e instanceof Error ? e.message : "That didn't work."); }
    setBusy("");
  }

  if (error) return <ErrorState message={error} onRetry={refetch} />;
  if (loading && !data) return <Skeleton className="h-96 w-full" />;
  if (!data) return null;
  const subtotal = data.lines.reduce((s, l) => s + l.line_subtotal, 0);
  const tax = data.lines.reduce((s, l) => s + l.line_tax, 0);
  const free = (lookups.data?.discounts ?? []).filter((d) => !data.discounts.some((x) => x.id === d.id));

  return (
    <Reveal>
      <Link href={`${base}/subscriptions`} className="no-print mb-4 inline-flex items-center gap-2 text-sm text-muted hover:text-ink"><ArrowLeft className="h-4 w-4" />All subscriptions</Link>
      <PageHeader eyebrow={data.company_name} title={data.number} subtitle={`${data.plan_name}, ${data.payment_term}`}
        action={<div className="flex flex-col items-end gap-3"><StatusDot status={data.status} />
          {!portal && <div className="flex flex-wrap justify-end gap-2">
            {data.transitions.map((t) => (
              <Button key={t.to_status} variant={t.to_status === "CLOSED" ? "danger" : "primary"} loading={busy === t.to_status}
                onClick={() => act(t.to_status, `/subscriptions/${id}/transition`, { method: "POST", body: JSON.stringify({ to_status: t.to_status }) })}>{t.action_label}</Button>
            ))}
          </div>}</div>} />
      {actionError && <p role="alert" className="mb-4 rounded border border-danger/30 bg-danger/5 px-4 py-3 text-sm text-danger">{actionError}</p>}

      <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <Panel>
          <PanelHeader title="What is billed each period" />
          <Table rows={data.lines} columns={[
            { header: "Item", cell: (l) => l.description },
            { header: "Qty", numeric: true, cell: (l) => l.quantity },
            { header: "Unit price", numeric: true, cell: (l) => formatMoney(l.unit_price) },
            { header: "Tax", numeric: true, cell: (l) => <span className="text-muted">{l.tax_name}</span> },
            { header: "Amount", numeric: true, cell: (l) => formatMoney(l.line_subtotal) },
          ]} />
          <dl className="num space-y-1 border-t border-line px-5 py-4 text-right text-sm">
            <div className="flex justify-between"><dt className="text-muted">Subtotal</dt><dd>{formatMoney(subtotal)}</dd></div>
            <div className="flex justify-between"><dt className="text-muted">Tax</dt><dd>{formatMoney(tax)}</dd></div>
            <div className="flex justify-between text-base font-medium"><dt>Per period</dt><dd>{formatMoney(subtotal + tax)}</dd></div>
          </dl>
        </Panel>

        <div className="space-y-6">
          <Panel>
            <PanelHeader title="Dates" />
            <dl className="space-y-2 p-5 text-sm">
              {([["Starts", data.start_date], ["Expires", data.expiry_date], ["Next invoice", data.next_billing_date]] as const).map(([k, v]) => (
                <div key={k} className="flex justify-between"><dt className="text-muted">{k}</dt><dd className="num">{v ? formatDate(v) : "-"}</dd></div>
              ))}
            </dl>
          </Panel>
          <Panel>
            <PanelHeader title="Discounts" />
            <div className="space-y-3 p-5 text-sm">
              {data.discounts.length === 0 && <p className="text-muted">No discounts attached.</p>}
              {data.discounts.map((d) => (
                <div key={d.id} className="flex items-center justify-between"><span>{d.name} <span className="text-muted">({discountText(d)})</span></span>
                  {!portal && <button className="text-xs text-danger hover:underline" onClick={() => act(`rm${d.id}`, `/subscriptions/${id}/discounts/${d.id}`, { method: "DELETE" })}>Remove</button>}
                </div>
              ))}
              {!portal && free.length > 0 && (
                <div className="flex items-end gap-2 border-t border-line pt-3">
                  <div className="flex-1"><Select label="Attach a discount" value={pick} onChange={(e) => setPick(e.target.value)}>
                    <option value="">Choose…</option>{free.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</Select></div>
                  <Button variant="secondary" disabled={!pick} loading={busy === "add"}
                    onClick={() => act("add", `/subscriptions/${id}/discounts`, { method: "POST", body: JSON.stringify({ discount_id: Number(pick) }) })}>Attach</Button>
                </div>
              )}
            </div>
          </Panel>
          <Panel>
            <PanelHeader title="History" />
            <ol className="space-y-3 p-5 text-sm">
              {data.events.map((e, i) => (
                <li key={i} className="flex justify-between gap-3">
                  <span>{e.from_status ? `${e.from_status.toLowerCase()} → ` : ""}<strong className="font-medium">{e.to_status.toLowerCase()}</strong>
                    {e.changed_by_name && <span className="text-muted"> by {e.changed_by_name}</span>}</span>
                  <span className="num text-xs text-muted">{formatDate(e.changed_at.slice(0, 10))}</span>
                </li>
              ))}
            </ol>
          </Panel>
        </div>
      </div>
    </Reveal>
  );
}
