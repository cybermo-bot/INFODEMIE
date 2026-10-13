"use client";
import { useEffect, useState, useCallback, useRef, Fragment } from "react";
import {
  Activity,
  LayoutDashboard,
  MessagesSquare,
  Files,
  Library,
  ShieldCheck,
  PenLine,
  ClipboardCheck,
  Send,
  BarChart3,
  FileText,
  Radio,
  Settings2,
  BookOpen,
  LogOut,
  Search,
  Bell,
  ChevronDown,
  ChevronRight,
  ArrowUpRight,
  ArrowRight,
  Plus,
  Download,
  Filter,
  Calendar,
  Globe2,
  Check,
  CheckCircle2,
  AlertTriangle,
  Info,
  Clock,
  MoreHorizontal,
  Upload,
  Layers,
  Tag,
  FlaskConical,
  Workflow,
  History,
  X,
  Menu,
  RefreshCw,
  UserRound,
  ExternalLink,
  Lock,
  CheckCheck,
  Signal,
  Database,
  Compass,
  Command,
} from "lucide-react";
import { api, post, patch, review, Entity, PageResult } from "./api";
import { Locale, translator, statusLabels } from "./i18n";
import { LocalSetup, PasswordChange } from "./local-access";
import { parseImportFile } from "./import-file";
import { LiveConnections, LivePublications } from "./live-overview";
import { SocialTracking } from "./social-tracking";
type NavItem = {
  key: string;
  path: string;
  icon: any;
  group: number;
  kind?: string;
};
const nav: NavItem[] = [
  { key: "overview", path: "/overview", icon: LayoutDashboard, group: 0 },
  {
    key: "conversations",
    path: "/conversations",
    icon: MessagesSquare,
    group: 0,
    kind: "content",
  },
  { key: "claims", path: "/claims", icon: Files, group: 0, kind: "cases" },
  {
    key: "narratives",
    path: "/narratives",
    icon: Layers,
    group: 0,
    kind: "narratives",
  },
  { key: "alerts", path: "/alerts", icon: Bell, group: 0, kind: "alerts" },
  {
    key: "evidence",
    path: "/evidence/documents",
    icon: Library,
    group: 1,
    kind: "documents",
  },
  {
    key: "responses",
    path: "/responses",
    icon: PenLine,
    group: 1,
    kind: "responses",
  },
  {
    key: "approvals",
    path: "/approvals",
    icon: ClipboardCheck,
    group: 1,
    kind: "responses",
  },
  { key: "actions", path: "/actions", icon: Send, group: 1, kind: "actions" },
  {
    key: "impact",
    path: "/impact",
    icon: BarChart3,
    group: 1,
    kind: "follow-ups",
  },
  {
    key: "reports",
    path: "/reports",
    icon: FileText,
    group: 1,
    kind: "reports",
  },
  { key: "sources", path: "/sources", icon: Radio, group: 2, kind: "sources" },
  {
    key: "annotation",
    path: "/annotation",
    icon: Tag,
    group: 2,
    kind: "annotations",
  },
  {
    key: "evaluation",
    path: "/evaluation",
    icon: FlaskConical,
    group: 2,
    kind: "evaluations",
  },
  { key: "admin", path: "/admin", icon: Settings2, group: 2, kind: "users" },
  {
    key: "jobs",
    path: "/operations/jobs",
    icon: Workflow,
    group: 2,
    kind: "jobs",
  },
  { key: "audit", path: "/audit", icon: History, group: 2, kind: "audit" },
];
const roles = [
  "analyst",
  "scientific_reviewer",
  "communication_editor",
  "institutional_approver",
  "viewer",
  "administrator",
  "operator",
];
const topicOptions = [
  "Vaccination",
  "Prévention",
  "Médicaments",
  "Surveillance",
  "Accès aux soins",
  "Nutrition",
  "Environnement",
];
const verdicts = [
  "unassessed",
  "supported",
  "contradicted",
  "misleading",
  "insufficient_evidence",
  "conflicting_evidence",
  "not_factual",
];
type Field = {
  name: string;
  label: string;
  type?: string;
  options?: string[];
  required?: boolean;
  value?: any;
};
type Form = {
  title: string;
  description?: string;
  fields: Field[];
  submit: (v: any) => Promise<any>;
};

function Trend({
  data,
  large = false,
}: {
  data: { date: string; count: number }[];
  large?: boolean;
}) {
  const max = Math.max(...data.map((d) => d.count), 1);
  const points = data
    .map(
      (d, i) =>
        `${50 + (i * 600) / Math.max(data.length - 1, 1)},${165 - (d.count / max) * 125}`,
    )
    .join(" ");
  return (
    <div className={"trend " + (large ? "large" : "")}>
      <svg viewBox="0 0 690 205" role="img" aria-label="Collected items by day">
        <defs>
          <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#1d9a91" stopOpacity=".2" />
            <stop offset="100%" stopColor="#1d9a91" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0, 1, 2, 3].map((i) => (
          <g key={i}>
            <line
              x1="48"
              y1={40 + i * 42}
              x2="660"
              y2={40 + i * 42}
              stroke="#e8edf1"
              strokeDasharray="3 4"
            />
            <text x="20" y={44 + i * 42} fill="#87949f" fontSize="10">
              {Math.round(max * (1 - i / 3))}
            </text>
          </g>
        ))}
        {data.length > 0 && (
          <>
            <polygon
              points={"50,168 " + points + " 650,168"}
              fill="url(#area)"
            />
            <polyline
              points={points}
              fill="none"
              stroke="#118a81"
              strokeWidth="2.5"
              strokeLinejoin="round"
            />
            {data.map((d, i) => (
              <g key={d.date}>
                <circle
                  cx={50 + (i * 600) / Math.max(data.length - 1, 1)}
                  cy={165 - (d.count / max) * 125}
                  r="3"
                  fill="#fff"
                  stroke="#118a81"
                  strokeWidth="2"
                />
                <text
                  x={50 + (i * 600) / Math.max(data.length - 1, 1)}
                  y="193"
                  fill="#7e8996"
                  fontSize="10"
                  textAnchor="middle"
                >
                  {d.date.slice(5)}
                </text>
              </g>
            ))}
          </>
        )}
      </svg>
      <details>
        <summary>Data table / Tableau de données</summary>
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Items</th>
            </tr>
          </thead>
          <tbody>
            {data.map((d) => (
              <tr key={d.date}>
                <td>{d.date}</td>
                <td>{d.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}
export default function Workspace() {
  const [user, setUser] = useState<Entity | null>(null),
    [locale, setLocale] = useState<Locale>("fr"),
    [path, setPath] = useState("/overview"),
    [query, setQuery] = useState(""),
    [topic, setTopic] = useState(""),
    [language, setLanguage] = useState(""),
    [cursor, setCursor] = useState(0),
    [data, setData] = useState<PageResult>({
      items: [],
      total: 0,
      next_cursor: null,
    }),
    [overview, setOverview] = useState<any>(null),
    [busy, setBusy] = useState(true),
    [error, setError] = useState(""),
    [toast, setToast] = useState(""),
    [revision, setRevision] = useState(0),
    [form, setForm] = useState<Form | null>(null),
    [detail, setDetail] = useState<Entity | null>(null),
    [caseData, setCaseData] = useState<Record<string, Entity[]>>({}),
    [tab, setTab] = useState("summary"),
    [mobile, setMobile] = useState(false),
    [loginRole, setLoginRole] = useState("analyst"),
    [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [submitting, setSubmitting] = useState(false),
    [days, setDays] = useState(7);
  const t = translator(locale),
    rtl = locale === "ar" || locale === "derja";
  const [versions, setVersions] = useState<Record<string, Entity[]>>({});
  const quietReload = useRef(false);
  const [authConfig, setAuthConfig] = useState<{
    mode: string;
    configured: boolean;
  } | null>(null);
  const isLocal = authConfig?.mode === "local";
  const signedOut = () => {
    sessionStorage.removeItem("pnsi-token");
    setUser(null);
    setPassword("");
    setBusy(false);
  };
  async function showVersions(kind: string, r: Entity) {
    try {
      const result = await api<{ items: Entity[] }>(
        "/versions/" + kind + "/" + r.id,
      );
      setVersions((x) => ({ ...x, [r.id]: result.items }));
    } catch (e) {
      setError(message(e));
    }
  }
  const current =
    nav.find((n) => n.path === path) ||
    (path.startsWith("/cases/")
      ? nav.find((n) => n.key === "claims")
      : nav.find((n) => path.startsWith(n.path) && n.key !== "overview"));
  const caseId = path.startsWith("/cases/") ? path.split("/")[2] : null;
  const responseId = path.startsWith("/responses/") ? path.split("/")[2] : null;
  const allowed = (...r: string[]) => !!user && r.includes(user.role);
  const message = (e: any) => (e instanceof Error ? e.message : String(e));
  const refresh = () => setRevision((x) => x + 1);
  const label = (s: string) =>
    statusLabels[locale === "derja" ? "ar" : locale]?.[s] ||
    statusLabels.en[s] ||
    statusLabels.fr[s] ||
    s?.replaceAll("_", " ");
  const date = (d?: string) =>
    d
      ? new Intl.DateTimeFormat(
          locale === "ar" || locale === "derja"
            ? "ar-TN"
            : locale === "en"
              ? "en-GB"
              : "fr-TN",
          {
            dateStyle: "medium",
            timeStyle: "short",
            timeZone: user?.timezone || "Africa/Tunis",
          },
        ).format(new Date(d))
      : "—";
  const go = (url: string) => {
    history.pushState({}, "", url);
    setPath(url.split("?")[0]);
    setQuery("");
    setTopic("");
    setLanguage("");
    setCursor(0);
    setError("");
    setDetail(null);
    setTab("summary");
    setMobile(false);
  };
  useEffect(() => {
    const parse = () => {
      setPath(location.pathname === "/" ? "/overview" : location.pathname);
      const p = new URLSearchParams(location.search);
      setQuery(p.get("q") || "");
      setTopic(p.get("topic") || "");
      setLanguage(p.get("language") || "");
    };
    parse();
    api<{ mode: string; configured: boolean }>("/auth/config")
      .then(setAuthConfig)
      .catch((e) => setError(message(e)));
    const lc = localStorage.getItem("pnsi-locale") as Locale;
    if (lc) setLocale(lc);
    const expire = () => {
      setUser(null);
      sessionStorage.removeItem("pnsi-token");
      setBusy(false);
    };
    window.addEventListener("popstate", parse);
    window.addEventListener("pnsi-session-expired", expire);
    if (sessionStorage.getItem("pnsi-token"))
      api<Entity>("/me")
        .then(setUser)
        .catch(() => {})
        .finally(() => setBusy(false));
    else setBusy(false);
    return () => {
      window.removeEventListener("popstate", parse);
      window.removeEventListener("pnsi-session-expired", expire);
    };
  }, []);
  useEffect(() => {
    document.documentElement.dir = rtl ? "rtl" : "ltr";
    document.documentElement.lang = locale.startsWith("derja")
      ? "ar-TN"
      : locale;
    localStorage.setItem("pnsi-locale", locale);
  }, [locale, rtl]);
  useEffect(() => {
    if (!user || user.must_change_password) return;
    const timer = setTimeout(() => {
      const params = new URLSearchParams();
      if (query) params.set("q", query);
      if (topic) params.set("topic", topic);
      if (language) params.set("language", language);
      history.replaceState(
        {},
        "",
        path + (params.size ? "?" + params.toString() : ""),
      );
    }, 300);
    return () => clearTimeout(timer);
  }, [path, query, topic, language, user]);
  useEffect(() => {
    if (!user || user.must_change_password) return;
    let active = true;
    if (!quietReload.current) setBusy(true);
    quietReload.current = false;
    setError("");
    const params = new URLSearchParams({
      q: query,
      topic,
      language,
      cursor: String(cursor),
      days: String(days),
    });
    const load = async () => {
      try {
        if (path === "/overview") {
          const d = await api("/overview?" + params);
          if (active) setOverview(d);
        } else if (caseId) {
          const c = await api<Entity>("/cases/" + caseId);
          const kinds = [
            "content",
            "claims",
            "assessments",
            "responses",
            "actions",
            "follow-ups",
            "documents",
          ];
          const results = await Promise.all(
            kinds.map((k) =>
              api<PageResult>(
                "/" + k + "?case_id=" + (k === "documents" ? "" : caseId),
              ),
            ),
          );
          const timeline = await api<{ items: Entity[] }>(
            "/cases/" + caseId + "/timeline",
          );
          if (active) {
            setDetail(c);
            setCaseData(
              Object.fromEntries([
                ...kinds.map((k, i) => [k, results[i].items]),
                ["timeline", timeline.items],
              ]),
            );
          }
        } else if (responseId) {
          const d = await api<Entity>("/responses/" + responseId);
          if (active) setDetail(d);
        } else if (path === "/imports") {
          const d = await api<PageResult>("/sources");
          if (active) setData(d);
        } else if (path === "/profile" || path === "/help") {
        } else {
          let kind = current?.kind || "documents";
          if (path === "/evidence/sources") kind = "evidence-sources";
          if (path === "/evidence/reviews") kind = "documents";
          const d = await api<PageResult>("/" + kind + "?" + params);
          if (active)
            setData(
              path === "/approvals"
                ? {
                    ...d,
                    items: d.items.filter(
                      (x) => !["approved", "draft"].includes(x.state),
                    ),
                  }
                : d,
            );
        }
      } catch (e) {
        if (active) {
          setError(message(e));
          if (path === "/overview")
            setOverview((previous: any) =>
              previous?.connections
                ? {
                    ...previous,
                    connections: {
                      ...previous.connections,
                      api: "unavailable",
                      database: "unknown",
                      worker: "unknown",
                    },
                  }
                : previous,
            );
        }
      } finally {
        if (active) setBusy(false);
      }
    };
    const timer = setTimeout(load, query ? 250 : 0);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [
    user,
    path,
    query,
    topic,
    language,
    cursor,
    revision,
    caseId,
    responseId,
    days,
  ]);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 5000);
    return () => clearTimeout(timer);
  }, [toast]);
  useEffect(() => {
    if (!user || user.must_change_password || !isLocal || path !== "/overview")
      return;
    const timer = setInterval(() => {
      quietReload.current = true;
      refresh();
    }, 15000);
    return () => clearInterval(timer);
  }, [user?.id, user?.must_change_password, isLocal, path]);
  async function act(fn: () => Promise<any>, success = "Enregistré / Saved") {
    setSubmitting(true);
    try {
      await fn();
      refresh();
      setToast(success);
    } catch (e) {
      setError(message(e));
    } finally {
      setSubmitting(false);
    }
  }
  async function signIn(demo = false) {
    setSubmitting(true);
    setError("");
    try {
      const d = await post("/auth/login", {
        email: demo ? loginRole + "@demo-onmne.local" : email,
        password: demo ? "Pnsi-Demo-2026!" : password,
      });
      sessionStorage.setItem("pnsi-token", d.token);
      setUser(d.user);
      go(d.user.must_change_password ? "/profile" : "/overview");
    } catch (e) {
      setError(message(e));
    } finally {
      setSubmitting(false);
    }
  }
  function ask(
    title: string,
    submit: (v: any) => Promise<any>,
    fields: Field[],
    description?: string,
  ) {
    setForm({ title, submit, fields, description });
  }
  function rationale(
    title: string,
    item: Entity,
    path: string,
    decision: string,
  ) {
    ask(
      title,
      (v) => review(path, item, decision, v.rationale),
      [
        {
          name: "rationale",
          label: "Justification / Rationale",
          type: "textarea",
          required: true,
        },
      ],
      "La décision sera enregistrée avec votre rôle et la version exacte. / Decision is audited with your role and exact version.",
    );
  }
  function Badge({ state }: { state: string }) {
    return (
      <span className={"badge " + state}>
        <span className="dot" />
        {label(state)}
      </span>
    );
  }
  function Empty() {
    return (
      <div className="empty">
        <Database size={30} />
        <h3>{t("empty")}</h3>
        <p>{t("emptyNote")}</p>
      </div>
    );
  }
  function caseRows(items: Entity[], compact = false) {
    return (
      <div className="table-wrap">
        <table className={compact ? "compact" : ""}>
          <thead>
            <tr>
              <th>Dossier / Case</th>
              <th>{t("evidenceStatus")}</th>
              <th>{t("priority")}</th>
              {!compact && <th>{t("owner")}</th>}
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((c) => (
              <tr key={c.id}>
                <td>
                  <button
                    className="row-link"
                    onClick={() => go("/cases/" + c.id)}
                  >
                    <span className="case-code">
                      <bdi>{c.code}</bdi> · {c.topic}
                    </span>
                    <strong dir="auto">{c.title}</strong>
                  </button>
                </td>
                <td>
                  <Badge state={c.evidence_status} />
                </td>
                <td>
                  <span
                    className={
                      "priority " +
                      (c.priority >= 70
                        ? "high"
                        : c.priority >= 40
                          ? "medium"
                          : "low")
                    }
                  >
                    <Signal size={13} />
                    {c.priority}
                    <small>/100</small>
                  </span>
                  <small className="muted">
                    {c.completeness}% completeness
                  </small>
                </td>
                {!compact && (
                  <td>
                    <span className="owner">
                      <span className="avatar small">
                        {c.owner?.[0] || "?"}
                      </span>
                      {c.owner || "—"}
                    </span>
                  </td>
                )}
                <td>
                  <button
                    className="icon-btn"
                    aria-label={t("open") + " " + c.code}
                    onClick={() => go("/cases/" + c.id)}
                  >
                    <ArrowUpRight size={17} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  function newCase() {
    ask(
      t("new"),
      (v) => post("/cases", { data: { ...v, priority: Number(v.priority) } }),
      [
        {
          name: "title",
          label: "Allégation neutre / Neutral claim",
          type: "textarea",
          required: true,
        },
        { name: "topic", label: t("topic"), options: topicOptions },
        {
          name: "language",
          label: t("language"),
          options: [
            "fr",
            "en",
            "ar",
            "derja",
            "derja-latin",
            "mixed",
            "unknown",
          ],
        },
        {
          name: "priority",
          label: "Priorité manuelle (0–100)",
          type: "number",
          value: 0,
        },
      ],
      "Ce dossier démarre sans verdict. / This case starts unassessed.",
    );
  }
  function newReport() {
    ask(
      t("export"),
      (v) => post("/reports", { data: v }),
      [
        { name: "title", label: "Titre / Title", required: true },
        {
          name: "type",
          label: "Périodicité",
          options: ["daily", "weekly", "monthly"],
        },
      ],
      "Snapshot figé des 7 derniers jours. Validation institutionnelle requise avant export.",
    );
  }
  function newSource(evidence = false) {
    ask(
      evidence ? "Proposer une source de preuves" : "Configurer une source RSS",
      (v) => post(evidence ? "/evidence-sources" : "/sources", { data: v }),
      [
        { name: "name", label: "Nom / Name", required: true },
        {
          name: evidence ? "organization" : "url",
          label: evidence ? "Organisation" : "Exact HTTPS feed URL",
          required: true,
        },
        {
          name: "permission",
          label: "Référence de permission / Permission basis",
          type: "textarea",
          required: true,
        },
        {
          name: evidence ? "scope" : "owner",
          label: evidence
            ? "Périmètre d’autorité / Authority scope"
            : t("owner"),
          required: true,
        },
      ],
      "Cette source reste en attente jusqu’à sa revue. Aucun accès n’est présumé.",
    );
  }
  function newDocument() {
    api<PageResult>("/evidence-sources")
      .then((d) =>
        ask(
          "Ajouter un document de preuve",
          (v) => {
            const source = d.items.find((x) => x.name === v.source);
            if (!source) throw new Error("Select an approved source");
            return post("/documents", {
              data: {
                title: v.title,
                source_id: source.id,
                effective_date: v.effective_date,
                language: v.language,
                permission: v.permission,
                edition: v.edition,
                passages: [{ text: v.text, page: Number(v.page) }],
              },
            });
          },
          [
            { name: "title", label: "Titre / Title", required: true },
            {
              name: "source",
              label: "Source approuvée",
              options: d.items
                .filter((x) => x.state === "approved")
                .map((x) => x.name),
            },
            {
              name: "language",
              label: t("language"),
              options: ["fr", "en", "ar", "derja"],
            },
            { name: "edition", label: "Version / Edition", required: true },
            {
              name: "effective_date",
              label: "Date d’effet / Effective date",
              type: "date",
              required: true,
            },
            {
              name: "permission",
              label: "Droit de stockage / Storage permission",
              required: true,
            },
            { name: "page", label: "Page", type: "number", value: 1 },
            {
              name: "text",
              label: "Passage exact / Exact passage",
              type: "textarea",
              required: true,
            },
          ],
          "Saisie manuelle autorisée. Le document reste en attente de revue scientifique.",
        ),
      )
      .catch((e) => setError(message(e)));
  }
  function draft(c: Entity, a: Entity) {
    ask(
      "Créer une variante de réponse",
      (v) =>
        post("/responses", {
          data: {
            ...v,
            case_id: c.id,
            assessment_id: a.id,
            script: ["ar", "derja"].includes(v.locale) ? "arabic" : "latin",
          },
        }),
      [
        {
          name: "locale",
          label: t("language"),
          options: ["fr", "en", "ar", "derja", "derja-latin"],
        },
        {
          name: "channel",
          label: "Canal / Channel",
          options: ["FAQ", "Post", "Press statement", "Spokesperson Q&A"],
        },
      ],
      "Un modèle déterministe propose un brouillon à partir de l’évaluation revue. Aucun modèle IA n’est configuré.",
    );
  }
  function responseControls(r: Entity) {
    return (
      <div className="button-row">
        {allowed("communication_editor") &&
          ["draft", "changes_requested"].includes(r.state) && (
            <button
              className="btn primary"
              onClick={() =>
                rationale(
                  "Demander la revue scientifique",
                  r,
                  "/responses/" + r.id + "/approve",
                  "request_review",
                )
              }
            >
              Demander la revue <ArrowRight size={14} />
            </button>
          )}
        {allowed("scientific_reviewer") && r.state === "scientific_review" && (
          <button
            className="btn primary"
            onClick={() =>
              rationale(
                "Valider la revue scientifique",
                r,
                "/responses/" + r.id + "/approve",
                "scientific",
              )
            }
          >
            Valider scientifiquement
          </button>
        )}
        {allowed("communication_editor") && r.state === "language_review" && (
          <button
            className="btn primary"
            onClick={() =>
              rationale(
                "Valider la langue et l’équivalence",
                r,
                "/responses/" + r.id + "/approve",
                "language",
              )
            }
          >
            Valider la langue
          </button>
        )}
        {allowed("institutional_approver") &&
          r.state === "institutional_review" && (
            <button
              className="btn primary"
              onClick={() =>
                rationale(
                  "Approuver cette version exacte",
                  r,
                  "/responses/" + r.id + "/approve",
                  "institutional",
                )
              }
            >
              Approuver la version {r.version}
            </button>
          )}
        {allowed("communication_editor") && (
          <button
            className="btn"
            onClick={() =>
              ask(
                "Modifier · approbations invalidées",
                (v) =>
                  api("/responses/" + r.id, {
                    method: "PUT",
                    body: JSON.stringify({ expected_version: r.version, ...v }),
                  }),
                [
                  {
                    name: "body",
                    label: "Texte exact / Exact body",
                    type: "textarea",
                    value: r.body,
                    required: true,
                  },
                  {
                    name: "locale",
                    label: t("language"),
                    options: ["fr", "en", "ar", "derja", "derja-latin"],
                    value: r.locale,
                  },
                  {
                    name: "channel",
                    label: "Channel",
                    value: r.channel,
                    required: true,
                  },
                ],
                "Toute modification crée une nouvelle version et reprend les revues.",
              )
            }
          >
            Modifier
          </button>
        )}
        {[
          "scientific_review",
          "language_review",
          "institutional_review",
        ].includes(r.state) &&
          allowed(
            "scientific_reviewer",
            "communication_editor",
            "institutional_approver",
          ) && (
            <button
              className="btn danger"
              onClick={() =>
                rationale(
                  "Demander des modifications",
                  r,
                  "/responses/" + r.id + "/approve",
                  "reject",
                )
              }
            >
              Demander des modifications
            </button>
          )}
        {r.state === "approved" &&
          allowed("communication_editor", "institutional_approver") && (
            <button
              className="btn primary"
              onClick={() =>
                ask(
                  "Enregistrer une publication effectuée",
                  (v) =>
                    post(
                      "/actions/record",
                      {
                        response_id: r.id,
                        expected_version: r.version,
                        channel: v.channel,
                        performed_at: new Date(v.performed_at).toISOString(),
                        reference: v.reference || null,
                      },
                      { "Idempotency-Key": crypto.randomUUID() },
                    ),
                  [
                    {
                      name: "channel",
                      label: "Canal réel / Actual channel",
                      value: r.channel,
                      required: true,
                    },
                    {
                      name: "performed_at",
                      label: "Date réelle (heure locale de votre navigateur)",
                      type: "datetime-local",
                      required: true,
                    },
                    {
                      name: "reference",
                      label: "Référence autorisée (facultative)",
                    },
                  ],
                  "Cette action n’envoie rien. Elle enregistre votre publication manuelle et planifie 48h / 7j / 30j.",
                )
              }
            >
              Enregistrer l’action <Send size={14} />
            </button>
          )}
      </div>
    );
  }
  async function downloadReport(r: Entity, format: string) {
    try {
      const resp = await fetch(
        "/api/v1/reports/" + r.id + "/export?format=" + format,
        {
          headers: {
            Authorization: "Bearer " + sessionStorage.getItem("pnsi-token"),
          },
        },
      );
      if (!resp.ok) throw new Error((await resp.json()).message);
      const url = URL.createObjectURL(await resp.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = "pnsi-report-" + r.id.slice(0, 8) + "." + format;
      a.click();
      URL.revokeObjectURL(url);
      setToast("Export créé / Export created");
    } catch (e) {
      setError(message(e));
    }
  }

  if (user?.must_change_password)
    return (
      <div className="login local-login">
        <div className="login-form">
          <PasswordChange required onComplete={signedOut} />
          <button
            className="btn"
            onClick={() =>
              act(async () => {
                await post("/auth/logout", {});
                signedOut();
              })
            }
          >
            Se déconnecter
          </button>
        </div>
      </div>
    );
  if (isLocal && !authConfig?.configured)
    return (
      <LocalSetup
        onComplete={() => {
          setAuthConfig({ mode: "local", configured: true });
          setToast("Espace créé. Connecte-toi avec ton compte.");
        }}
      />
    );
  if (!user && !authConfig && error)
    return (
      <div className="loading">
        <p role="alert">{error}</p>
        <button className="btn" onClick={() => location.reload()}>
          Réessayer la connexion au serveur
        </button>
      </div>
    );
  if (!user && (busy || !authConfig))
    return (
      <div className="loading">
        <RefreshCw className="spin" />
        <p>{t("loading")}</p>
      </div>
    );
  if (!user)
    return (
      <div className="login">
        <div className="login-story">
          <div className="brand">
            <span className="brand-icon">
              <Activity />
            </span>
            <span>
              PNSI<small>HEALTH INTELLIGENCE</small>
            </span>
          </div>
          <div>
            <span className="eyebrow">TUNISIE · VEILLE SANITAIRE</span>
            <h1>
              De la conversation
              <br />à une action
              <br />
              <em>éclairée.</em>
            </h1>
            <p>
              Une plateforme pour écouter les préoccupations, examiner les
              preuves et préparer des réponses revues par des humains.
            </p>
            <div className="login-steps">
              <span>
                <Compass />
                Observer
              </span>
              <span>
                <ShieldCheck />
                Vérifier
              </span>
              <span>
                <Send />
                Agir
              </span>
            </div>
          </div>
          <small>Proposition PNSI · Version de développement · 2026</small>
        </div>
        <div className="login-form">
          <div className="login-card">
            <span className="eyebrow teal">ESPACE INSTITUTIONNEL</span>
            <h2>Bienvenue dans PNSI</h2>
            <p className="muted">Connectez-vous à votre espace de travail.</p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                signIn();
              }}
            >
              <label>
                Adresse professionnelle
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="nom@institution.tn"
                />
              </label>
              <label>
                Mot de passe
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </label>
              <button className="btn primary full" disabled={submitting}>
                Se connecter <ArrowRight size={16} />
              </button>
            </form>
            {!isLocal && (
              <>
                <div className="or">EXPLORER LA DÉMONSTRATION</div>
                <label>
                  Rôle dans l’atelier
                  <select
                    value={loginRole}
                    onChange={(e) => setLoginRole(e.target.value)}
                  >
                    {roles.map((r) => (
                      <option key={r}>{r}</option>
                    ))}
                  </select>
                </label>
                <button
                  className="btn full"
                  disabled={submitting}
                  onClick={() => signIn(true)}
                >
                  Ouvrir l’atelier synthétique <ArrowUpRight size={16} />
                </button>
                <p className="login-note">
                  <Lock size={13} />
                  Comptes de démonstration isolés. Aucun accès institutionnel
                  réel, aucune conclusion médicale.
                </p>
              </>
            )}
            {error && (
              <div role="alert" className="error">
                {error}
              </div>
            )}
          </div>
        </div>
      </div>
    );

  async function reviewAssessment(a: Entity) {
    try {
      const documents = await api<PageResult>("/documents?limit=100");
      const choices = documents.items
        .filter((d) => d.state === "approved")
        .flatMap((d) =>
          d.passages.map((p: any) => ({
            key: d.title + " · p." + p.page + " · " + p.id,
            link: {
              document_id: d.id,
              document_version: d.version,
              passage_id: p.id,
              relation: "context",
              relevance_reason: "Reviewed for this claim",
            },
          })),
        );
      ask(
        "Revue scientifique de l’évaluation",
        (v) => {
          const selected = choices.find((c: any) => c.key === v.passage);
          const links = [...(a.evidence_links || [])];
          if (selected) {
            const link = {
              ...selected.link,
              relation: v.relation,
              relevance_reason: v.rationale,
            };
            const index = links.findIndex(
              (x) => x.passage_id === link.passage_id,
            );
            if (index >= 0) links[index] = link;
            else links.push(link);
          }
          return post("/assessments/" + a.id + "/review", {
            expected_version: a.version,
            decision: v.decision,
            rationale: v.rationale,
            evidence_links: links,
          });
        },
        [
          {
            name: "decision",
            label: "Conclusion",
            options: verdicts.filter((x) => x !== "unassessed"),
            value: a.proposed_status,
          },
          {
            name: "passage",
            label: "Ajouter / réviser un passage approuvé",
            options: [
              "Conserver les liens actuels",
              ...choices.map((x: any) => x.key),
            ],
          },
          {
            name: "relation",
            label: "Relation du passage",
            options: ["context", "supports", "contradicts"],
          },
          {
            name: "rationale",
            label: "Justification, population et limites",
            type: "textarea",
            value: a.rationale,
            required: true,
          },
        ],
        "Les verdicts factuels nécessitent des preuves approuvées. Vérifiez la pertinence, les dates et les contradictions.",
      );
    } catch (e) {
      setError(message(e));
    }
  }
  function dashboard() {
    return (
      <>
        <div className="page-intro">
          <div>
            <div className="eyebrow">PNSI / INTELLIGENCE SANITAIRE</div>
            <h1>{t("title")}</h1>
            <p>{t("subtitle")}</p>
          </div>
          <button
            className="btn"
            disabled={!allowed("analyst", "institutional_approver")}
            onClick={newReport}
          >
            <Download size={15} />
            {t("export")}
          </button>
        </div>
        <div className="filter-bar">
          <span className="filter-title">
            <Filter size={14} />{" "}
            {locale === "en" ? "Workspace filters" : "Filtres de veille"}
          </span>
          <select
            aria-label={t("topic")}
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
          >
            <option value="">{t("topic")} : tous</option>
            {topicOptions.map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
          <select
            aria-label={t("language")}
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            <option value="">{t("language")} : toutes</option>
            {["fr", "en", "ar", "derja", "derja-latin", "unknown"].map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
          <span className="filter-spacer" />
          <Calendar size={14} />
          <select
            aria-label="Period"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          >
            <option value={7}>{t("period")}</option>
            <option value={30}>30 days / jours</option>
            <option value={90}>90 days / jours</option>
          </select>
        </div>
        {overview && (
          <>
            {isLocal && overview.connections && (
              <LiveConnections
                data={overview}
                connect={() =>
                  act(
                    () =>
                      post("/connectors/public", {
                        keys: ["ecdc-news", "ecdc-updates", "ecdc-threats"],
                      }),
                    "Flux raccordés. Collectes en cours; les résultats se mettent à jour automatiquement.",
                  )
                }
                refresh={() => {
                  quietReload.current = true;
                  refresh();
                }}
                busy={submitting}
                formatDate={date}
              />
            )}
            {isLocal && <SocialTracking />}
            <div className="kpi-grid">
              {[
                {
                  k: "items",
                  icon: MessagesSquare,
                  value: overview.items,
                  note: isLocal
                    ? "Dans la période sélectionnée"
                    : "Imports synthétiques",
                  url: "/conversations",
                },
                {
                  k: "review",
                  icon: ShieldCheck,
                  value: overview.needs_review,
                  note: "Revue scientifique requise",
                  url: "/claims",
                },
                {
                  k: "approved",
                  icon: CheckCheck,
                  value: overview.approved_responses,
                  note: "Versions signées uniquement",
                  url: "/responses",
                },
                {
                  k: "priority",
                  icon: Signal,
                  value: overview.high_priority,
                  note: "Seuil pilote ≥ 70",
                  url: "/alerts",
                },
              ].map((x, i) => (
                <button
                  className={"kpi kpi-" + i}
                  key={x.k}
                  onClick={() => go(x.url)}
                >
                  <div className="kpi-top">
                    <span>{t(x.k)}</span>
                    <x.icon size={18} />
                  </div>
                  <strong>{x.value.toString().padStart(2, "0")}</strong>
                  <div className="kpi-bottom">
                    <span className="tiny-dot" />
                    {x.note}
                    <ArrowUpRight size={14} />
                  </div>
                </button>
              ))}
            </div>
            <div className="dashboard-main">
              <section className="panel">
                <div className="panel-head">
                  <div>
                    <h2>{isLocal ? "Publications observées" : t("volume")}</h2>
                    <p>Éléments dédupliqués · sources sélectionnées</p>
                  </div>
                  <span className="legend">
                    <span />
                    {isLocal
                      ? "Publications & imports"
                      : "Imports synthétiques"}
                  </span>
                </div>
                <Trend data={overview.trend} />
                <div className="panel-foot">
                  <Info size={13} />
                  {t("sourceNote")}
                </div>
              </section>
              <section className="panel source-health">
                <div className="panel-head">
                  <div>
                    <h2>{t("coverage")}</h2>
                    <p>Disponibilité réelle des connecteurs</p>
                  </div>
                  <Radio size={18} />
                </div>
                <div className="coverage-summary">
                  <strong>
                    {String(
                      overview.sources.filter(
                        (s: Entity) => s.state === "ready",
                      ).length,
                    ).padStart(2, "0")}
                    <span>
                      /{String(overview.sources.length).padStart(2, "0")}
                    </span>
                  </strong>
                  <div>
                    routes disponibles
                    <small>
                      {isLocal
                        ? "Flux RSS & imports autorisés"
                        : "Import manuel uniquement"}
                    </small>
                  </div>
                </div>
                {overview.sources
                  .slice()
                  .sort(
                    (a: Entity, b: Entity) =>
                      [
                        "manual",
                        "rss",
                        "youtube",
                        "bluesky",
                        "meta",
                        "x",
                      ].indexOf(a.platform) -
                      [
                        "manual",
                        "rss",
                        "youtube",
                        "bluesky",
                        "meta",
                        "x",
                      ].indexOf(b.platform),
                  )
                  .slice(0, 4)
                  .map((s: Entity) => (
                    <div className="source-mini" key={s.id}>
                      <span className="source-icon">
                        {s.platform === "manual" ? (
                          <Upload size={15} />
                        ) : s.platform === "rss" ? (
                          <Radio size={15} />
                        ) : (
                          <Globe2 size={15} />
                        )}
                      </span>
                      <div>
                        <strong>{s.name}</strong>
                        <small>
                          {s.last_success
                            ? date(s.last_success)
                            : "Aucune collecte réussie"}
                        </small>
                      </div>
                      <span
                        className={
                          "health-dot " + (s.state === "ready" ? "good" : "")
                        }
                      />
                    </div>
                  ))}
                <button className="text-btn" onClick={() => go("/sources")}>
                  Examiner les sources <ArrowRight size={14} />
                </button>
              </section>
            </div>
            {isLocal && overview.connections && (
              <LivePublications
                data={overview}
                formatDate={date}
                showAll={() => go("/conversations")}
              />
            )}
            <div className="dashboard-bottom">
              <section className="panel queue">
                <div className="panel-head">
                  <div>
                    <h2>
                      {t("queue")}{" "}
                      <span className="count">{overview.queue.length}</span>
                    </h2>
                    <p>
                      Priorité d’action et état des preuves restent distincts
                    </p>
                  </div>
                  <button className="text-btn" onClick={() => go("/claims")}>
                    {t("all")}
                    <ArrowRight size={14} />
                  </button>
                </div>
                {caseRows(overview.queue, true)}
              </section>
              <section className="panel topics">
                <div className="panel-head">
                  <div>
                    <h2>Thèmes observés</h2>
                    <p>
                      {isLocal
                        ? "Répartition des éléments collectés"
                        : "Répartition du corpus synthétique"}
                    </p>
                  </div>
                  <Layers size={18} />
                </div>
                {Object.entries(overview.topics).map(([k, v], i) => (
                  <button
                    className="topic-row"
                    key={k}
                    onClick={() => {
                      go("/conversations");
                      setTopic(k);
                    }}
                  >
                    <div>
                      <span className={"topic-color color-" + i} />
                      {k}
                      <strong>{Number(v)}</strong>
                    </div>
                    <div className="topic-track">
                      <span
                        style={{
                          width:
                            (Number(v) / Math.max(overview.items, 1)) * 100 +
                            "%",
                          background: [
                            "#188a82",
                            "#6486ad",
                            "#9aabc0",
                            "#d6a051",
                            "#8d9bc3",
                            "#b3bac3",
                          ][i % 6],
                        }}
                      />
                    </div>
                  </button>
                ))}
                <div className="quiet-note">
                  Géographie : inconnue
                  <br />
                  Aucune inférence de résidence.
                </div>
              </section>
            </div>
            <div className="workflow-strip">
              <ShieldCheck size={21} />
              <div>
                <strong>{t("workflow")}</strong>
                <span>
                  Import → preuves → revue scientifique → langue → validation →
                  action manuelle
                </span>
              </div>
              <button className="text-btn" onClick={() => go("/help")}>
                Consulter le guide <ArrowUpRight size={14} />
              </button>
            </div>
          </>
        )}
      </>
    );
  }

  function assessmentCard(a: Entity) {
    return (
      <article className="card" key={a.id}>
        <div className="card-top">
          <Badge state={a.proposed_status} />
          <Badge state={a.review_status} />
          <span className="muted">v{a.version}</span>
        </div>
        <p dir="auto">{a.rationale}</p>
        <ul className="muted">
          {a.limitations?.map((x: string) => (
            <li key={x}>{x}</li>
          ))}
        </ul>
        <div className="evidence-links">
          {a.evidence_links?.map((l: any) => (
            <div key={l.passage_id}>
              <BookOpen size={14} />
              <bdi>{l.passage_id}</bdi>
              <span>{l.relation}</span>
              <small>
                Document v{l.document_version} · {l.relevance_reason}
              </small>
            </div>
          ))}
        </div>
        {allowed("scientific_reviewer") && (
          <button className="btn primary" onClick={() => reviewAssessment(a)}>
            Réviser / confirmer
          </button>
        )}
        {a.review_status === "confirmed" &&
          allowed("communication_editor") &&
          detail && (
            <button className="btn" onClick={() => draft(detail, a)}>
              Créer un brouillon <PenLine size={14} />
            </button>
          )}
      </article>
    );
  }
  function responseCard(r: Entity) {
    return (
      <article className="card" key={r.id}>
        <div className="card-top">
          <Badge state={r.state} />
          <span className="pill">
            {r.locale} · {r.channel}
          </span>
          <bdi className="muted">v{r.version}</bdi>
          <button className="text-btn" onClick={() => go("/responses/" + r.id)}>
            Ouvrir <ArrowUpRight size={14} />
          </button>
        </div>
        <p className="response-body" dir="auto">
          {r.body}
        </p>
        <p className="muted">
          Assessment v{r.assessment_version} · {r.citation_ids?.length || 0}{" "}
          passage(s) · {r.generated_by}
        </p>
        {r.approval && (
          <div className="approved-stamp">
            <CheckCircle2 size={15} />
            Version {r.approval.exact_version} · {date(r.approval.at)} ·{" "}
            {r.approval.role}
          </div>
        )}
        {responseControls(r)}
        <button
          className="text-btn"
          onClick={() => showVersions("responses", r)}
        >
          Comparer les versions <History size={14} />
        </button>
        {versions[r.id] && (
          <details open>
            <summary>Versions immuables / Immutable versions</summary>
            {versions[r.id].map((v) => (
              <blockquote key={v.version}>
                <small>
                  v{v.version} · {v.state} · {date(v.updated_at)}
                </small>
                <p dir="auto">{v.body}</p>
              </blockquote>
            ))}
          </details>
        )}
      </article>
    );
  }
  function casePage() {
    if (!detail) return null;
    const c = detail;
    const tabs = [
      "summary",
      "conversation",
      "spread",
      "evidenceTab",
      "assessment",
      "responses",
      "actions",
      "followup",
      "timeline",
    ];
    return (
      <>
        <button className="text-btn back" onClick={() => go("/claims")}>
          ← {t("back")}
        </button>
        <div className="case-header">
          <div className="eyebrow">
            <bdi>{c.code}</bdi> / {c.topic} /{" "}
            {c.synthetic ? t("synthetic") : "Dossier réel"}
          </div>
          <h1 dir="auto">{c.title}</h1>
          <div className="case-meta">
            <Badge state={c.evidence_status} />
            <Badge state={c.status} />
            <span className="priority high">
              <Signal size={14} />
              {c.priority}/100
            </span>
            <span className="muted">
              {c.completeness}% completeness · {c.owner}
            </span>
          </div>
        </div>
        <div className="tabs" role="tablist">
          {tabs.map((k) => (
            <button
              role="tab"
              aria-selected={tab === k}
              key={k}
              onClick={() => setTab(k)}
              className={tab === k ? "active" : ""}
            >
              {t(k)}
            </button>
          ))}
        </div>
        {tab === "summary" && (
          <div className="case-columns">
            <section className="panel pad">
              <span className="eyebrow teal">
                SYNTHETIC CASE / HUMAN REVIEW
              </span>
              <h2>Pourquoi ce dossier mérite une revue</h2>
              <p>{c.priority_rationale}</p>
              <div className="info-box">
                <Info size={18} />
                <div>
                  Les preuves et la priorité sont indépendantes. Un risque
                  potentiel élevé ne constitue pas un verdict de fausseté.
                </div>
              </div>
              <h3>Texte original</h3>
              <blockquote dir="auto">{c.original_text}</blockquote>
              <dl>
                <dt>{t("language")}</dt>
                <dd>{c.language}</dd>
                <dt>{t("owner")}</dt>
                <dd>{c.owner}</dd>
                <dt>Reviewer</dt>
                <dd>{c.reviewer || "Non assigné"}</dd>
                <dt>Échéance</dt>
                <dd>{date(c.due_at)} Africa/Tunis</dd>
              </dl>
              {allowed("analyst") && (
                <button
                  className="btn"
                  onClick={() =>
                    ask(
                      "Triage et attribution",
                      (v) =>
                        patch("cases", c, {
                          ...v,
                          priority: Number(v.priority),
                        }),
                      [
                        {
                          name: "owner",
                          label: t("owner"),
                          value: c.owner,
                          required: true,
                        },
                        {
                          name: "reviewer",
                          label: "Reviewer",
                          value: c.reviewer,
                        },
                        {
                          name: "priority",
                          label: "Priorité manuelle 0–100",
                          type: "number",
                          value: c.priority,
                        },
                        {
                          name: "priority_rationale",
                          label: "Justification",
                          type: "textarea",
                          value: c.priority_rationale,
                          required: true,
                        },
                      ],
                    )
                  }
                >
                  Modifier l’attribution
                </button>
              )}
            </section>
            <section className="panel pad">
              <h2>Prochaine étape</h2>
              <p>
                Rechercher des preuves, puis confier l’évaluation à un reviewer
                scientifique.
              </p>
              {(caseData.claims || []).map((claim) => (
                <div className="card" key={claim.id}>
                  <strong dir="auto">{claim.neutral_text}</strong>
                  <p className="muted">
                    {claim.claim_type} · {claim.language}
                  </p>
                  <button
                    className="btn primary"
                    disabled={!allowed("analyst", "scientific_reviewer")}
                    onClick={() =>
                      act(
                        () => post("/claims/" + claim.id + "/verify", {}),
                        "Recherche placée dans la file / Retrieval queued",
                      )
                    }
                  >
                    Rechercher les preuves <Search size={14} />
                  </button>
                </div>
              ))}
              <div className="quiet-note">
                Le moteur local est une base lexicale. Il s’abstient de rendre
                un verdict automatique. Le traitement est asynchrone.
              </div>
            </section>
          </div>
        )}
        {tab === "conversation" &&
          renderCards("content", caseData.content || [])}
        {tab === "spread" && (
          <section className="panel pad">
            <h2>Volume observé · mentions collectées</h2>
            <Trend
              data={Object.entries(
                (caseData.content || []).reduce((a: any, x) => {
                  const k = (
                    x.published_at ||
                    x.collected_at ||
                    x.created_at
                  ).slice(0, 10);
                  a[k] = (a[k] || 0) + 1;
                  return a;
                }, {}),
              )
                .sort()
                .map(([date, count]) => ({ date, count: Number(count) }))}
            />
            <div className="info-box">
              <Info />
              Géographie inconnue · sources sélectionnées · aucune mesure de
              portée nationale.
            </div>
          </section>
        )}
        {tab === "evidenceTab" &&
          renderCards("documents", caseData.documents || [])}
        {tab === "assessment" &&
          ((caseData.assessments || []).length ? (
            (caseData.assessments || []).map(assessmentCard)
          ) : (
            <Empty />
          ))}
        {tab === "responses" && (
          <>
            {allowed("communication_editor") &&
              (caseData.assessments || []).some(
                (a) => a.review_status === "confirmed",
              ) && (
                <button
                  className="btn primary section-action"
                  onClick={() =>
                    draft(
                      c,
                      (caseData.assessments || []).find(
                        (a) => a.review_status === "confirmed",
                      )!,
                    )
                  }
                >
                  Nouvelle variante <Plus size={14} />
                </button>
              )}
            {(caseData.responses || []).length ? (
              (caseData.responses || []).map(responseCard)
            ) : (
              <Empty />
            )}
          </>
        )}
        {tab === "actions" && renderCards("actions", caseData.actions || [])}
        {tab === "followup" &&
          renderCards("follow-ups", caseData["follow-ups"] || [])}
        {tab === "timeline" && renderCards("audit", caseData.timeline || [])}
      </>
    );
  }

  function renderCards(kind: string, items: Entity[]) {
    if (!items.length) return <Empty />;
    return (
      <div
        className={
          ["sources", "evidence-sources", "documents", "narratives"].includes(
            kind,
          )
            ? "cards-grid"
            : "cards-list"
        }
      >
        {items.map((r) => {
          if (kind === "responses") return responseCard(r);
          if (kind === "assessments") return assessmentCard(r);
          return (
            <article className="card" key={r.id}>
              <div className="card-top">
                <span className="record-icon">
                  {kind === "content" ? (
                    <MessagesSquare size={17} />
                  ) : kind === "documents" ? (
                    <FileText size={17} />
                  ) : kind === "sources" ? (
                    <Radio size={17} />
                  ) : kind === "audit" ? (
                    <History size={17} />
                  ) : (
                    <Layers size={17} />
                  )}
                </span>
                <div>
                  <small className="muted">
                    {r.source_name ||
                      r.organization ||
                      r.platform ||
                      r.actor ||
                      r.language ||
                      kind}
                  </small>
                  <h3 dir="auto">
                    {r.title ||
                      r.name ||
                      r.action ||
                      r.text ||
                      r.channel ||
                      r.label ||
                      "Record " + r.id.slice(0, 8)}
                  </h3>
                </div>
                {r.state && <Badge state={r.state} />}
              </div>
              {kind === "content" && (
                <>
                  <p dir="auto">{r.original_text}</p>
                  {r.translation && (
                    <div className="translation">
                      <Globe2 size={14} />
                      {r.translation}
                    </div>
                  )}
                  <div className="card-meta">
                    {date(r.published_at)} · {r.language} ·{" "}
                    {r.stance || "Review required"} · {r.geography}
                  </div>
                  {r.source_url && (
                    <div className="button-row">
                      <a
                        className="btn"
                        href={r.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Publication originale <ExternalLink size={14} />
                      </a>
                      {r.license_url && (
                        <a
                          className="text-btn"
                          href={r.license_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {r.attribution} · CC BY 4.0
                        </a>
                      )}
                    </div>
                  )}
                  {r.modifications && (
                    <p className="muted">{r.modifications}</p>
                  )}
                  {r.case_id ? (
                    <button
                      className="text-btn"
                      onClick={() => go("/cases/" + r.case_id)}
                    >
                      Ouvrir le dossier <ArrowUpRight size={14} />
                    </button>
                  ) : (
                    allowed("analyst") && (
                      <button
                        className="btn"
                        onClick={() =>
                          ask(
                            "Créer un dossier depuis cet élément",
                            (v) => post("/content/" + r.id + "/case", v),
                            [
                              {
                                name: "title",
                                label: "Allégation neutre",
                                type: "textarea",
                                value: r.text,
                                required: true,
                              },
                            ],
                          )
                        }
                      >
                        Créer un dossier
                      </button>
                    )
                  )}
                </>
              )}
              {["sources", "evidence-sources"].includes(kind) && (
                <>
                  <dl>
                    <dt>Permission</dt>
                    <dd>{r.permission || "Non fournie"}</dd>
                    <dt>
                      {kind === "sources" ? "Dernier succès" : "Périmètre"}
                    </dt>
                    <dd>
                      {kind === "sources" ? date(r.last_success) : r.scope}
                    </dd>
                    <dt>Owner / reviewer</dt>
                    <dd>{r.owner || r.reviewer || "À désigner"}</dd>
                  </dl>
                  {r.error && <p className="warning-text">{r.error}</p>}
                  <div className="button-row">
                    {kind === "evidence-sources" &&
                      allowed("scientific_reviewer") && (
                        <>
                          <button
                            className="btn"
                            onClick={() =>
                              rationale(
                                "Approuver le périmètre",
                                r,
                                "/evidence-sources/" + r.id + "/review",
                                "approved",
                              )
                            }
                          >
                            Approuver
                          </button>
                          <button
                            className="btn danger"
                            onClick={() =>
                              rationale(
                                "Suspendre cette source",
                                r,
                                "/evidence-sources/" + r.id + "/review",
                                "suspended",
                              )
                            }
                          >
                            Suspendre
                          </button>
                        </>
                      )}
                    {kind === "sources" &&
                      allowed("administrator") &&
                      r.platform === "rss" && (
                        <>
                          <button
                            className="btn"
                            onClick={() =>
                              rationale(
                                r.enabled
                                  ? "Désactiver"
                                  : "Activer après revue de permission",
                                r,
                                "/sources/" + r.id + "/enable",
                                r.enabled ? "disable" : "enable",
                              )
                            }
                          >
                            {r.enabled ? "Désactiver" : "Activer"}
                          </button>
                          <button
                            className="btn"
                            onClick={() =>
                              ask(
                                "Modifier la configuration RSS",
                                (v) => patch("sources", r, v),
                                [
                                  {
                                    name: "name",
                                    label: "Name",
                                    value: r.name,
                                    required: true,
                                  },
                                  {
                                    name: "url",
                                    label: "Exact HTTPS URL",
                                    value: r.url,
                                    required: true,
                                  },
                                  {
                                    name: "permission",
                                    label: "Permission basis",
                                    value: r.permission,
                                    type: "textarea",
                                    required: true,
                                  },
                                  {
                                    name: "owner",
                                    label: "Owner",
                                    value: r.owner,
                                  },
                                ],
                              )
                            }
                          >
                            Configurer
                          </button>
                        </>
                      )}
                    {kind === "sources" &&
                      allowed("operator", "administrator") &&
                      r.platform === "rss" &&
                      r.enabled && (
                        <button
                          className="btn primary"
                          onClick={() =>
                            act(
                              () => post("/sources/" + r.id + "/collect", {}),
                              "Collecte en file / Collection queued",
                            )
                          }
                        >
                          Collecter
                        </button>
                      )}
                  </div>
                </>
              )}
              {kind === "documents" && (
                <>
                  <p className="muted">
                    {r.edition} · {r.language} · Effective {r.effective_date} ·
                    Review {r.review_date || "À fixer"}
                  </p>
                  {r.passages?.map((p: any) => (
                    <blockquote key={p.id}>
                      <span className="passage-id">
                        p. {p.page} · <bdi>{p.id}</bdi>
                      </span>
                      <span dir="auto">{p.text}</span>
                    </blockquote>
                  ))}
                  <small className="muted">{r.permission}</small>
                  {allowed("scientific_reviewer") && (
                    <div className="button-row">
                      <button
                        className="btn"
                        onClick={() =>
                          rationale(
                            "Approuver ce document",
                            r,
                            "/documents/" + r.id + "/review",
                            "approved",
                          )
                        }
                      >
                        Approuver
                      </button>
                      <button
                        className="btn danger"
                        onClick={() =>
                          rationale(
                            "Retirer et rouvrir les évaluations",
                            r,
                            "/documents/" + r.id + "/review",
                            "withdrawn",
                          )
                        }
                      >
                        Retirer
                      </button>
                    </div>
                  )}
                </>
              )}
              {kind === "narratives" && (
                <>
                  <p>{r.rationale}</p>
                  {allowed("analyst") && (
                    <button
                      className="btn"
                      onClick={() =>
                        ask(
                          "Revoir le narratif",
                          (v) => patch("narratives", r, v),
                          [
                            {
                              name: "title",
                              label: "Libellé",
                              value: r.title,
                              required: true,
                            },
                            {
                              name: "rationale",
                              label: "Justification",
                              type: "textarea",
                              value: r.rationale,
                              required: true,
                            },
                            {
                              name: "state",
                              label: "State",
                              options: ["proposed", "confirmed"],
                              value: r.state,
                            },
                          ],
                        )
                      }
                    >
                      Revoir le regroupement
                    </button>
                  )}
                </>
              )}
              {kind === "alerts" && (
                <>
                  <p>{r.rationale}</p>
                  <p className="muted">
                    {r.owner} · Due {date(r.due_at)} · Selected source coverage
                  </p>
                  <div className="button-row">
                    {r.case_id && (
                      <button
                        className="btn"
                        onClick={() => go("/cases/" + r.case_id)}
                      >
                        Dossier <ArrowUpRight size={14} />
                      </button>
                    )}
                    {allowed("analyst") && (
                      <>
                        <button
                          className="btn primary"
                          onClick={() =>
                            act(() =>
                              patch("alerts", r, { state: "acknowledged" }),
                            )
                          }
                        >
                          Prendre en charge
                        </button>
                        <button
                          className="btn"
                          onClick={() =>
                            ask(
                              "Escalader avec justification",
                              (v) =>
                                patch("alerts", r, {
                                  state: "escalated",
                                  rationale: v.rationale,
                                }),
                              [
                                {
                                  name: "rationale",
                                  label: "Justification",
                                  type: "textarea",
                                  required: true,
                                },
                              ],
                              "Cette action enregistre une escalade interne; aucun destinataire externe n’est configuré.",
                            )
                          }
                        >
                          Escalader
                        </button>
                      </>
                    )}
                  </div>
                </>
              )}
              {kind === "actions" && (
                <>
                  <p className="response-body" dir="auto">
                    {r.body}
                  </p>
                  <p className="muted">
                    {r.actor} · {date(r.performed_at)} · Approved v
                    {r.approved_variant_version} · {r.locale}
                  </p>
                  <div className="approved-stamp">
                    <CheckCircle2 size={15} />
                    Publication enregistrée manuellement · 48h / 7j / 30j
                  </div>
                  {r.case_id && (
                    <button
                      className="text-btn"
                      onClick={() => go("/cases/" + r.case_id)}
                    >
                      Ouvrir le suivi <ArrowUpRight size={14} />
                    </button>
                  )}
                </>
              )}
              {kind === "follow-ups" && (
                <>
                  <h3>
                    {r.window_hours === 48
                      ? "48 h"
                      : r.window_hours === 168
                        ? "7 jours"
                        : "30 jours"}{" "}
                    · {date(r.due_at)}
                  </h3>
                  <p>{r.limitations}</p>
                  <dl>
                    <dt>Baseline</dt>
                    <dd>{r.baseline_count ?? "Unknown"}</dd>
                    <dt>Observed</dt>
                    <dd>{r.observed_count ?? "Unknown"}</dd>
                    <dt>Coverage comparable</dt>
                    <dd>
                      {r.coverage_comparable === null
                        ? "To review"
                        : String(r.coverage_comparable)}
                    </dd>
                  </dl>
                  {r.interpretation && <p>{r.interpretation}</p>}
                  {allowed("analyst") && (
                    <button
                      className="btn"
                      onClick={() =>
                        ask(
                          "Enregistrer une observation",
                          (v) =>
                            patch("follow-ups", r, {
                              ...v,
                              baseline_count:
                                v.baseline_count === ""
                                  ? null
                                  : Number(v.baseline_count),
                              observed_count:
                                v.observed_count === ""
                                  ? null
                                  : Number(v.observed_count),
                              coverage_comparable:
                                v.coverage_comparable === "true",
                              state: "completed",
                            }),
                          [
                            {
                              name: "baseline_count",
                              label: "Éléments avant action",
                              type: "number",
                              value: r.baseline_count ?? "",
                            },
                            {
                              name: "observed_count",
                              label: "Éléments dans la fenêtre",
                              type: "number",
                              value: r.observed_count ?? "",
                            },
                            {
                              name: "coverage_comparable",
                              label: "Couverture comparable ?",
                              options: ["false", "true"],
                            },
                            {
                              name: "limitations",
                              label: "Limites / changements de couverture",
                              type: "textarea",
                              value: r.limitations,
                              required: true,
                            },
                            {
                              name: "interpretation",
                              label: "Interprétation sans attribution causale",
                              type: "textarea",
                              value: r.interpretation,
                              required: true,
                            },
                          ],
                        )
                      }
                    >
                      Documenter l’observation
                    </button>
                  )}
                </>
              )}
              {kind === "reports" && (
                <>
                  <p className="muted">
                    {r.type} · Snapshot {date(r.cutoff)} · v{r.version}
                  </p>
                  <div className="report-stats">
                    <span>
                      <strong>{r.snapshot?.items}</strong>items
                    </span>
                    <span>
                      <strong>{r.snapshot?.cases}</strong>cases
                    </span>
                    <span>
                      <strong>{r.snapshot?.needs_review}</strong>pending review
                    </span>
                  </div>
                  <p>{r.coverage}</p>
                  <div className="button-row">
                    {allowed("institutional_approver") &&
                      r.state !== "approved" && (
                        <button
                          className="btn primary"
                          onClick={() =>
                            rationale(
                              "Approuver le rapport figé",
                              r,
                              "/reports/" + r.id + "/review",
                              "approved",
                            )
                          }
                        >
                          Approuver
                        </button>
                      )}
                    {r.state === "approved" && (
                      <>
                        <button
                          className="btn"
                          onClick={() => downloadReport(r, "json")}
                        >
                          <Download size={14} />
                          JSON
                        </button>
                        <button
                          className="btn"
                          onClick={() => downloadReport(r, "csv")}
                        >
                          <Download size={14} />
                          CSV
                        </button>
                        <button
                          className="btn"
                          onClick={() => downloadReport(r, "pdf")}
                        >
                          <Download size={14} />
                          PDF
                        </button>
                        <button
                          className="btn"
                          onClick={() => downloadReport(r, "pdf")}
                        >
                          <Download size={14} />
                          PDF
                        </button>
                      </>
                    )}
                  </div>
                  <details>
                    <summary>Snapshot preview</summary>
                    <pre>{JSON.stringify(r.snapshot, null, 2)}</pre>
                  </details>
                </>
              )}
              {kind === "jobs" && (
                <>
                  <progress max="100" value={r.progress || 0} />
                  <p className="muted">
                    Attempts {r.attempts} · {date(r.created_at)}
                  </p>
                  {r.error && <p className="warning-text">{r.error}</p>}
                  {r.result && <pre>{JSON.stringify(r.result, null, 2)}</pre>}
                  {r.state === "failed" && allowed("operator") && (
                    <button
                      className="btn"
                      onClick={() =>
                        act(() => post("/jobs/" + r.id + "/retry", {}))
                      }
                    >
                      Réessayer
                    </button>
                  )}
                </>
              )}
              {kind === "audit" && (
                <>
                  <p className="muted">
                    {r.actor} · {date(r.created_at)} ·{" "}
                    <bdi>{r.entity_id || r.id}</bdi>
                  </p>
                  <details>
                    <summary>Before / after version details</summary>
                    <pre>{JSON.stringify(r.details, null, 2)}</pre>
                  </details>
                </>
              )}
              {kind === "users" && (
                <>
                  <p>{r.email}</p>
                  <div className="card-meta">
                    {r.role} · {r.active ? "Active" : "Inactive"} · {r.locale}
                  </div>
                  {r.id !== user?.id && (
                    <>
                      <button
                        className="btn"
                        onClick={() =>
                          act(() => patch("users", r, { active: !r.active }))
                        }
                      >
                        {r.active ? "Deactivate" : "Activate"}
                      </button>
                      {isLocal && (
                        <button
                          className="btn"
                          onClick={() =>
                            ask(
                              "Réinitialiser le mot de passe",
                              (v) =>
                                post("/accounts/" + r.id + "/reset-password", {
                                  expected_version: r.version,
                                  temporary_password: v.temporary_password,
                                }),
                              [
                                {
                                  name: "temporary_password",
                                  label: "Nouveau mot de passe temporaire",
                                  type: "password",
                                  required: true,
                                },
                              ],
                              "Toutes les sessions de ce compte seront fermées. Le nouveau mot de passe devra être remplacé à la connexion.",
                            )
                          }
                        >
                          Réinitialiser le mot de passe
                        </button>
                      )}
                    </>
                  )}
                </>
              )}
              {["annotations", "evaluations"].includes(kind) && (
                <>
                  <p>{r.rationale}</p>
                  <pre>
                    {JSON.stringify(
                      {
                        label: r.label,
                        uncertainty: r.uncertainty,
                        dataset_version: r.dataset_version,
                        metrics: r.metrics,
                      },
                      null,
                      2,
                    )}
                  </pre>
                </>
              )}
            </article>
          );
        })}
      </div>
    );
  }

  function importsPage() {
    return (
      <ImportPanel
        sources={data.items.filter((x) => x.platform === "manual")}
        onComplete={() => {
          refresh();
          setToast("Import persisted / Import enregistré");
        }}
      />
    );
  }
  function ImportPanel({
    sources,
    onComplete,
  }: {
    sources: Entity[];
    onComplete: () => void;
  }) {
    const [text, setText] = useState(
        isLocal
          ? "[]"
          : '[\n  {"text": "Question synthétique sur le service T", "language": "fr", "topic": "Accès aux soins"}\n]',
      ),
      [permission, setPermission] = useState(""),
      [source, setSource] = useState(sources[0]?.id || ""),
      [preview, setPreview] = useState<any>(null),
      [err, setErr] = useState(""),
      [loading, setLoading] = useState(false);
    async function run(commit = false) {
      setLoading(true);
      setErr("");
      try {
        const d = await post(
          "/imports",
          {
            source_id: source,
            permission,
            items: JSON.parse(text),
            preview: !commit,
          },
          { "Idempotency-Key": crypto.randomUUID() },
        );
        if (commit) {
          setPreview(null);
          onComplete();
          setErr(
            "Import completed · " +
              d.count +
              " items, " +
              d.duplicates +
              " duplicates",
          );
        } else setPreview(d);
      } catch (e) {
        setErr(message(e));
      } finally {
        setLoading(false);
      }
    }
    return (
      <div className="case-columns">
        <section className="panel pad">
          <h2>Import autorisé · CSV / JSON</h2>
          <p>
            500 lignes maximum. Texte original, langue et date UTC; pas
            d’identifiants personnels.
          </p>
          <label>
            Source
            <select
              value={source}
              onChange={(e) => {
                setSource(e.target.value);
                setPreview(null);
              }}
            >
              {sources.map((s) => (
                <option value={s.id} key={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Déclaration de droits
            <input
              value={permission}
              onChange={(e) => {
                setPermission(e.target.value);
                setPreview(null);
              }}
              placeholder="Référence et périmètre de l’autorisation"
            />
          </label>
          <label>
            Données
            <textarea
              className="code-input"
              rows={12}
              value={text}
              onChange={(e) => {
                setText(e.target.value);
                setPreview(null);
              }}
            />
          </label>
          <label>
            Charger un fichier CSV ou JSON
            <input
              type="file"
              accept=".csv,.json"
              disabled={loading || !allowed("analyst")}
              onChange={async (e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                setPreview(null);
                setErr("");
                try {
                  if (file.size > 2_000_000)
                    throw new Error("Fichier limité à 2 Mo.");
                  setText(
                    JSON.stringify(
                      parseImportFile(await file.text(), file.name),
                      null,
                      2,
                    ),
                  );
                } catch (err) {
                  setErr(message(err));
                }
                e.target.value = "";
              }}
            />
          </label>
          <p className="muted">
            CSV UTF-8 : text, language, topic, published_at. Le fichier est lu
            sur ce PC. Seuls les éléments prévisualisés puis confirmés sont
            enregistrés.
          </p>
          <button
            className="btn primary"
            disabled={loading || !allowed("analyst")}
            onClick={() => run()}
          >
            Valider et prévisualiser <ArrowRight size={14} />
          </button>
          {err && (
            <div className="info-box" role="status">
              {err}
            </div>
          )}
        </section>
        <section className="panel pad">
          <h2>Prévisualisation de redaction</h2>
          {preview ? (
            <>
              <p>{preview.redaction_note}</p>
              {preview.errors?.map((e: any) => (
                <div className="error" key={e.row}>
                  Row {e.row}: {e.message}
                </div>
              ))}
              {preview.preview?.map((p: any, i: number) => (
                <blockquote dir="auto" key={i}>
                  {p.text}
                </blockquote>
              ))}
              <button
                className="btn primary"
                disabled={loading || !!preview.errors?.length}
                onClick={() => run(true)}
              >
                Confirmer les données relues <Check size={14} />
              </button>
            </>
          ) : (
            <div className="empty">
              <Upload />
              <p>
                La prévisualisation sera affichée ici. Vérifiez les noms et le
                contexte permettant une identification.
              </p>
            </div>
          )}
        </section>
      </div>
    );
  }
  function listPage() {
    const key = current?.key || "evidence";
    let kind = current?.kind || "documents";
    if (path === "/evidence/sources") kind = "evidence-sources";
    if (path === "/evidence/reviews") kind = "documents";
    return (
      <>
        <div className="page-intro">
          <div>
            <div className="eyebrow">PNSI / {key.toUpperCase()}</div>
            <h1>{t(key)}</h1>
            <p>
              Sources sélectionnées · décisions versionnées ·{" "}
              {isLocal ? "Espace local" : t("synthetic")}
            </p>
          </div>
          <div className="button-row">
            {key === "claims" && allowed("analyst") && (
              <button className="btn primary" onClick={newCase}>
                <Plus size={15} />
                {t("new")}
              </button>
            )}
            {key === "conversations" && allowed("analyst") && (
              <button className="btn primary" onClick={() => go("/imports")}>
                <Upload size={15} />
                {t("imports")}
              </button>
            )}
            {key === "sources" && allowed("administrator") && (
              <button className="btn primary" onClick={() => newSource()}>
                <Plus size={15} />
                Source RSS
              </button>
            )}
            {key === "admin" && isLocal && allowed("administrator") && (
              <button
                className="btn primary"
                onClick={() =>
                  ask(
                    "Créer un compte",
                    (v) => post("/accounts", v),
                    [
                      { name: "name", label: "Nom", required: true },
                      {
                        name: "email",
                        label: "Adresse e-mail",
                        type: "email",
                        required: true,
                      },
                      { name: "role", label: "Rôle", options: roles },
                      {
                        name: "password",
                        label:
                          "Mot de passe temporaire (12 caractères minimum)",
                        type: "password",
                        required: true,
                      },
                    ],
                    "Donne le mot de passe temporaire à cette personne par un canal privé. Elle devra le remplacer à sa première connexion.",
                  )
                }
              >
                <Plus size={15} />
                Créer un compte
              </button>
            )}
            {key === "evidence" && allowed("scientific_reviewer") && (
              <button
                className="btn primary"
                onClick={() =>
                  kind === "evidence-sources" ? newSource(true) : newDocument()
                }
              >
                <Plus size={15} />
                {kind === "evidence-sources" ? "Source" : "Document"}
              </button>
            )}
            {key === "reports" &&
              allowed("analyst", "institutional_approver") && (
                <button className="btn primary" onClick={newReport}>
                  <Plus size={15} />
                  {t("export")}
                </button>
              )}
            {key === "annotation" &&
              allowed("analyst", "scientific_reviewer") && (
                <button
                  className="btn primary"
                  onClick={() =>
                    ask(
                      "Nouvelle annotation",
                      (v) =>
                        post("/annotations", {
                          data: { ...v, annotator_id: user?.id },
                        }),
                      [
                        {
                          name: "title",
                          label: "Référence / Original context",
                          type: "textarea",
                          required: true,
                        },
                        {
                          name: "label",
                          label: "Task label",
                          options: verdicts,
                        },
                        {
                          name: "uncertainty",
                          label: "Uncertainty",
                          options: ["high", "medium", "low"],
                        },
                        {
                          name: "rationale",
                          label: "Rationale",
                          type: "textarea",
                          required: true,
                        },
                        {
                          name: "dataset_version",
                          label: "Dataset version",
                          required: true,
                        },
                      ],
                    )
                  }
                >
                  <Plus size={15} />
                  Annotation
                </button>
              )}
          </div>
        </div>
        {key === "evidence" && (
          <div className="tabs">
            {[
              ["/evidence/documents", "Documents"],
              ["/evidence/sources", "Registre des sources"],
              ["/evidence/reviews", "Revue des documents"],
            ].map(([p, k]) => (
              <button
                key={p}
                onClick={() => go(p)}
                className={p === path ? "active" : ""}
              >
                {k}
              </button>
            ))}
          </div>
        )}
        {key === "evaluation" && allowed("scientific_reviewer") && (
          <button
            className="btn primary"
            onClick={() =>
              ask(
                "Geler un benchmark revu",
                (v) => post("/evaluation/freeze", { data: v }),
                [
                  {
                    name: "title",
                    label: "Titre du benchmark",
                    required: true,
                  },
                  {
                    name: "dataset_version",
                    label: "Version des annotations résolues",
                    required: true,
                  },
                ],
                "Toutes les annotations de cette version doivent avoir été résolues indépendamment. Aucun score n’est inventé.",
              )
            }
          >
            <FlaskConical size={14} />
            Geler le dataset revu
          </button>
        )}
        {key === "annotation" &&
          allowed("scientific_reviewer") &&
          data.items.length > 0 && (
            <div className="button-row">
              {data.items
                .filter((r) => r.review_state !== "resolved")
                .map((r) => (
                  <button
                    className="btn"
                    key={r.id}
                    onClick={() =>
                      ask(
                        "Résoudre une annotation indépendante",
                        (v) =>
                          post("/annotations/" + r.id + "/resolve", {
                            expected_version: r.version,
                            ...v,
                          }),
                        [
                          {
                            name: "reference_label",
                            label: "Label de référence",
                            options: verdicts,
                            value: r.label,
                          },
                          {
                            name: "rationale",
                            label: "Justification",
                            type: "textarea",
                            required: true,
                          },
                        ],
                        "Votre identité doit être différente de celle de l’annotateur initial.",
                      )
                    }
                  >
                    Résoudre : {r.title?.slice(0, 45)}
                  </button>
                ))}
            </div>
          )}
        {key === "evaluation" &&
          allowed("scientific_reviewer") &&
          data.items.length > 0 && (
            <div className="button-row">
              {data.items.map((r) => (
                <button
                  className="btn"
                  key={r.id}
                  onClick={() =>
                    ask(
                      "Mesurer des prédictions sur le benchmark",
                      (v) =>
                        post("/evaluations/" + r.id + "/measure", {
                          expected_version: r.version,
                          model_version: v.model_version,
                          predictions: JSON.parse(v.predictions),
                        }),
                      [
                        {
                          name: "model_version",
                          label: "Modèle / version / prompt",
                          required: true,
                        },
                        {
                          name: "predictions",
                          label: "JSON : annotation ID → predicted label",
                          type: "textarea",
                          value: JSON.stringify(
                            Object.fromEntries(
                              (r.dataset || []).map((a: any) => [
                                a.id,
                                "unassessed",
                              ]),
                            ),
                            null,
                            2,
                          ),
                          required: true,
                        },
                      ],
                      "Le backend calcule les métriques et la matrice de confusion depuis les prédictions; les seuils de release restent à approuver.",
                    )
                  }
                >
                  Mesurer : {r.title}
                </button>
              ))}
            </div>
          )}
        {key === "evaluation" && (
          <div className="info-box">
            <FlaskConical />
            <div>
              <strong>Aucun benchmark validé.</strong>
              <p>
                Aucun modèle n’est sélectionné ni évalué. Les performances par
                langue, calibration, coûts et critères de release restent à
                mesurer sur un corpus revu.
              </p>
            </div>
          </div>
        )}
        {key === "impact" && (
          <div className="info-box">
            <Info />
            <div>
              Les observations avant / après ne prouvent pas un effet causal.
              Comparez seulement les fenêtres avec une couverture stable.
            </div>
          </div>
        )}
        {key === "admin" && (
          <div className="info-box">
            <Lock />
            <div>
              Les comptes de formation sont initialisés avec des rôles séparés.
              L’intégration OIDC, MFA et l’onboarding de production restent à
              configurer.
            </div>
          </div>
        )}
        <div className="list-toolbar">
          <div className="search-inline">
            <Search size={15} />
            <input
              aria-label="Search records"
              placeholder="Rechercher / Search…"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setCursor(0);
              }}
            />
          </div>
          {["cases", "content"].includes(kind) && (
            <select
              aria-label={t("topic")}
              value={topic}
              onChange={(e) => {
                setTopic(e.target.value);
                setCursor(0);
              }}
            >
              <option value="">Tous les thèmes</option>
              {topicOptions.map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          )}
          <span className="muted">{data.total} records</span>
          <button
            className="icon-btn"
            aria-label={t("retry")}
            onClick={refresh}
          >
            <RefreshCw size={15} />
          </button>
        </div>
        {kind === "cases" ? (
          data.items.length ? (
            <section className="panel">{caseRows(data.items)}</section>
          ) : (
            <Empty />
          )
        ) : (
          renderCards(
            kind,
            path === "/evidence/reviews"
              ? data.items.filter((x) => x.state === "pending")
              : data.items,
          )
        )}
        <div className="pagination">
          <button
            className="btn"
            disabled={cursor === 0}
            onClick={() => setCursor(Math.max(0, cursor - 50))}
          >
            Previous
          </button>
          <span>
            {cursor + 1}–{Math.min(cursor + 50, data.total)} / {data.total}
          </span>
          <button
            className="btn"
            disabled={data.next_cursor === null}
            onClick={() => setCursor(data.next_cursor || 0)}
          >
            Next
          </button>
        </div>
      </>
    );
  }

  return (
    <div
      className={"app " + (mobile ? "mobile-open" : "")}
      dir={rtl ? "rtl" : "ltr"}
    >
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      <aside className="sidebar" id="workspace-navigation">
        <div className="brand">
          <span className="brand-icon">
            <Activity size={24} />
          </span>
          <span>
            PNSI<small>HEALTH INTELLIGENCE</small>
          </span>
        </div>
        <div className="workspace-name">
          <span className="workspace-mark">TN</span>
          <div>
            Atelier PNSI<small>Institution de démonstration</small>
          </div>
          <Lock size={12} />
        </div>
        <nav aria-label="Main navigation">
          {nav.map((n, i) => (
            <Fragment key={n.key}>
              {(i === 0 || nav[i - 1].group !== n.group) && (
                <div className="nav-section">
                  {
                    ["OBSERVER & COMPRENDRE", "VÉRIFIER & AGIR", "PILOTER"][
                      n.group
                    ]
                  }
                </div>
              )}
              <button
                className={
                  "nav-item " + (current?.key === n.key ? "active" : "")
                }
                onClick={() => go(n.path)}
              >
                <n.icon size={17} />
                <span>{t(n.key)}</span>
                {n.key === "alerts" && <span className="nav-dot" />}
              </button>
            </Fragment>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <button className="nav-item" onClick={() => go("/help")}>
            <BookOpen size={17} />
            {t("help")}
            <ArrowUpRight size={13} />
          </button>
          <button className="profile-button" onClick={() => go("/profile")}>
            <span className="avatar">{user.name[0]}</span>
            <div>
              <strong>{user.name.split(" · ")[0]}</strong>
              <small>{user.role.replaceAll("_", " ")}</small>
            </div>
            <ChevronDown size={14} />
          </button>
        </div>
      </aside>
      {mobile && (
        <button
          className="nav-overlay"
          aria-label="Close navigation"
          onClick={() => setMobile(false)}
        />
      )}
      <div className="main-shell">
        <header className="topbar">
          <button
            className="icon-btn mobile-menu"
            aria-expanded={mobile}
            aria-controls="workspace-navigation"
            aria-label="Menu"
            onClick={() => setMobile(!mobile)}
          >
            <Menu size={20} />
          </button>
          <div className="breadcrumb">
            Espace de travail <ChevronRight size={13} />
            <strong>
              {caseId
                ? "Dossier"
                : responseId
                  ? "Réponse"
                  : t(current?.key || path.slice(1))}
            </strong>
          </div>
          <div className="global-search">
            <Search size={15} />
            <input
              aria-label={t("search")}
              placeholder={t("search")}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <div className="top-actions">
            <Globe2 size={15} />
            <select
              aria-label="Interface language"
              value={locale}
              onChange={(e) => setLocale(e.target.value as Locale)}
            >
              <option value="fr">FR</option>
              <option value="en">EN</option>
              <option value="ar">العربية</option>
              <option value="derja">تونسي</option>
              <option value="derja-latin">Derja Latin</option>
            </select>
            <span className="top-divider" />
            <button
              className="icon-btn notification-btn"
              aria-label={t("notifications")}
              onClick={() => go("/alerts")}
            >
              <Bell size={18} />
              <span />
            </button>
            <span className="avatar small">{user.name[0]}</span>
          </div>
        </header>
        <div className="demo-banner">
          <span>
            <span className="demo-dot" />
            <strong>{isLocal ? "Espace local personnel" : t("demo")}</strong>
            <span className="banner-divider" />
            {isLocal
              ? "Tes comptes · tes données · stockage sur ce PC"
              : t("demoNote")}
          </span>
          <span>
            <ShieldCheck size={13} />
            Proposition · validation humaine
          </span>
        </div>
        {locale !== "fr" && (
          <div className="translation-banner">
            Interface translations provisional · local linguistic review
            required, especially Derja. Records retain original language.
          </div>
        )}
        <main id="main">
          <div className="error" role="alert" hidden={!error}>
            <AlertTriangle size={17} />
            <span>{error}</span>
            <button className="text-btn" onClick={refresh}>
              {t("retry")}
            </button>
            <button
              className="icon-btn"
              aria-label="Dismiss"
              onClick={() => setError("")}
            >
              <X size={15} />
            </button>
          </div>
          {busy ? (
            <div className="loading">
              <RefreshCw className="spin" />
              <p>{t("loading")}</p>
            </div>
          ) : error && !detail && !overview && !data.items.length ? (
            <div className="empty">
              <Lock />
              <h2>{t("restricted")}</h2>
            </div>
          ) : path === "/overview" ? (
            dashboard()
          ) : caseId ? (
            casePage()
          ) : responseId && detail ? (
            responseCard(detail)
          ) : path === "/imports" ? (
            importsPage()
          ) : path === "/help" ? (
            <>
              <div className="page-intro">
                <div>
                  <div className="eyebrow">PNSI / HANDBOOK</div>
                  <h1>{t("help")}</h1>
                  <p>Une revue humaine à chaque étape décisive.</p>
                </div>
              </div>
              <div className="cards-grid">
                {[
                  [
                    "01",
                    "Analyste",
                    "Importez uniquement des contenus autorisés. Prévisualisez la redaction; ouvrez un dossier, attribuez-le et demandez une recherche de preuves.",
                  ],
                  [
                    "02",
                    "Reviewer scientifique",
                    "Inspectez les passages, les dates et les contradictions. Confirmez ou révisez l’évaluation avec une justification. L’absence de preuves conduit à l’abstention.",
                  ],
                  [
                    "03",
                    "Communication",
                    "Créez une variante depuis une évaluation confirmée. Demandez la revue scientifique, puis vérifiez la langue et l’équivalence. Chaque variante a ses propres revues.",
                  ],
                  [
                    "04",
                    "Approbateur institutionnel",
                    "Approuvez une version exacte après les deux revues. Une modification invalide l’approbation. La plateforme ne publie jamais automatiquement.",
                  ],
                  [
                    "05",
                    "Suivi",
                    "Enregistrez la publication réelle. Documentez les fenêtres à 48h, 7j et 30j, les sources et les limites. Évitez une attribution causale.",
                  ],
                  [
                    "06",
                    "Opérations",
                    "Contrôlez les jobs et la fraîcheur des sources. Les connecteurs indisponibles ne produisent pas de données de remplacement.",
                  ],
                ].map(([i, title, body]) => (
                  <article className="card" key={i}>
                    <span className="step-number">{i}</span>
                    <h2>{title}</h2>
                    <p>{body}</p>
                  </article>
                ))}
              </div>
            </>
          ) : path === "/profile" ? (
            <section className="panel pad profile-panel">
              <h1>{t("profile")}</h1>
              <div className="owner">
                <span className="avatar">{user.name[0]}</span>
                <h2>{user.name}</h2>
              </div>
              <dl>
                <dt>Email</dt>
                <dd>{user.email}</dd>
                <dt>Role</dt>
                <dd>{user.role}</dd>
                <dt>Institution</dt>
                <dd>{user.institution}</dd>
                <dt>Timezone</dt>
                <dd>{user.timezone}</dd>
              </dl>
              {isLocal && <PasswordChange onComplete={signedOut} />}
              <button
                className="btn"
                onClick={() =>
                  ask(
                    "Préférences du profil",
                    async (v) => {
                      const d = await api<Entity>("/profile", {
                        method: "PUT",
                        body: JSON.stringify({ data: v }),
                      });
                      setUser(d);
                      setLocale(v.locale);
                      return d;
                    },
                    [
                      {
                        name: "locale",
                        label: "Locale",
                        options: ["fr", "en", "ar", "derja", "derja-latin"],
                        value: locale,
                      },
                      {
                        name: "timezone",
                        label: "Timezone",
                        options: ["Africa/Tunis", "Europe/London", "UTC"],
                        value: user.timezone,
                      },
                    ],
                  )
                }
              >
                Modifier les préférences
              </button>
              <button
                className="btn danger"
                onClick={() =>
                  act(async () => {
                    await post("/auth/logout", {});
                    sessionStorage.removeItem("pnsi-token");
                    setUser(null);
                  })
                }
              >
                <LogOut size={14} />
                {t("logout")}
              </button>
            </section>
          ) : (
            listPage()
          )}
          <footer>
            {" "}
            PNSI · {isLocal ? "Espace local" : "Prototype institutionnel"}{" "}
            <span>
              Sources sélectionnées ·{" "}
              {isLocal ? "Données locales" : "Données de démonstration"} ·
              Africa/Tunis
            </span>
          </footer>
        </main>
      </div>
      {toast && (
        <div className="toast" role="status">
          <CheckCircle2 size={17} />
          {toast}
        </div>
      )}
      {form && (
        <FormModal
          form={form}
          onClose={() => setForm(null)}
          onSave={async (v) => {
            await form.submit(v);
            setForm(null);
            refresh();
            setToast("Enregistré / Saved");
          }}
          t={t}
        />
      )}
    </div>
  );
}
function FormModal({
  form,
  onClose,
  onSave,
  t,
}: {
  form: Form;
  onClose: () => void;
  onSave: (v: any) => Promise<void>;
  t: (key: string) => string;
}) {
  const [values, setValues] = useState<Record<string, any>>(() =>
      Object.fromEntries(
        form.fields.map((f) => [f.name, f.value ?? f.options?.[0] ?? ""]),
      ),
    ),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement;
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab") {
        const elements = Array.from(
          document.querySelectorAll<HTMLElement>(
            ".modal button,.modal input,.modal select,.modal textarea",
          ),
        );
        const first = elements[0],
          last = elements[elements.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    document
      .querySelector<HTMLElement>(".modal input,.modal select,.modal textarea")
      ?.focus();
    return () => {
      document.removeEventListener("keydown", key);
      previous?.focus();
    };
  }, [onClose]);
  return (
    <div className="modal-overlay">
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <div className="modal-header">
          <h2 id="modal-title">{form.title}</h2>
          <button className="icon-btn" aria-label="Close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
        {form.description && (
          <p className="modal-description">{form.description}</p>
        )}
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            setError("");
            try {
              await onSave(values);
            } catch (err) {
              setError(err instanceof Error ? err.message : String(err));
            } finally {
              setBusy(false);
            }
          }}
        >
          {form.fields.map((f) => (
            <label key={f.name}>
              {f.label}
              {f.required && " *"}
              {f.options ? (
                <select
                  required={f.required}
                  value={values[f.name]}
                  onChange={(e) =>
                    setValues({ ...values, [f.name]: e.target.value })
                  }
                >
                  {f.options.length ? (
                    f.options.map((o) => <option key={o}>{o}</option>)
                  ) : (
                    <option value="">No approved source available</option>
                  )}
                </select>
              ) : f.type === "textarea" ? (
                <textarea
                  rows={5}
                  required={f.required}
                  value={values[f.name]}
                  onChange={(e) =>
                    setValues({ ...values, [f.name]: e.target.value })
                  }
                />
              ) : (
                <input
                  type={f.type || "text"}
                  min={f.type === "number" ? 0 : undefined}
                  max={f.name === "priority" ? 100 : undefined}
                  required={f.required}
                  value={values[f.name]}
                  onChange={(e) =>
                    setValues({ ...values, [f.name]: e.target.value })
                  }
                />
              )}
            </label>
          ))}
          {error && (
            <div className="error" role="alert">
              {error}
            </div>
          )}
          <div className="modal-footer">
            <button type="button" className="btn" onClick={onClose}>
              {t("cancel")}
            </button>
            <button className="btn primary" disabled={busy}>
              {busy ? "Saving…" : t("save")}
              <Check size={15} />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
