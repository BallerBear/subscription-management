"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { motion } from "motion/react";
import { LogOut, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";
import { logout, useUser } from "@/lib/session";
import { EASE } from "../motion";

export type NavItem = { href: string; label: string; icon: LucideIcon; exact?: boolean };

const isActive = (path: string, i: NavItem) => (i.exact ? path === i.href : path === i.href || path.startsWith(i.href + "/"));

/** Vertical nav (admin + staff). A shared-layout pill slides between items. */
export function SideNav({ items, dark, group }: { items: NavItem[]; dark?: boolean; group: string }) {
  const path = usePathname();
  return (
    <nav aria-label="Main" className="flex flex-col gap-0.5">
      {items.map((item, i) => {
        const active = isActive(path, item);
        return (
          <motion.div key={item.href} initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.1 + i * 0.045, ease: EASE }}>
            <Link href={item.href} aria-current={active ? "page" : undefined}
              className={cn("group relative flex items-center gap-3 rounded px-3 py-2.5 text-sm transition-colors",
                dark ? (active ? "text-surface" : "text-surface/60 hover:text-surface") : active ? "text-accent" : "text-muted hover:text-ink")}>
              {active && (
                <motion.span layoutId={`pill-${group}`} transition={{ type: "spring", stiffness: 420, damping: 36 }}
                  className={cn("absolute inset-0 rounded", dark ? "bg-surface/10" : "bg-accent-soft")} />
              )}
              {active && <motion.span layoutId={`bar-${group}`} className={cn("absolute left-0 top-2 bottom-2 w-0.5 rounded", dark ? "bg-surface" : "bg-accent")} />}
              <item.icon className="relative h-4 w-4 transition-transform duration-300 group-hover:translate-x-0.5" strokeWidth={1.6} aria-hidden />
              <span className="relative">{item.label}</span>
            </Link>
          </motion.div>
        );
      })}
    </nav>
  );
}

/** Horizontal nav (customer portal). Underline slides between tabs. */
export function TopNav({ items }: { items: NavItem[] }) {
  const path = usePathname();
  return (
    <nav aria-label="Main" className="flex gap-1">
      {items.map((item) => {
        const active = isActive(path, item);
        return (
          <Link key={item.href} href={item.href} aria-current={active ? "page" : undefined}
            className={cn("relative px-3 py-4 text-sm transition-colors", active ? "text-ink" : "text-muted hover:text-ink")}>
            {item.label}
            {active && <motion.span layoutId="portal-underline" className="absolute inset-x-3 bottom-0 h-0.5 bg-accent" transition={{ type: "spring", stiffness: 420, damping: 36 }} />}
          </Link>
        );
      })}
    </nav>
  );
}

export function UserChip({ dark }: { dark?: boolean }) {
  const user = useUser();
  const router = useRouter();
  return (
    <div className={cn("flex items-center gap-3 text-sm", dark ? "text-surface" : "text-ink")}>
      <span className={cn("flex h-8 w-8 items-center justify-center rounded-full text-xs font-medium", dark ? "bg-surface/15" : "bg-accent-soft text-accent")} aria-hidden>
        {user.name.split(" ").map((p) => p[0]).join("").slice(0, 2)}
      </span>
      <div className="min-w-0 flex-1 leading-tight">
        <p className="truncate font-medium">{user.name}</p>
        <p className={cn("text-xs capitalize", dark ? "text-surface/50" : "text-muted")}>{user.role.toLowerCase()}</p>
      </div>
      <button onClick={() => logout(router)} aria-label="Log out" title="Log out"
        className={cn("rounded p-2 transition-colors", dark ? "hover:bg-surface/10" : "hover:bg-ink/5")}>
        <LogOut className="h-4 w-4" strokeWidth={1.6} />
      </button>
    </div>
  );
}
