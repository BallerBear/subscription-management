import { cn } from "@/lib/cn";

export function Logo({ className, invert }: { className?: string; invert?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      {/* a loop: two arcs closing a circle, the billing cycle */}
      <svg width="26" height="26" viewBox="0 0 26 26" fill="none" aria-hidden>
        <circle cx="13" cy="13" r="10" stroke={invert ? "#FBF9F4" : "#1E5C3A"} strokeWidth="2" strokeDasharray="46 17" strokeLinecap="round" />
        <circle cx="13" cy="13" r="3" fill={invert ? "#FBF9F4" : "#1E5C3A"} />
      </svg>
      <span className="font-display text-xl tracking-tight">Brightloop</span>
    </span>
  );
}
