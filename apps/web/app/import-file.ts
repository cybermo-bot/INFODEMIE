export type ImportRow = {
  text: string;
  language?: string;
  topic?: string;
  published_at?: string;
};

/** RFC 4180 quoted fields; French semicolon CSV is accepted explicitly. */
export function parseImportFile(input: string, filename: string): ImportRow[] {
  input = input.replace(/^\uFEFF/, "");
  if (new TextEncoder().encode(input).length > 2_000_000)
    throw new Error("Fichier limité à 2 Mo.");
  let records: unknown;
  if (filename.toLowerCase().endsWith(".json")) records = JSON.parse(input);
  else if (filename.toLowerCase().endsWith(".csv")) {
    const firstLine = input.split(/\r?\n/)[0];
    const separator = firstLine.includes(";") ? ";" : ",";
    const rows: string[][] = [];
    let row: string[] = [],
      field = "",
      quoted = false,
      closed = false;
    for (let i = 0; i < input.length; i++) {
      const c = input[i];
      if (quoted) {
        if (c === '"' && input[i + 1] === '"') {
          field += '"';
          i++;
        } else if (c === '"') {
          quoted = false;
          closed = true;
        } else field += c;
      } else if (c === separator) {
        row.push(field);
        field = "";
        closed = false;
      } else if (c === "\n" || c === "\r") {
        if (c === "\r" && input[i + 1] === "\n") i++;
        row.push(field);
        if (row.some((v) => v !== "")) rows.push(row);
        row = [];
        field = "";
        closed = false;
      } else if (c === '"' && field === "" && !closed) quoted = true;
      else if (closed || c === '"')
        throw new Error(
          "CSV invalide : guillemets ou contenu après un champ fermé.",
        );
      else field += c;
      if (rows.length > 501) throw new Error("500 éléments maximum.");
    }
    if (quoted) throw new Error("CSV invalide : guillemets non fermés.");
    row.push(field);
    if (row.some((v) => v !== "")) rows.push(row);
    const header = rows.shift()?.map((v) => v.trim());
    if (
      !header?.includes("text") ||
      new Set(header).size !== header.length ||
      header.some(
        (v) => !["text", "language", "topic", "published_at"].includes(v),
      )
    )
      throw new Error(
        "Colonnes attendues : text (obligatoire), language, topic, published_at. Les autres colonnes ne sont pas importées.",
      );
    records = rows.map((r, i) => {
      if (r.length !== header.length)
        throw new Error(`Ligne ${i + 2} : nombre de colonnes incorrect.`);
      return Object.fromEntries(
        header.flatMap((k, j) => (r[j] !== "" ? [[k, r[j]]] : [])),
      );
    });
  } else throw new Error("Choisis un fichier .csv ou .json.");
  if (!Array.isArray(records) || records.length === 0 || records.length > 500)
    throw new Error("Le fichier doit contenir de 1 à 500 éléments.");
  for (const [i, value] of records.entries()) {
    if (
      !value ||
      typeof value !== "object" ||
      Array.isArray(value) ||
      typeof value.text !== "string" ||
      !value.text.trim()
    )
      throw new Error(`Élément ${i + 1} : un champ text non vide est requis.`);
    if (
      Object.keys(value).some(
        (k) => !["text", "language", "topic", "published_at"].includes(k),
      )
    )
      throw new Error(
        `Élément ${i + 1} : champ inconnu. Utilise text, language, topic, published_at.`,
      );
    if (Object.values(value).some((v) => typeof v !== "string"))
      throw new Error(`Élément ${i + 1} : les champs doivent être du texte.`);
  }
  return records as ImportRow[];
}
