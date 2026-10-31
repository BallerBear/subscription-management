"use client";
import { TimeMachine } from "@/components/billing/TimeMachine";
import { PageHeader } from "@/components/Panel";
import { Reveal } from "@/components/motion";

export default function TimeMachinePage() {
  return (
    <Reveal>
      <PageHeader eyebrow="Admin only" title="Time Machine" subtitle="Move the system date, then run billing. Overdue, dashboards and billing all follow the clock." />
      <TimeMachine />
    </Reveal>
  );
}
