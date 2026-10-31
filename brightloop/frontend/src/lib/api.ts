const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

/** Normalized API error supporting both FastAPI's { detail } and field errors. */
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

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "same-origin",
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (response.status === 204) return undefined as T;

  const contentType = response.headers.get("content-type") ?? "";
  const body: unknown = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const payload = typeof body === "object" && body !== null
      ? body as { detail?: unknown; message?: unknown; fields?: Record<string, string> }
      : undefined;
    const detail = typeof payload?.detail === "string"
      ? payload.detail
      : typeof payload?.message === "string"
        ? payload.message
        : typeof body === "string" && body
          ? body
          : `Request failed (${response.status})`;
    throw new ApiError(detail, response.status, payload?.fields);
  }

  return body as T;
}
