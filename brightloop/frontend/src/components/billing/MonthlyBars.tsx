"use client";
import { motion } from "motion/react";
import { EASE } from "../motion";
import { formatMoney } from "@/lib/money";
import { previewMonthly } from "@/lib/preview";

// Hand-built bars (no chart library): bars grow up from the baseline, staggered.
export function MonthlyBars({ data = previewMonthly }: { data?: typeof previewMonthly }) {
  const max = Math.max(...data.map((d) => d.v));
  return (
    <div className="flex h-56 items-end gap-4 px-5 pb-5 pt-8">
      {data.map((d, i) => {
        const last = i === data.length - 1;
        return (
          <div key={d.m} className="group flex h-full flex-1 flex-col justify-end gap-2">
            <p className="num text-center text-xs text-muted opacity-0 transition-opacity group-hover:opacity-100">{formatMoney(d.v, { whole: true })}</p>
            <motion.div className={last ? "rounded-t-sm bg-accent" : "rounded-t-sm bg-accent/25 transition-colors group-hover:bg-accent/60"}
              style={{ originY: 1, height: `${(d.v / max) * 100}%` }}
              initial={{ scaleY: 0 }} animate={{ scaleY: 1 }} transition={{ duration: 0.9, delay: 0.3 + i * 0.08, ease: EASE }} />
            <p className="text-center text-xs text-muted">{d.m}</p>
          </div>
        );
      })}
    </div>
  );
}
