import { AlertTriangle, Inbox } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "./Button";
import { cn } from "@/lib/cn";

/** Shimmering placeholder. Fixed sizes mean numbers never make the layout jump. */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div className={cn("relative overflow-hidden rounded bg-line/60", className)}>
      <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-surface/70 to-transparent" />
    </div>
  );
}

export function TableSkeleton({ rows = 6, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="divide-y divide-line" aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-6 px-5 py-4">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function EmptyState({ title, body, action }: { title: string; body?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center px-6 py-14 text-center">
      <Inbox className="mb-4 h-8 w-8 text-accent" strokeWidth={1.25} aria-hidden />
      <p className="font-display text-xl">{title}</p>
      {body && <p className="mt-1 max-w-sm text-sm text-muted">{body}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center px-6 py-14 text-center">
      <AlertTriangle className="mb-4 h-8 w-8 text-danger" strokeWidth={1.25} aria-hidden />
      <p className="font-display text-xl">Something went wrong</p>
      <p className="mt-1 max-w-sm text-sm text-muted">{message}</p>
      {onRetry && <Button variant="secondary" className="mt-5" onClick={onRetry}>Try again</Button>}
    </div>
  );
}
