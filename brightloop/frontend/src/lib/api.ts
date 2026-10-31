const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";
const ACCESS_TOKEN_KEY = "brightloop_access_token";

/** Normalized API error supporting FastAPI's { detail } and field validation errors. */
export class ApiError extends Error {
  status: number;
  detail: string;
  fields?: Record<string, string>;

  constructor(message: string, status: number, fields?: Record<string, string>) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = message;
    this.fields = fields;
  }
}

export function setAccessToken(token: string): void {
  if (typeof window !== "undefined") {
    window.sessionStorage.setItem(ACCESS_TOKEN_KEY, token);
  }
}

export function clearAccessToken(): void {
  if (typeof window !== "undefined") {
    window.sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  }
}

function validationDetails(detail: unknown): { message?: string; fields?: Record<string, string> } {
  if (typeof detail === "string") return { message: detail };
  if (!Array.isArray(detail)) return {};

  const fields: Record<string, string> = {};
  const messages: string[] = [];
  for (const issue of detail) {
    if (!issue || typeof issue !== "object") continue;
    const item = issue as { loc?: unknown[]; msg?: unknown };
    const message = typeof item.msg === "string" ? item.msg : "Invalid value";
    messages.push(message);
    const field = item.loc?.filter((part) => part !== "body").at(-1);
    if (typeof field === "string") fields[field] = message;
  }
  return {
    message: messages[0] ?? "The submitted information is invalid.",
    fields: Object.keys(fields).length ? fields : undefined,
  };
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");

  if (!headers.has("Authorization") && typeof window !== "undefined") {
    const token = window.sessionStorage.getItem(ACCESS_TOKEN_KEY);
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "same-origin",
    ...init,
    headers,
  });

  if (response.status === 204) return undefined as T;

  const contentType = response.headers.get("content-type") ?? "";
  const rawBody = await response.text();
  let body: unknown = rawBody;
  if (rawBody && contentType.includes("application/json")) {
    try {
      body = JSON.parse(rawBody);
    } catch {
      body = rawBody;
    }
  } else if (!rawBody) {
    body = undefined;
  }

  if (!response.ok) {
    const payload = typeof body === "object" && body !== null
      ? body as { detail?: unknown; message?: unknown; fields?: Record<string, string> }
      : undefined;
    const validation = validationDetails(payload?.detail);
    const message = validation.message
      ?? (typeof payload?.message === "string" ? payload.message : undefined)
      ?? (typeof body === "string" && body ? body : undefined)
      ?? `Request failed (${response.status})`;
    throw new ApiError(message, response.status, payload?.fields ?? validation.fields);
  }

  return body as T;
}
