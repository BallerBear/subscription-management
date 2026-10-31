import { cn } from "@/lib/cn";

// Status = text label + coloured dot (not rainbow pills).
const tone: Record<string, { dot: string; label: string }> = {
  DRAFT: { dot: "bg-muted/60", label: "Draft" },
  QUOTATION: { dot: "bg-muted/60", label: "Quotation" },
  CONFIRMED: { dot: "bg-ink", label: "Confirmed" },
  ACTIVE: { dot: "bg-accent", label: "Active" },
  PAID: { dot: "bg-accent", label: "Paid" },
  PAUSED: { dot: "bg-warn", label: "Paused" },
  OVERDUE: { dot: "bg-danger", label: "Overdue" },
  CANCELLED: { dot: "bg-muted/60", label: "Cancelled" },
  CLOSED: { dot: "bg-muted/60", label: "Closed" },
};

export function StatusDot({ status }: { status: string }) {
  const t = tone[status] ?? { dot: "bg-muted/60", label: status };
  const live = status === "OVERDUE" || status === "ACTIVE";
  return (
    <span className="inline-flex items-center gap-2 text-sm">
      <span className={cn("h-2 w-2 rounded-full", t.dot, live && "animate-pulseDot")} aria-hidden />
      {t.label}
    </span>
  );
}
