"use client";
import {
  Activity,
  Database,
  Radio,
  RefreshCw,
  ExternalLink,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
type Publication = {
  id: string;
  title?: string;
  text: string;
  summary?: string;
  source_name: string;
  source_url?: string;
  published_at?: string;
  collected_at?: string;
  created_at: string;
  attribution?: string;
  license_url?: string;
  modifications?: string;
};
type Collection = {
  id: string;
  source_name?: string;
  created_at: string;
  state: string;
  count: number;
  fetched?: number;
  duplicates?: number;
};
export type LiveOverviewData = {
  total_collected: number;
  live_publications: number;
  connected_feeds: number;
  catalog_available: boolean;
  connections: {
    api: string;
    database: string;
    worker: string;
    checked_at: string;
    worker_last_seen?: string;
    last_collection_at?: string;
    queued: number;
    running: number;
    failed: number;
  };
  latest_publications: Publication[];
  recent_collections: Collection[];
};
export function LiveConnections({
  data,
  connect,
  refresh,
  busy,
  formatDate,
}: {
  data: LiveOverviewData;
  connect: () => void;
  refresh: () => void;
  busy: boolean;
  formatDate: (value?: string) => string;
}) {
  return (
    <section className="live-connections panel pad">
      <div className="live-heading">
        <div>
          <span className="eyebrow teal">DONNÉES VÉRIFIABLES</span>
          <h2>Veille connectée</h2>
          <p>
            Publications officielles collectées depuis les sources · aucune
            donnée de démonstration ajoutée.
          </p>
        </div>
        <div className="button-row">
          <button className="btn" onClick={refresh} disabled={busy}>
            <RefreshCw size={15} />
            Actualiser les résultats
          </button>
          {data.catalog_available && (
            <button className="btn primary" onClick={connect} disabled={busy}>
              <Radio size={15} />
              {data.connected_feeds
                ? "Synchroniser les flux ECDC"
                : "Raccorder les flux ECDC"}
            </button>
          )}
        </div>
      </div>
      <div className="connection-grid">
        {[
          {
            name: "API",
            icon: Activity,
            state: data.connections.api,
            detail: "Réponse authentifiée du serveur",
          },
          {
            name: "Base de données",
            icon: Database,
            state: data.connections.database,
            detail: `${data.total_collected} éléments enregistrés`,
          },
          {
            name: "Collecteur",
            icon: Radio,
            state: data.connections.worker,
            detail: data.connections.worker_last_seen
              ? `Dernier signal : ${formatDate(data.connections.worker_last_seen)}`
              : "Aucun signal reçu",
          },
        ].map((x) => (
          <div className="connection-card" key={x.name}>
            <x.icon size={18} />
            <div>
              <strong>{x.name}</strong>
              <small>{x.detail}</small>
            </div>
            <span
              className={
                x.state === "connected" ? "connection-ok" : "connection-warn"
              }
            >
              {x.state === "connected" ? (
                <CheckCircle2 size={15} />
              ) : (
                <AlertTriangle size={15} />
              )}{" "}
              {x.state === "connected" ? "Connectée" : "À vérifier"}
            </span>
          </div>
        ))}
      </div>
      <div className="live-counts">
        <span>
          <strong>{data.live_publications}</strong> publications réelles en base
        </span>
        <span>
          <strong>{data.connected_feeds}</strong> flux ayant répondu
        </span>
        <span>
          <strong>{data.connections.queued + data.connections.running}</strong>{" "}
          collectes en cours
        </span>
        <small>
          Dernière collecte : {formatDate(data.connections.last_collection_at)}{" "}
          · Contrôle API : {formatDate(data.connections.checked_at)}
        </small>
      </div>
      {!data.total_collected && (
        <p className="info-box">
          Raccorde les flux publics ECDC pour collecter des résultats réels, ou
          importe tes fichiers autorisés. Les indicateurs ne sont renseignés
          qu’après enregistrement effectif.
        </p>
      )}
      {data.connections.failed > 0 && (
        <p className="connection-warn">
          {data.connections.failed} opération(s) en échec dans le journal.
          Consulte Opérations pour connaître la cause.
        </p>
      )}
    </section>
  );
}
export function LivePublications({
  data,
  formatDate,
  showAll,
}: {
  data: LiveOverviewData;
  formatDate: (value?: string) => string;
  showAll: () => void;
}) {
  return (
    <section className="panel live-publications">
      <div className="panel-head">
        <div>
          <h2>Dernières publications dans la période</h2>
          <p>Dates de publication originales · liens vers l’éditeur</p>
        </div>
        <button className="text-btn" onClick={showAll}>
          Tout consulter <ArrowRight size={14} />
        </button>
      </div>
      {data.latest_publications.length ? (
        <div className="publication-list">
          {data.latest_publications.map((p) => (
            <article key={p.id} className="publication-row">
              <div className="publication-date">
                {formatDate(p.published_at)}
                <small>{p.source_name}</small>
              </div>
              <div>
                <h3 dir="auto">{p.title || p.text.split("\n")[0]}</h3>
                <p dir="auto">
                  {p.summary?.slice(0, 280) || p.text.slice(0, 280)}
                  {(p.summary?.length || p.text.length) > 280 ? "…" : ""}
                </p>
                <div className="publication-attribution">
                  <span>{p.attribution || p.source_name}</span>
                  {p.license_url && (
                    <a
                      href={p.license_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      CC BY 4.0
                    </a>
                  )}
                  <small>{p.modifications}</small>
                </div>
              </div>
              {p.source_url && (
                <a
                  className="btn publication-link"
                  href={p.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Source <ExternalLink size={14} />
                </a>
              )}
            </article>
          ))}
        </div>
      ) : (
        <div className="empty">
          <Radio />
          <p>Aucune publication dans cette période.</p>
          <small>
            Élargis la période ou lance une collecte. Aucun résultat n’est
            simulé.
          </small>
        </div>
      )}
      {data.recent_collections.length > 0 && (
        <div className="panel-foot">
          <details>
            <summary>Traçabilité des dernières collectes</summary>
            <ul>
              {data.recent_collections.map((r) => (
                <li key={r.id}>
                  {r.source_name || "Import"} · {formatDate(r.created_at)} ·{" "}
                  {r.fetched ?? r.count} reçus, {r.count} nouveaux,{" "}
                  {r.duplicates ?? 0} doublons
                </li>
              ))}
            </ul>
          </details>
        </div>
      )}
    </section>
  );
}
