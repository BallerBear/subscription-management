import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Logo } from "@/components/Logo";
import { Reveal, Stagger, StaggerItem, MotionProvider } from "@/components/motion";

const steps = ["Product", "Plan", "Subscription", "Invoice", "Payment", "Report"];

export default function HomePage() {
  return (
    <MotionProvider>
      <main className="mx-auto flex min-h-screen max-w-5xl flex-col px-6 py-8">
        <header className="flex items-center justify-between">
          <Logo />
          <Link href="/login" className="link-u text-sm">Sign in</Link>
        </header>

        <section className="flex flex-1 flex-col justify-center py-20">
          <Reveal>
            <p className="mb-5 text-xs font-medium uppercase tracking-[0.16em] text-accent">Subscription billing</p>
            <h1 className="max-w-3xl text-6xl leading-[1.05] md:text-7xl">
              Bill every customer. <span className="italic text-accent">Once.</span> On time.
            </h1>
            <p className="mt-6 max-w-xl text-lg text-muted">
              Brightloop replaces the spreadsheet: plans, subscriptions, invoices and payments in one calm,
              auditable ledger.
            </p>
            <div className="mt-9 flex gap-3">
              <Link href="/login" className="inline-flex h-11 items-center gap-2 rounded bg-accent px-6 text-sm font-medium text-surface transition-transform hover:-translate-y-0.5">
                Open workspace <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="/signup" className="inline-flex h-11 items-center rounded border border-line bg-surface px-6 text-sm font-medium transition-colors hover:border-ink">
                Customer sign up
              </Link>
            </div>
          </Reveal>
        </section>

        <Stagger className="grid grid-cols-2 gap-px overflow-hidden rounded-md border border-line bg-line md:grid-cols-6">
          {steps.map((s, i) => (
            <StaggerItem key={s} className="bg-surface px-4 py-5">
              <p className="num text-xs text-muted">{String(i + 1).padStart(2, "0")}</p>
              <p className="mt-1 font-display text-lg">{s}</p>
            </StaggerItem>
          ))}
        </Stagger>
      </main>
    </MotionProvider>
  );
}
