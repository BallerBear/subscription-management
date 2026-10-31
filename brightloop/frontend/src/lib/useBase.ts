"use client";
import { useUser } from "./session";

/** "/admin", "/staff" or "/portal": the URL prefix for the logged-in role's screens. */
export function useBase(): string {
  const role = useUser().role;
  return role === "ADMIN" ? "/admin" : role === "STAFF" ? "/staff" : "/portal";
}
