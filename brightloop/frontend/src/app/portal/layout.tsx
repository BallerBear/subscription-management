import type { ReactNode } from "react";
import { PortalShell } from "@/components/shells/PortalShell";

export default function Layout({ children }: { children: ReactNode }) {
  return <PortalShell>{children}</PortalShell>;
}
