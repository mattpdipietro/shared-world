const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

/**
 * Fetch wrapper for the FastAPI backend. Always sends the session cookie
 * (`credentials: "include"`) since auth is cookie-based, not a bearer token.
 */
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw new ApiError(response.status, `${init?.method ?? "GET"} ${path} failed: ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

/** Full browser navigation to the backend Discord login endpoint. OAuth
 * redirects must be a top-level navigation, not a `fetch`/XHR call. */
export function goToDiscordLogin(): void {
  window.location.href = `${API_URL}/auth/discord/login`;
}
