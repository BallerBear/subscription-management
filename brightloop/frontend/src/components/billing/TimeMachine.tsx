"use client";
import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { CalendarPlus, Play } from "lucide-react";
import { Button } from "../Button";
import { Panel, PanelHeader } from "../Panel";
import { EASE } from "../motion";
import { ApiError, apiRequest } from "@/lib/api";
import { formatDate } from "@/lib/money";
import { PREVIEW } from "@/lib/preview";

type Run = { created: number; skipped: number; closed: number; up_to_date: number; as_of: string };

const addDays = (iso: string, n: number) => new Date(Date.parse(iso) + n * 864e5).toISOString().slice(0, 10);

/** Admin only. Move "today", run billing, run it again, and watch the second run create nothing. */
export function TimeMachine() {
  const [today, setToday] = useState("2026-10-31");
  const [run, setRun] = useState<Run | null>(null);
  const [runs, setRuns] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [pulse, setPulse] = useState(0);

  async function advance(days: number) {
    setError("");
    try {
      const r = await apiRequest<{ today: string }>("/clock/advance", { method: "POST", body: JSON.stringify({ days }) });
      setToday(r.today);
    } catch (e) {
      if (PREVIEW) setToday((t) => addDays(t, days));
      else setError(e instanceof ApiError ? e.message : "Could not move the clock.");
    }
    setPulse((p) => p + 1); setRun(null); setRuns(0);
  }

  async function runBilling() {
    setBusy(true); setError("");
    try {
      setRun(await apiRequest<Run>("/billing/run", { method: "POST", body: JSON.stringify({ auto_confirm: true }) }));
    } catch (e) {
      if (PREVIEW) { // simulate the idempotent engine: first run bills, repeat runs find nothing
        await new Promise((r) => setTimeout(r, 900));
        setRun(runs === 0 ? { created: 38, skipped: 0, closed: 2, up_to_date: 249, as_of: today } : { created: 0, skipped: 0, closed: 0, up_to_date: 287, as_of: today });
      } else setError(e instanceof ApiError ? e.message : "Billing failed. Nothing was changed.");
    }
    setRuns((n) => n + 1); setBusy(false);
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
      <Panel>
        <PanelHeader title="System date" />
        <div className="px-6 py-8">
          <p className="text-xs uppercase tracking-[0.14em] text-muted">Today, according to Brightloop</p>
          <AnimatePresence mode="wait">
            <motion.p key={today + pulse} initial={{ opacity: 0, y: 18, filter: "blur(4px)" }} animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              exit={{ opacity: 0, y: -18 }} transition={{ duration: 0.45, ease: EASE }} className="num mt-3 text-5xl tracking-tight">
              {formatDate(today)}
            </motion.p>
          </AnimatePresence>
          <div className="mt-8 flex flex-wrap gap-2">
            {[[1, "+1 day"], [7, "+1 week"], [30, "+1 month"], [90, "+3 months"]].map(([d, label]) => (
              <Button key={label} variant="secondary" icon={<CalendarPlus className="h-4 w-4" />} onClick={() => advance(d as number)}>{label}</Button>
            ))}
          </div>
        </div>
      </Panel>

      <Panel>
        <PanelHeader title="Billing run" />
        <div className="px-6 py-8">
          <Button onClick={runBilling} loading={busy} icon={<Play className="h-4 w-4" />} className="w-full">Run billing</Button>
          {error && <p role="alert" className="mt-4 text-sm text-danger">{error}</p>}
          <AnimatePresence mode="wait">
            {run && (
              <motion.div key={runs} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: EASE }} className="mt-6">
                <p className="font-display text-3xl">
                  {run.created === 0 ? "Nothing to bill." : `${run.created} new invoices.`}
                </p>
                <p className="mt-2 text-muted">
                  <span className="num">{run.up_to_date}</span> subscriptions already up to date
                  {run.closed > 0 && <>, <span className="num">{run.closed}</span> closed at expiry</>}.
                </p>
                {run.created === 0 && runs > 1 && (
                  <p className="mt-4 border-l-2 border-accent pl-3 text-sm text-accent">Run again and again: no subscription is ever billed twice.</p>
                )}
                <p className="num mt-4 text-xs text-muted">As of {formatDate(run.as_of)}</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </Panel>
    </div>
  );
}
