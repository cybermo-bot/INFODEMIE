"use client";
import { useState } from "react";
import { api, post } from "./api";
type Observation = {
  target_id: string;
  watch_id?: string;
  platform: string;
  source_url: string;
  title?: string;
  state: string;
  metrics: Record<string, number | null>;
  observed_at: string;
  query?: string;
};
type Watch = {
  id: string;
  platform: string;
  query: string;
  language: string;
  state: string;
  error?: string;
  next_poll_at?: string;
  last_attempt_at?: string;
  interval_minutes?: number;
};
export type AutomaticData = {
  automatic: {
    enabled: boolean;
    interval_minutes: number;
    state: string;
    last_attempt_at?: string;
    next_poll_at?: string;
    runner: { state: string; last_tick_at?: string };
  };
  watches: Watch[];
  discoveries: Observation[];
};
const date = (value?: string) =>
  value ? new Date(value).toLocaleString() : "En attente du premier cycle";
export function AutomaticTracking({
  data,
  busy,
  run,
}: {
  data: AutomaticData;
  busy: boolean;
  run: (action: () => Promise<unknown>) => Promise<void>;
}) {
  const [query, setQuery] = useState(""),
    [platform, setPlatform] = useState("bluesky"),
    [server, setServer] = useState("https://mastodon.social"),
    [language, setLanguage] = useState(""),
    [purpose, setPurpose] = useState(""),
    [accepted, setAccepted] = useState(false);
  return (
    <div className="social-directions" aria-label="Veille automatique">
      <div className="live-heading">
        <div>
          <h3>Veille automatique</h3>
          <p>
            <strong>{data.automatic.enabled ? "Activée" : "En pause"}</strong> ·
            Publications enregistrées : toutes les{" "}
            {data.automatic.interval_minutes} minutes · Recherche de nouvelles
            publications : toutes les heures (Mastodon : toutes les 2 heures),
            avec ralentissement en cas d’erreur ou de quota.
          </p>
        </div>
        <button
          className="btn"
          disabled={busy}
          onClick={() =>
            void run(() =>
              api("/tracking/automatic", {
                method: "PUT",
                body: JSON.stringify({
                  enabled: !data.automatic.enabled,
                  interval_minutes: data.automatic.interval_minutes,
                }),
              }),
            )
          }
        >
          {data.automatic.enabled ? "Mettre en pause" : "Activer la veille"}
        </button>
      </div>
      <p>
        Le moteur fonctionne sur ce PC même si vous fermez cet onglet. Gardez
        PNSI démarré et le PC éveillé et connecté. Moteur :{" "}
        {data.automatic.runner.state} · Dernier contrôle :{" "}
        {date(data.automatic.runner.last_tick_at)}.
      </p>
      <p>
        Configurez le sujet une seule fois. La plateforme cherche ensuite des
        publications correspondantes et récupère les mesures accessibles. RSS
        officiels : collecte toutes les 30 minutes. YouTube et X attendent vos
        clés et les droits API nécessaires; une recherche Bluesky peut être
        refusée par le service. Une correspondance par mots-clés n’est pas une
        rumeur confirmée.
      </p>
      {data.watches.map((w) => (
        <article className="panel pad" key={w.id}>
          <div className="live-heading">
            <div>
              <strong>
                {w.platform} · {w.state}
              </strong>
              <p>{w.query}</p>
              <p>
                Langue : {w.language || "toutes · selon les mots-clés"} ·
                Dernière tentative : {date(w.last_attempt_at)} · Prochaine
                recherche : {date(w.next_poll_at)}
              </p>
              {w.error && <p role="alert">{w.error}</p>}
            </div>
            <button
              className="btn"
              disabled={busy}
              onClick={() =>
                void run(() =>
                  api("/tracking/watches/" + w.id, { method: "DELETE" }),
                )
              }
            >
              Retirer cette recherche
            </button>
          </div>
        </article>
      ))}
      <details>
        <summary>Configurer une recherche par sujet (4 maximum)</summary>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void run(async () => {
              await post("/tracking/watches", {
                platform,
                query,
                language,
                purpose,
                terms_accepted: accepted,
                server,
              });
              setQuery("");
              setPurpose("");
              setAccepted(false);
            });
          }}
        >
          <label>
            1. Source
            <select
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
            >
              <option value="bluesky">Bluesky · accès public à vérifier</option>
              <option value="youtube">YouTube · clé requise</option>
              <option value="mastodon">Mastodon · hashtags publics</option>
              <option value="x">X · accès recherche et jeton requis</option>
            </select>
          </label>
          <label>
            2. Mots-clés à rechercher (Mastodon : hashtags séparés par des
            virgules)
            <input
              required
              minLength={2}
              maxLength={150}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ex. : vaccination, rougeole ou une affirmation précise"
            />
          </label>
          {platform === "mastodon" && (
            <label>
              Serveur Mastodon
              <input
                required
                type="url"
                value={server}
                onChange={(e) => setServer(e.target.value)}
                placeholder="https://mastodon.social"
              />
            </label>
          )}
          <label>
            3. Langue
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              <option value="">
                Toutes · utilisez aussi des mots-clés Derja/Arabizi
              </option>
              <option value="fr">Français</option>
              <option value="en">English</option>
              <option value="ar">العربية</option>
            </select>
          </label>
          <label>
            4. Objet de la veille
            <input
              required
              minLength={10}
              maxLength={300}
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              placeholder="Décrivez le sujet et la justification de cette veille"
            />
          </label>
          <label className="social-consent">
            <input
              type="checkbox"
              required
              checked={accepted}
              onChange={(e) => setAccepted(e.target.checked)}
            />{" "}
            J’ai examiné les conditions de cette source et dispose d’un motif
            autorisé pour la veille.
          </label>
          <button
            className="btn primary"
            disabled={busy || data.watches.length >= 4}
          >
            Enregistrer la recherche automatique
          </button>
        </form>
      </details>
      <h3>Publications découvertes automatiquement</h3>
      <p>
        Échantillon : au plus 10 résultats récents par recherche, période de 7
        jours, sans parcours exhaustif. Les résultats sont renouvelés au
        prochain cycle et expirent au plus tard 15 minutes après le cycle
        attendu (maximum 2 h 15). Un échec retire les anciennes mesures. La
        couverture géographique est inconnue. Aucun historique de propagation ni
        détection médicale automatique.
      </p>
      {!data.discoveries.length && (
        <p>
          Aucun résultat récent disponible. Consultez l’état de chaque recherche
          ci-dessus : attente de clés, accès refusé, premier cycle en attente ou
          absence de correspondance.
        </p>
      )}
      {data.discoveries.map((o) => (
        <article className="panel pad" key={(o.watch_id || "") + o.target_id}>
          <strong>
            {o.title || "Publication correspondante · " + o.platform}
          </strong>
          <p>
            {o.state === "observed"
              ? "Mesures reçues de l’API officielle"
              : "Publication indisponible"}{" "}
            · {date(o.observed_at)}
          </p>
          <a href={o.source_url} target="_blank" rel="noreferrer">
            Ouvrir la publication originale
          </a>
          <div className="button-row">
            {Object.entries(o.metrics).map(([key, value]) => (
              <span className="pill" key={key}>
                {key} : {value === null ? "inconnue" : value.toLocaleString()}
              </span>
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}
