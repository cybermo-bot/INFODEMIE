export type Entity = {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  institution: string;
  [key: string]: any;
};
export type PageResult = {
  items: Entity[];
  total: number;
  next_cursor: number | null;
};
export async function api<T = any>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token =
    typeof window !== "undefined" ? sessionStorage.getItem("pnsi-token") : null;
  const r = await fetch("/api/v1" + path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: "Bearer " + token } : {}),
      ...options.headers,
    },
  });
  if (!r.ok) {
    const d = await r
      .json()
      .catch(() => ({ message: "Connection unavailable" }));
    if (r.status === 401)
      window.dispatchEvent(new Event("pnsi-session-expired"));
    throw new Error(d.message || JSON.stringify(d.detail) || "Request failed");
  }
  return r.json();
}
export const post = (
  path: string,
  body: any,
  headers: Record<string, string> = {},
) => api(path, { method: "POST", body: JSON.stringify(body), headers });
export const patch = (kind: string, item: Entity, data: any) =>
  api("/" + kind + "/" + item.id, {
    method: "PATCH",
    body: JSON.stringify({ expected_version: item.version, data }),
  });
export const review = (
  path: string,
  item: Entity,
  decision: string,
  rationale: string,
) => post(path, { expected_version: item.version, decision, rationale });
