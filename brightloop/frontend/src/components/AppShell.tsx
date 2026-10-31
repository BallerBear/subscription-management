"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type CurrentUser } from "@/lib/api";

function Mark() {
  return (
    <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true">
      <circle cx="13" cy="13" r="9" fill="none" stroke="currentColor" strokeWidth="3" />
      <circle cx="22" cy="13" r="3.2" fill="var(--signal)" />
    </svg>
  );
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    api<CurrentUser>("/auth/me")
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setChecked(true));
  }, []);

  async function logout() {
    await api("/auth/logout", { method: "POST" }).catch(() => null);
    setUser(null);
    router.push("/login");
    router.refresh();
  }

  return (
    <div className="shell">
      <header className="topbar">
        <Link href="/" className="brand">
          <Mark />
          <span>Brightloop</span>
        </Link>
        <nav className="topnav" aria-label="Account">
          {!checked ? null : user ? (
            <>
              <span className="whoami">
                {user.name} <span className="role">{user.role.toLowerCase()}</span>
              </span>
              <button className="btn btn-quiet" onClick={logout}>
                Log out
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="link">
                Log in
              </Link>
              <Link href="/signup" className="btn btn-primary">
                Create account
              </Link>
            </>
          )}
        </nav>
      </header>
      <main className="content">{children}</main>
    </div>
  );
}
