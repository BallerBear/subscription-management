"use client";
import type { ReactNode } from "react";
import { FileText, Home, Repeat } from "lucide-react";
import { RoleGuard } from "@/lib/session";
import { Logo } from "../Logo";
import { MotionProvider } from "../motion";
import { TopNav, UserChip, type NavItem } from "./nav";

// CUSTOMER: calm, narrow, top-bar layout. Shows only their own data.
const items: NavItem[] = [
  { href: "/portal", label: "Overview", icon: Home, exact: true },
  { href: "/portal/subscriptions", label: "My subscriptions", icon: Repeat },
  { href: "/portal/invoices", label: "My invoices", icon: FileText },
];

export function PortalShell({ children }: { children: ReactNode }) {
  return (
    <RoleGuard role="CUSTOMER">
      <MotionProvider>
        <div className="min-h-screen">
          <header className="no-print sticky top-0 z-10 border-b border-line bg-surface">
            <div className="mx-auto flex max-w-4xl items-center justify-between gap-6 px-6">
              <Logo />
              <TopNav items={items} />
              <div className="w-48"><UserChip /></div>
            </div>
          </header>
          <main className="mx-auto max-w-4xl px-6 py-12">{children}</main>
        </div>
      </MotionProvider>
    </RoleGuard>
  );
}
