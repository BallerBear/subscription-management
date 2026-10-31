"use client";
import { motion } from "motion/react";
import { CountUp, EASE } from "../motion";
import { Skeleton } from "../States";
import { formatMoney } from "@/lib/money";
import type { previewKpis } from "@/lib/preview";

export type Kpis = typeof previewKpis;

/** The dashboard leads with ONE number that matters: money still owed, and how much is overdue. */
export function OutstandingHero({ kpis }: { kpis?: Kpis }) {
  if (!kpis) return <Skeleton className="h-52 w-full" />;
  const overduePct = Math.round((kpis.overdue_amount / kpis.outstanding) * 100);
  return (
    <div className="hairline grid gap-8 rounded-md bg-surface p-8 md:grid-cols-[1.4fr_1fr]">
      <div>
        <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">Outstanding</p>
        <p className="num mt-3 text-6xl leading-none tracking-tight">
          <CountUp value={kpis.outstanding} money />
        </p>
        <div className="mt-6">
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-line">
            <motion.div className="h-full bg-danger" initial={{ width: 0 }} animate={{ width: `${overduePct}%` }} transition={{ duration: 1.3, delay: 0.5, ease: EASE }} />
          </div>
          <p className="mt-2 text-sm text-muted">
            <span className="num text-danger">{formatMoney(kpis.overdue_amount, { whole: true })}</span> of this is overdue
            <span className="num"> ({overduePct}%)</span> across <span className="num">{kpis.overdue_invoices}</span> invoices.
          </p>
        </div>
      </div>
      <dl className="grid grid-cols-1 content-center gap-5 border-t border-line pt-6 md:border-l md:border-t-0 md:pl-8 md:pt-0">
        {[
          ["Collected this month", <CountUp key="c" value={kpis.collected_this_month} money whole />],
          ["Monthly recurring revenue", <CountUp key="m" value={kpis.mrr} money whole />],
          ["Active subscriptions", <CountUp key="a" value={kpis.active_subscriptions} />],
        ].map(([label, value]) => (
          <div key={String(label)} className="flex items-baseline justify-between gap-4">
            <dt className="text-sm text-muted">{label}</dt>
            <dd className="num text-lg">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
