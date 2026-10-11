// Requests outside a locale (rare: the proxy prefixes every path).
export default function NotFound() {
  return (
    <html lang="fr">
      <body>
        <p>Page introuvable.</p>
      </body>
    </html>
  );
}
