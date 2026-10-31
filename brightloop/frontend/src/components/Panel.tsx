import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export function Panel({ children, className }: { children: ReactNode; className?: string }) {
  return <section className={cn("hairline rounded-md bg-surface", className)}>{children}</section>;
}

export function PanelHeader({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <header className="flex items-center justify-between border-b border-line px-5 py-3.5">
      <h2 className="font-display text-lg">{title}</h2>
      {action}
    </header>
  );
}

export function PageHeader({ eyebrow, title, subtitle, action }: { eyebrow?: string; title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow && <p className="mb-2 text-xs font-medium uppercase tracking-[0.14em] text-accent">{eyebrow}</p>}
        <h1 className="text-4xl leading-tight">{title}</h1>
        {subtitle && <p className="mt-2 max-w-xl text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}
