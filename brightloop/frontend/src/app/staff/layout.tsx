import type { ReactNode } from "react";
import { StaffShell } from "@/components/shells/StaffShell";

export default function Layout({ children }: { children: ReactNode }) {
  return <StaffShell>{children}</StaffShell>;
}
