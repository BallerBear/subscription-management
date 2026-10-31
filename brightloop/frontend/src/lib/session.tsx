"use client";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { apiRequest } from "./api";
import { PREVIEW, homeFor, previewUsers, type Role, type SessionUser } from "./preview";

const Ctx = createContext<SessionUser | null>(null);
export const useUser = () => useContext(Ctx)!;

/**
 * Wraps a whole role area. Asks the server who we are (the JWT lives in an
 * httpOnly cookie, so JS never sees it), then:
 *   not logged in -> /login      wrong role -> that user's own home
 * This is only UX: the API itself enforces roles with require_role.
 */
export function RoleGuard({ role, children }: { role: Role; children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<SessionUser | null>(null);

  useEffect(() => {
    const preview = PREVIEW ? sessionStorage.getItem("preview_role") : null; // preview only, never real auth
    apiRequest<SessionUser>("/auth/me")
      .then((u) => (u.role === role ? setUser(u) : router.replace(homeFor(u.role))))
      .catch(() => {
        if (PREVIEW && preview === role) setUser(previewUsers[role]);
        else if (PREVIEW && preview) router.replace(homeFor(preview as Role));
        else router.replace("/login");
      });
  }, [role, router]);

  if (!user) return <div className="min-h-screen bg-paper" aria-busy="true" />;
  return <Ctx.Provider value={user}>{children}</Ctx.Provider>;
}

export async function logout(router: ReturnType<typeof useRouter>) {
  try { await apiRequest("/auth/logout", { method: "POST" }); } catch { /* preview */ }
  sessionStorage.removeItem("preview_role");
  router.replace("/login");
}
