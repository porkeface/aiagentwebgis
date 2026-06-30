const BASE_URL = "/api/v1";

export class APIError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = "APIError";
    this.status = status;
    this.detail = detail;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  token?: string | null;
}

/**
 * Build an Authorization header for the currently-logged-in user, if any.
 * Returns an empty object when no token is present so it can be spread
 * into a headers Record unconditionally.
 */
export function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, headers = {}, token } = options;

  const url = `${BASE_URL}${path}`;

  // Don't set Content-Type on GET/HEAD (triggers unnecessary CORS preflight).
  const initHeaders: Record<string, string> = { ...headers };
  if (body !== undefined && !initHeaders["Content-Type"]) {
    initHeaders["Content-Type"] = "application/json";
  }

  const init: RequestInit = {
    method,
    headers: initHeaders,
  };

  if (token) {
    (init.headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  } else if (initHeaders["Authorization"]) {
    // authHeaders() already set it via spread; nothing to do.
  } else {
    // Fall back to the current user's token from localStorage.
    const bearer = authHeaders()["Authorization"];
    if (bearer) (init.headers as Record<string, string>)["Authorization"] = bearer;
  }

  if (body !== undefined) {
    init.body = JSON.stringify(body);
  }

  let response: Response;
  try {
    response = await fetch(url, init);
  } catch (err) {
    throw new APIError(0, `Network error: ${err instanceof Error ? err.message : String(err)}`);
  }

  if (!response.ok) {
    let detail: unknown;
    try {
      detail = await response.json();
    } catch {
      // ignore parse error
    }
    const rawMessage =
      detail && typeof detail === "object" && "detail" in detail
        ? (detail as { detail: unknown }).detail
        : `Request failed with status ${response.status}`;
    const message = formatErrorMessage(rawMessage, response.status);
    throw new APIError(response.status, message, detail);
  }

  // 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

/**
 * FastAPI 422 returns `detail` as an array of {loc, msg, type} objects.
 * String(arr) would yield "[object Object]" — extract a readable message.
 */
function formatErrorMessage(raw: unknown, status: number): string {
  if (typeof raw === "string") return raw;
  if (Array.isArray(raw) && raw.length > 0) {
    const first = raw[0];
    if (first && typeof first === "object" && "msg" in first) {
      return String((first as { msg: unknown }).msg);
    }
  }
  if (raw && typeof raw === "object") {
    try {
      return JSON.stringify(raw);
    } catch {
      return `Request failed with status ${status}`;
    }
  }
  return `Request failed with status ${status}`;
}

// Late import to avoid circular dep with auth.ts which imports request().
import { getToken } from "./auth";
