import { ApiError, createPnsiClient, unwrap, type Me } from "@pnsi/api-client";

// Same-origin client: Next.js rewrites /api/* to the FastAPI server.
export const api = createPnsiClient();

export const meQueryKey = ["me"] as const;

// The current user, or null when not signed in. Other failures throw, so the
// shell can show that the API is unavailable instead of pretending to be empty.
export async function fetchMe(): Promise<Me | null> {
  const result = await api.GET("/api/v1/me");
  if (result.response.status === 401) return null;
  return unwrap(result);
}

export { ApiError };
export type { Me };
