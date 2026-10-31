import { Hammer } from "lucide-react";
import { PageHeader, Panel } from "./Panel";
import { Reveal } from "./motion";

/** Placeholder for a screen another teammate is still building. */
export function Stub({ eyebrow, title, body }: { eyebrow: string; title: string; body: string }) {
  return (
    <Reveal>
      <PageHeader eyebrow={eyebrow} title={title} />
      <Panel>
        <div className="flex flex-col items-center px-6 py-16 text-center">
          <Hammer className="mb-4 h-8 w-8 text-accent" strokeWidth={1.25} aria-hidden />
          <p className="font-display text-xl">Coming together</p>
          <p className="mt-1 max-w-sm text-sm text-muted">{body}</p>
        </div>
      </Panel>
    </Reveal>
  );
}
