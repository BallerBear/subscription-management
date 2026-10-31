"use client";
import type { ReactNode } from "react";
import { AlarmClock, CalendarClock, FileText, LayoutDashboard, Package, Repeat, ShieldCheck, Users, UsersRound, Wallet } from "lucide-react";
import { RoleGuard } from "@/lib/session";
import { Logo } from "../Logo";
import { MotionProvider } from "../motion";
import { SideNav, UserChip, type NavItem } from "./nav";

// ADMIN: the full control room. Dark ink sidebar so it feels distinct from staff.
const items: NavItem[] = [
  { href: "/admin", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { href: "/admin/subscriptions", label: "Subscriptions", icon: Repeat },
  { href: "/admin/invoices", label: "Invoices", icon: FileText },
  { href: "/admin/payments", label: "Payments", icon: Wallet },
  { href: "/admin/overdue", label: "Overdue", icon: AlarmClock },
  { href: "/admin/customers", label: "Customers", icon: Users },
  { href: "/admin/catalog", label: "Catalog", icon: Package },
  { href: "/admin/time-machine", label: "Time Machine", icon: CalendarClock },
  { href: "/admin/team", label: "Staff accounts", icon: UsersRound },
  { href: "/admin/audit", label: "Audit log", icon: ShieldCheck },
];

export function AdminShell({ children }: { children: ReactNode }) {
  return (
    <RoleGuard role="ADMIN">
      <MotionProvider>
        <div className="min-h-screen lg:grid lg:grid-cols-[256px_1fr]">
          <aside className="no-print flex flex-col gap-8 bg-ink px-4 py-6 text-surface lg:sticky lg:top-0 lg:h-screen">
            <div className="px-3"><Logo invert /><p className="mt-1 text-[11px] uppercase tracking-[0.16em] text-surface/40">Admin console</p></div>
            <div className="flex-1 overflow-y-auto"><SideNav items={items} dark group="admin" /></div>
            <div className="border-t border-surface/10 pt-4"><UserChip dark /></div>
          </aside>
          <main className="px-6 py-10 lg:px-12"><div className="mx-auto max-w-6xl">{children}</div></main>
        </div>
      </MotionProvider>
    </RoleGuard>
  );
}

