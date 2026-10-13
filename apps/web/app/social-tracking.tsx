"use client";
import { useEffect, useState } from "react";
import { api, post } from "./api";
import { AutomaticTracking, AutomaticData } from "./automatic-tracking";

type Observation = {
  target_id: string;
  platform: string;
  source_url: string;
  state: string;
  title?: string;
  metrics: Record<string, number | null>;
  observed_at: string;
  provenance: string;
};
type Target = { id: string; url: string; platform: string; purpose: string };
type Status = AutomaticData & {
  targets: Target[];
  observations: Observation[];
  errors: { platform: string; message: string }[];
  youtube_configured: boolean;
  x_configured: boolean;
  can_configure: boolean;
  can_refresh: boolean;
  retention: string;
  unimplemented: string[];
};
export function SocialTracking() {
  const [data, setData] = useState<Status | null>(null),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [url, setUrl] = useState(""),
    [purpose, setPurpose] = useState(""),
    [accepted, setAccepted] = useState(false);
  async function load() {
    try {
      setData(await api<Status>("/tracking/status"));
    } catch (e) {
      setData(null);
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    void load();
    const timer = setInterval(() => void load(), 15000);
    return () => clearInterval(timer);
  }, []);
  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await action();
      await load();
    } catch (e) {
      setError((e as Error).message);
      await load();
    } finally {
      setBusy(false);
    }
  }
  const labels: Record<string, string> = {
    views: "Vues",
    impressions: "Impressions",
    likes: "J’aime",
    comments: "Commentaires",
    reposts: "Repartages",
    replies: "Réponses",
    quotes: "Citations",
  };
  return (
    <section
      className="panel pad live-connections"
      aria-label="Suivi des publications sociales"
    >
      <div className="live-heading">
        <div>
          <span className="eyebrow teal">
            API OFFICIELLES · MESURES OBSERVÉES
          </span>
          <h2>Suivi des publications sociales</h2>
          <p>
            Publications sélectionnées sur YouTube, X, Bluesky et Mastodon.
            Aucun score de viralité, audience estimée ou classement médical.
          </p>
        </div>
        <button
          className="btn primary"
          disabled={busy || !data?.can_refresh || !data.targets.length}
          onClick={() => void run(() => post("/tracking/refresh", {}))}
        >
          Interroger les API
        </button>
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {message && <p role="status">{message}</p>}
      {data?.errors.map((e) => (
        <p role="alert" key={e.platform}>
          {e.platform} : {e.message}
        </p>
      ))}
      {data && (
        <>
          {data.can_configure && (
            <AutomaticTracking data={data} busy={busy} run={run} />
          )}
          <p>
            YouTube :{" "}
            {data.youtube_configured
              ? "clé locale configurée · connexion à vérifier"
              : "déconnecté · clé API requise"}{" "}
            · X :{" "}
            {data.x_configured
              ? "jeton configuré · connexion à vérifier"
              : "déconnecté · accès API requis"}{" "}
            · Bluesky / Mastodon : API publiques · accès à vérifier lors de la
            collecte.
          </p>
          <p>
            Les vues ne sont pas des personnes uniques. Les likes et repartages
            ne prouvent ni l’adhésion ni la propagation d’une rumeur. La zone
            géographique et la couverture globale restent inconnues. Une mesure
            absente est affichée « inconnue ».
          </p>
          {data.can_configure && (
            <aside
              className="social-directions"
              aria-labelledby="social-directions-title"
            >
              <h3 id="social-directions-title">
                Suivre une publication précise (facultatif)
              </h3>
              <p>
                Pour commencer sans clé API, choisissez un post public Bluesky
                ou Mastodon. L’accès dépend des autorisations du service.
                YouTube et X nécessitent vos identifiants API configurés.
              </p>
              <ol>
                <li>
                  <strong>Copiez le lien du post.</strong> Ouvrez la publication
                  sur Bluesky ou Mastodon, puis utilisez « Partager » → « Copier
                  le lien », ou copiez son URL dans la barre d’adresse.
                  Choisissez une publication précise, pas un profil.
                </li>
                <li>
                  <strong>Collez ce lien</strong> dans le champ « URL de la
                  publication » ci-dessous.
                </li>
                <li>
                  <strong>Indiquez pourquoi vous la suivez</strong> dans « Objet
                  de la veille ». Exemple : « Suivre l’engagement sur cette
                  annonce publique concernant la vaccination. »
                </li>
                <li>
                  <strong>Lisez les conditions de la source</strong>, cochez la
                  case de confirmation, puis cliquez sur « Ajouter au suivi ».
                </li>
                <li>
                  <strong>Laissez la veille automatique activée.</strong> Les
                  mesures sont récupérées au prochain cycle, sans clic
                  supplémentaire. Pour une demande immédiate, cliquez sur «
                  Interroger les API ». Les compteurs reçus, leur date et le
                  lien original s’affichent dans la fiche de la publication
                  ci-dessous. Si l’accès est refusé, un message explique
                  l’échec.
                </li>
              </ol>
              <p>
                Ajouter un lien prépare le suivi. Le bouton « Interroger les API
                » récupère les mesures réelles.
              </p>
            </aside>
          )}
          {data.can_configure && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void run(async () => {
                  await post("/tracking/targets", {
                    url,
                    purpose,
                    terms_accepted: accepted,
                  });
                  setUrl("");
                  setPurpose("");
                  setAccepted(false);
                  setMessage(
                    "Publication ajoutée au suivi. La veille automatique récupérera ses mesures au prochain cycle. Vous pouvez aussi cliquer sur « Interroger les API » pour une demande manuelle.",
                  );
                });
              }}
            >
              <label>
                URL de la publication
                <input
                  required
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  maxLength={500}
                  placeholder="Collez ici le lien original du post ou de la vidéo"
                />
              </label>
              <label>
                Objet de la veille
                <input
                  required
                  value={purpose}
                  onChange={(e) => setPurpose(e.target.value)}
                  minLength={10}
                  maxLength={300}
                  placeholder="Ex. : Suivre l’engagement sur cette annonce publique concernant la vaccination."
                />
              </label>
              <label className="social-consent">
                <input
                  type="checkbox"
                  required
                  checked={accepted}
                  onChange={(e) => setAccepted(e.target.checked)}
                />{" "}
                J’ai examiné les conditions de la source et dispose d’un motif
                autorisé pour cette veille.
              </label>
              <div className="button-row">
                <button className="btn" disabled={busy}>
                  Ajouter au suivi
                </button>
                <a
                  href="https://developers.google.com/youtube/terms/developer-policies"
                  target="_blank"
                  rel="noreferrer"
                >
                  Conditions API YouTube
                </a>
                <a
                  href="https://bsky.social/about/support/tos"
                  target="_blank"
                  rel="noreferrer"
                >
                  Conditions Bluesky
                </a>
              </div>
            </form>
          )}
          {!data.targets.length && (
            <p>
              Aucune publication sélectionnée. Aucune donnée sociale n’a été
              inventée ou collectée.
            </p>
          )}
          {data.targets.map((target) => {
            const o = data.observations.find((x) => x.target_id === target.id);
            return (
              <article className="panel pad" key={target.id}>
                <div className="live-heading">
                  <div>
                    <strong>{o?.title || target.platform}</strong>
                    <p>{target.purpose}</p>
                    <a href={target.url} target="_blank" rel="noreferrer">
                      Publication originale
                    </a>
                  </div>
                  {data.can_configure && (
                    <button
                      className="btn"
                      disabled={busy}
                      onClick={() =>
                        void run(() =>
                          api("/tracking/targets/" + target.id, {
                            method: "DELETE",
                          }),
                        )
                      }
                    >
                      Retirer
                    </button>
                  )}
                </div>
                {!o ? (
                  <p>
                    Pas de mesure récente. Interrogez l’API pour obtenir un
                    résultat réel.
                  </p>
                ) : (
                  <>
                    <p>
                      {o.state === "observed"
                        ? "Observation réelle"
                        : "Publication indisponible ou non publique · aucune mesure"}{" "}
                      · {new Date(o.observed_at).toLocaleString()} ·{" "}
                      {o.provenance}
                    </p>
                    <div className="button-row">
                      {Object.entries(o.metrics).map(([key, value]) => (
                        <span className="pill" key={key}>
                          {labels[key] || key} :{" "}
                          {value === null ? "inconnue" : value.toLocaleString()}
                        </span>
                      ))}
                    </div>
                  </>
                )}
              </article>
            );
          })}
          <p>{data.retention}</p>
          <p>
            Autres plateformes à intégrer : {data.unimplemented.join(", ")}.
            Ajouter une clé seule ne suffit pas pour ces plateformes.
          </p>
          <p>
            Cette fonctionnalité utilise les API YouTube lorsque configurées.
            Consultez les{" "}
            <a
              href="https://www.youtube.com/t/terms"
              target="_blank"
              rel="noreferrer"
            >
              conditions YouTube
            </a>{" "}
            et la{" "}
            <a
              href="https://policies.google.com/privacy"
              target="_blank"
              rel="noreferrer"
            >
              politique de confidentialité Google
            </a>
            . Aucun compte social n’est connecté par OAuth; aucun message n’est
            publié. Les URL sélectionnées et leur objet sont conservés sur ce PC
            jusqu’au retrait. Les sauvegardes existantes doivent être traitées
            séparément en cas de suppression.
          </p>
        </>
      )}
    </section>
  );
}
