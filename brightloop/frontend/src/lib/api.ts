const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

/** Error carrying the server's { message, fields } shape (section 10 of the guide). */
export class ApiError extends Error {
  constructor(message: string, public status: number, public fields?: Record<string, string>) {
    super(message);
  }
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "same-origin",
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });

  if (!response.ok) {
    let body: { message?: string; fields?: Record<string, string> } = {};
    try { body = await response.json(); } catch { /* non-JSON error body */ }
    throw new ApiError(body.message ?? `Request failed (${response.status})`, response.status, body.fields);
  }
  return response.json() as Promise<T>;
}
