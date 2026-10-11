import type { ReactNode } from "react";

// Isolates a run of text whose direction may differ from the page: emails,
// identifiers, URLs, Arabizi or mixed-language content (spec §12).
export function Bidi({ children }: { children: ReactNode }) {
  return <bdi dir="auto">{children}</bdi>;
}
