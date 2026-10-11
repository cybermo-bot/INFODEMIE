// Typed client for the PNSI API. Types come from `schema.d.ts`, generated from
// the FastAPI OpenAPI schema with `make api-client`. Never edit schema.d.ts by hand.
import createClient, { type Middleware } from "openapi-fetch";

import type { components, paths } from "./schema";

export type { components, paths };
export type Schemas = components["schemas"];
export type Me = Schemas["MeOut"];
export type ApiErrorBody = Schemas["ErrorBody"];

export const CSRF_COOKIE = "pnsi_csrf";
export const CSRF_HEADER = "X-CSRF-Token";
const UNSAFE = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export function readCookie(name: string, cookieString?: string): string | undefined {
  const source = cookieString ?? (typeof document === "undefined" ? "" : document.cookie);
  for (const part of source.split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === name) return decodeURIComponent(rest.join("="));
  }
  return undefined;
}

// Echo the CSRF cookie in a header on unsafe requests (double submit, decision D13).
export const csrfMiddleware: Middleware = {
  onRequest({ request }) {
    if (UNSAFE.has(request.method.toUpperCase())) {
      const token = readCookie(CSRF_COOKIE);
      if (token) request.headers.set(CSRF_HEADER, token);
    }
    return request;
  },
};

export interface ClientOptions {
  // Empty string means same origin: the web app proxies /api to FastAPI.
  baseUrl?: string;
  headers?: Record<string, string>;
  fetch?: typeof fetch;
}

export function createPnsiClient(options: ClientOptions = {}) {
  const client = createClient<paths>({
    baseUrl: options.baseUrl ?? "",
    credentials: "include",
    headers: options.headers,
    fetch: options.fetch,
  });
  client.use(csrfMiddleware);
  return client;
}

export type PnsiClient = ReturnType<typeof createPnsiClient>;

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: ApiErrorBody | undefined,
  ) {
    super(body?.message ?? `HTTP ${status}`);
    this.name = "ApiError";
  }
}

// Unwrap an openapi-fetch result: return data or throw a typed ApiError.
export function unwrap<T>(result: {
  data?: T;
  error?: unknown;
  response: Response;
}): T {
  if (result.error !== undefined || !result.response.ok) {
    const err = result.error as { error?: ApiErrorBody } | undefined;
    throw new ApiError(result.response.status, err?.error);
  }
  // `undefined` only for bodiless responses such as 204.
  return result.data as T;
}
