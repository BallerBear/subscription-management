"use client";
import type { ReactNode } from "react";
import { motion } from "motion/react";
import { Logo } from "./Logo";
import { CountUp, EASE, MotionProvider, Reveal } from "./motion";

/** Split screen for login/signup: ink brand panel (with a live-feeling figure) + form. */
export function AuthFrame({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <MotionProvider>
      <div className="grid min-h-screen lg:grid-cols-2">
        <aside className="relative hidden overflow-hidden bg-ink p-12 text-surface lg:flex lg:flex-col lg:justify-between">
          <Logo invert />
          {/* slowly rotating ring: the "loop" */}
          <motion.svg aria-hidden viewBox="0 0 400 400" className="absolute -right-24 top-1/4 h-[460px] w-[460px] opacity-[0.12]"
            animate={{ rotate: 360 }} transition={{ duration: 80, repeat: Infinity, ease: "linear" }}>
            <circle cx="200" cy="200" r="180" fill="none" stroke="#FBF9F4" strokeWidth="1.5" strokeDasharray="6 10" />
            <circle cx="200" cy="200" r="120" fill="none" stroke="#FBF9F4" strokeWidth="1.5" />
            <circle cx="200" cy="20" r="7" fill="#FBF9F4" />
          </motion.svg>
          <div className="relative">
            <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3, duration: 0.8 }}
              className="text-xs uppercase tracking-[0.16em] text-surface/50">Billed this month</motion.p>
            <p className="num mt-2 text-6xl text-surface"><CountUp value={31840000} money whole duration={2} /></p>
            <motion.div initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ delay: 0.6, duration: 1.2, ease: EASE }}
              style={{ originX: 0 }} className="mt-6 h-px w-40 bg-surface/40" />
            <p className="mt-6 max-w-sm font-display text-2xl leading-snug text-surface/90">Every subscription billed once, on time, and never twice.</p>
          </div>
        </aside>
        <main className="flex items-center justify-center px-6 py-12">
          <Reveal className="w-full max-w-sm">
            <div className="mb-8 lg:hidden"><Logo /></div>
            <h1 className="text-4xl">{title}</h1>
            <p className="mb-8 mt-2 text-muted">{subtitle}</p>
            {children}
          </Reveal>
        </main>
      </div>
    </MotionProvider>
  );
}
