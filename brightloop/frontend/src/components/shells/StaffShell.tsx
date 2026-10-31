"use client";
import type { ReactNode } from "react";
import { AlarmClock, FileText, LayoutDashboard, Repeat, Users, Wallet } from "lucide-react";
import { RoleGuard } from "@/lib/session";
import { Logo } from "../Logo";
import { MotionProvider } from "../motion";
import { SideNav, UserChip, type NavItem } from "./nav";

// STAFF: day-to-day billing work. Light sidebar, no catalog/clock/users/audit.
const items: NavItem[] = [
  { href: "/staff", label: "Today", icon: LayoutDashboard, exact: true },
  { href: "/staff/customers", label: "Customers", icon: Users },
  { href: "/staff/subscriptions", label: "Subscriptions", icon: Repeat },
  { href: "/staff/invoices", label: "Invoices", icon: FileText },
  { href: "/staff/payments", label: "Payments", icon: Wallet },
  { href: "/staff/overdue", label: "Overdue", icon: AlarmClock },
];

export function StaffShell({ children }: { children: ReactNode }) {
  return (
    <RoleGuard role="STAFF">
      <MotionProvider>
        <div className="min-h-screen lg:grid lg:grid-cols-[240px_1fr]">
          <aside className="no-print flex flex-col gap-8 border-r border-line bg-surface px-4 py-6 lg:sticky lg:top-0 lg:h-screen">
            <div className="px-3"><Logo /><p className="mt-1 text-[11px] uppercase tracking-[0.16em] text-muted">Staff workspace</p></div>
            <div className="flex-1 overflow-y-auto"><SideNav items={items} group="staff" /></div>
            <div className="border-t border-line pt-4"><UserChip /></div>
          </aside>
          <main className="px-6 py-10 lg:px-12"><div className="mx-auto max-w-6xl">{children}</div></main>
        </div>
      </MotionProvider>
    </RoleGuard>
  );
}
