"use client";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { apiRequest, clearAccessToken } from "./api";
import { PREVIEW, homeFor, previewUsers, type Role, type SessionUser } from "./preview";

const Ctx = createContext<SessionUser | null>(null);
export const useUser = () => useContext(Ctx)!;

/**
 * Checks the current bearer token and protects each role-specific workspace.
 * This is a frontend navigation guard; the API independently enforces roles.
 */
export function RoleGuard({ role, children }: { role: Role; children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<SessionUser | null>(null);

  useEffect(() => {
    let active = true;
    const preview = PREVIEW ? sessionStorage.getItem("preview_role") : null;

    apiRequest<SessionUser>("/auth/me")
      .then((currentUser) => {
        if (!active) return;
        if (currentUser.role === role) setUser(currentUser);
        else router.replace(homeFor(currentUser.role));
      })
      .catch(() => {
        if (!active) return;
        if (PREVIEW && preview === role) setUser(previewUsers[role]);
        else if (PREVIEW && preview) router.replace(homeFor(preview as Role));
        else router.replace("/login");
      });

    return () => {
      active = false;
    };
  }, [role, router]);

  if (!user) return <div className="min-h-screen bg-paper" aria-busy="true" />;
  return <Ctx.Provider value={user}>{children}</Ctx.Provider>;
}

export function logout(router: ReturnType<typeof useRouter>) {
  clearAccessToken();
  sessionStorage.removeItem("preview_role");
  router.replace("/login");
}
