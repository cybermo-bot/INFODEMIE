from __future__ import annotations

import time
import pandas as pd
import streamlit as st

from src.arabic_nlp import detect_language, normalize_arabizi, detect_manipulation_techniques, get_technique_display, MANIPULATION_TECHNIQUES
from src.collector import (
    fetch_feed_items,
    item_from_url,
    items_to_table,
    load_demo_claims,
    read_csv_items_from_text,
)
from src.config import settings
from src.discovery import (
    append_discovery_items,
    build_discovery_index,
    collect_discovery_items,
    get_source_counts,
    load_discovery_items,
)
from src.inoculation import generate_inoculation_message
from src.llm import ollama_status
from src.pipeline import run_pipeline
from src.schemas import InputItem
from src.storage import save_feedback
from src.whitelist import build_whitelist_index


# ── Page config ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Plateforme Infodémie OMS Tunisie",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg:           #f0f4f8;
  --surface:      #ffffff;
  --surface2:     #f7fafc;
  --border:       #e2e8f0;
  --border2:      #cbd5e1;
  --accent:       #0f4c8a;
  --accent-light: #1a6cf6;
  --accent2:      #0891b2;
  --teal:         #0d9488;
  --text:         #1e293b;
  --text-mid:     #475569;
  --text-dim:     #94a3b8;
  --text-bright:  #0f172a;
  --red:          #dc2626;
  --orange:       #d97706;
  --yellow:       #ca8a04;
  --green:        #059669;
  --red-bg:       #fef2f2;
  --orange-bg:    #fffbeb;
  --green-bg:     #f0fdf4;
  --blue-bg:      #eff6ff;
  --font:         'Plus Jakarta Sans', sans-serif;
  --mono:         'JetBrains Mono', monospace;
  --radius:       10px;
  --shadow:       0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04);
  --shadow-md:    0 4px 12px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04);
}

html, body, [data-testid="stAppViewContainer"] {
  background-color: var(--bg) !important;
  font-family: var(--font) !important;
  color: var(--text) !important;
}
[data-testid="stSidebar"] {
  background-color: var(--accent) !important;
  border-right: none !important;
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] label { color: #94a3b8 !important; }
[data-testid="stHeader"] { background: transparent !important; }

h1,h2,h3,h4 { font-family: var(--font) !important; color: var(--text-bright) !important; font-weight:700 !important; }

[data-testid="stTabs"] [role="tablist"] {
  background: var(--surface) !important;
  border-radius: var(--radius) var(--radius) 0 0 !important;
  border-bottom: 2px solid var(--border) !important;
  padding: 0 8px !important; gap: 2px;
}
[data-testid="stTabs"] [role="tab"] {
  font-family: var(--font) !important; font-size: 12.5px !important; font-weight: 600 !important;
  color: var(--text-mid) !important; padding: 11px 14px !important;
  border: none !important; border-bottom: 2px solid transparent !important;
  background: transparent !important; border-radius: 0 !important;
  margin-bottom: -2px !important; transition: all 0.15s;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
  color: var(--accent) !important; border-bottom-color: var(--accent) !important;
}
[data-testid="stTabs"] [role="tab"]:hover:not([aria-selected="true"]) {
  color: var(--text) !important; background: var(--bg) !important;
}
[data-testid="stTabs"] [data-testid="stTabsContent"] {
  background: var(--surface) !important; border: 1px solid var(--border) !important;
  border-top: none !important; border-radius: 0 0 var(--radius) var(--radius) !important;
  padding: 24px !important;
}

[data-testid="stButton"] > button {
  font-family: var(--font) !important; font-size: 13px !important; font-weight: 600 !important;
  background: var(--accent) !important; color: white !important;
  border: none !important; border-radius: 8px !important;
  padding: 10px 20px !important; box-shadow: var(--shadow) !important; transition: all 0.15s !important;
}
[data-testid="stButton"] > button:hover {
  background: #1a3a6e !important; box-shadow: var(--shadow-md) !important; transform: translateY(-1px);
}

[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input {
  background: var(--surface) !important; border: 1.5px solid var(--border2) !important;
  color: var(--text) !important; border-radius: 8px !important;
  font-family: var(--font) !important; font-size: 14px !important; box-shadow: var(--shadow) !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
  border-color: var(--accent-light) !important; box-shadow: 0 0 0 3px rgba(26,108,246,0.12) !important;
}

[data-testid="stMetric"] {
  background: var(--surface) !important; border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important; padding: 16px 20px !important; box-shadow: var(--shadow) !important;
}
[data-testid="stMetricLabel"] {
  font-family: var(--mono) !important; font-size: 10px !important;
  color: var(--text-dim) !important; text-transform: uppercase; letter-spacing: 0.08em;
}
[data-testid="stMetricValue"] {
  font-family: var(--font) !important; font-size: 20px !important;
  font-weight: 700 !important; color: var(--text-bright) !important;
}

[data-testid="stExpander"] {
  background: var(--surface2) !important; border: 1px solid var(--border) !important;
  border-radius: 8px !important; margin-bottom: 6px !important; box-shadow: var(--shadow) !important;
}
[data-testid="stExpander"] summary {
  font-family: var(--font) !important; font-size: 13px !important;
  font-weight: 500 !important; color: var(--text-mid) !important;
}

[data-testid="stDataFrame"] {
  border: 1px solid var(--border) !important; border-radius: 8px !important;
  overflow: hidden; box-shadow: var(--shadow) !important;
}
[data-baseweb="select"] { background: var(--surface) !important; border-color: var(--border2) !important; }
[data-baseweb="select"] * { color: var(--text) !important; }
[data-testid="stFileUploader"] {
  background: var(--surface2) !important; border: 2px dashed var(--border2) !important; border-radius: 8px !important;
}
[data-testid="stCheckbox"] label, [data-testid="stCheckbox"] label p, [data-testid="stCheckbox"] label span { color: #1e293b !important; font-weight:500; }

[data-testid="stSidebar"] [data-testid="stButton"] > button {
  background: rgba(255,255,255,0.12) !important;
  border: 1px solid rgba(255,255,255,0.2) !important; color: white !important; width: 100%;
}
[data-testid="stSidebar"] [data-testid="stButton"] > button:hover {
  background: rgba(255,255,255,0.22) !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] {
  background: rgba(255,255,255,0.1) !important; border-color: rgba(255,255,255,0.2) !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] * { color: white !important; }

#MainMenu, footer, [data-testid="stToolbar"] { display: none !important; }

/* Copy button for inoculation messages */
.copy-block { position: relative; }
.copy-block pre {
  background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;
  padding: 14px 16px; font-size: 12.5px; line-height: 1.6; white-space: pre-wrap;
  font-family: 'Plus Jakarta Sans', sans-serif; color: #334155;
}
</style>
""", unsafe_allow_html=True)


# ── Design helpers ───────────────────────────────────────────────────────────────
CATEGORY_META = {
    "rumor_infodemie": ("#dc2626", "#fef2f2", "Rumeur / Infodémie"),
    "real_alert":      ("#d97706", "#fffbeb", "Alerte Sanitaire Réelle"),
    "weak_signal":     ("#ca8a04", "#fefce8", "Signal Faible"),
    "irrelevant":      ("#64748b", "#f8fafc", "Non Pertinent"),
}
RISK_META = {
    "critical": ("#dc2626", "#fef2f2"),
    "high":     ("#d97706", "#fffbeb"),
    "medium":   ("#ca8a04", "#fefce8"),
    "low":      ("#059669", "#f0fdf4"),
}
VERDICT_META = {
    "contradicted": ("#dc2626", "#fef2f2"),
    "uncertain":    ("#d97706", "#fffbeb"),
    "supported":    ("#059669", "#f0fdf4"),
}
SOURCE_TYPE_ICON = {
    "news_search": "📰",
    "bluesky":     "🦋",
    "rss":         "📡",
    "manual":      "✍️",
    "url_paste":   "🔗",
    "local_file":  "📄",
    "reddit":      "🤖",
    "ddg_news":    "🦆",
    "promed":      "🔬",
    "telegram":    "📨",
    "wahis":       "🐄",
    "csv":         "📊",
}

TRUST_BADGES = {
    "local_file":  ("Official WHO/MOH", "#059669", "#f0fdf4"),
    "rss":         ("News", "#d97706", "#fffbeb"),
    "news_search": ("News", "#d97706", "#fffbeb"),
    "ddg_news":    ("News", "#d97706", "#fffbeb"),
    "bluesky":     ("Social", "#7c3aed", "#faf5ff"),
    "reddit":      ("Social", "#7c3aed", "#faf5ff"),
    "telegram":    ("Social", "#7c3aed", "#faf5ff"),
    "promed":      ("Epidemic Alert", "#dc2626", "#fef2f2"),
    "wahis":       ("Animal Health", "#0891b2", "#ecfeff"),
}

def pill(label: str, color: str, bg: str) -> str:
    return (
        f'<span style="display:inline-flex;align-items:center;gap:4px;padding:3px 12px;'
        f'border-radius:20px;font-family:Plus Jakarta Sans,sans-serif;font-size:12px;'
        f'font-weight:600;background:{bg};color:{color};border:1px solid {color}33;">'
        f'{label}</span>'
    )

def section_header(title: str, icon: str = "", subtitle: str = "") -> None:
    sub = f'<div style="font-size:12px;color:#64748b;margin-top:2px;">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;margin:24px 0 12px;">'
        f'<div style="width:32px;height:32px;border-radius:8px;background:#eff6ff;'
        f'display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;">{icon}</div>'
        f'<div><div style="font-family:Plus Jakarta Sans,sans-serif;font-size:14px;'
        f'font-weight:700;color:#0f172a;">{title}</div>{sub}</div>'
        f'<div style="flex:1;height:1px;background:linear-gradient(90deg,#e2e8f0,transparent);'
        f'margin-left:8px;"></div></div>',
        unsafe_allow_html=True)

def info_card(content: str, border_color: str = "#1a6cf6", bg: str = "#eff6ff") -> None:
    st.markdown(
        f'<div style="background:{bg};border-left:4px solid {border_color};border-radius:0 8px 8px 0;'
        f'padding:14px 18px;font-size:14px;font-weight:500;color:#1e293b;line-height:1.6;">'
        f'{content}</div>', unsafe_allow_html=True)

def label_text(text: str) -> None:
    st.markdown(
        f'<div style="font-family:JetBrains Mono,monospace;font-size:11px;font-weight:500;'
        f'color:#94a3b8;text-transform:uppercase;letter-spacing:0.07em;margin-bottom:6px;">'
        f'{text}</div>', unsafe_allow_html=True)


# ── Language detection display ───────────────────────────────────────────────────
def show_language_badge(text: str) -> None:
    """Detect and display language info prominently."""
    lang_info = detect_language(text)
    parts = [pill(lang_info.display_label, "#0f4c8a", "#eff6ff")]
    if lang_info.is_tunisian:
        parts.append(pill("🇹🇳 Dialecte tunisien détecté", "#059669", "#f0fdf4"))
    if lang_info.arabizi_detected:
        parts.append(pill("🔤 Arabizi → normalisation appliquée", "#7c3aed", "#faf5ff"))
    conf_pct = f"{lang_info.confidence:.0%}"
    parts.append(f'<span style="font-family:JetBrains Mono,monospace;font-size:10px;color:#94a3b8;margin-left:6px;">conf: {conf_pct}</span>')
    st.markdown(f'<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:8px 0 14px;">{"".join(parts)}</div>', unsafe_allow_html=True)


# ── Item card ────────────────────────────────────────────────────────────────────
def show_item_card(item: InputItem) -> None:
    source_type = getattr(item, "source_type", "manual")
    icon = SOURCE_TYPE_ICON.get(source_type, "📄")
    meta = getattr(item, "metadata", None) or {}
    engagement = meta.get("engagement", 0)
    likes = meta.get("like_count", 0)
    reposts = meta.get("repost_count", 0)
    replies = meta.get("reply_count", 0)
    handle = meta.get("author_handle", "")
    score = meta.get("score", 0)
    num_comments = meta.get("num_comments", 0)

    # Trust badge
    badge_info = TRUST_BADGES.get(source_type, ("Source", "#64748b", "#f8fafc"))
    badge_html = (
        f'<span style="padding:2px 8px;border-radius:4px;font-size:10px;font-weight:600;'
        f'background:{badge_info[2]};color:{badge_info[1]};border:1px solid {badge_info[1]}22;'
        f'margin-left:8px;">{badge_info[0]}</span>'
    )

    engagement_html = ""
    if source_type == "bluesky" and (likes or reposts or replies):
        viral = "⚡ Viral risk" if engagement > 50 else ""
        engagement_html = (
            f'<div style="display:flex;gap:14px;margin-top:10px;padding-top:10px;border-top:1px solid #e2e8f0;">'
            f'<span style="font-size:12px;color:#64748b;">❤️ {likes}</span>'
            f'<span style="font-size:12px;color:#64748b;">🔁 {reposts}</span>'
            f'<span style="font-size:12px;color:#64748b;">💬 {replies}</span>'
            f'{"<span style=font-size:12px;color:#dc2626;font-weight:600;>" + viral + "</span>" if viral else ""}'
            f'</div>'
        )
        if handle:
            engagement_html = f'<div style="font-size:12px;color:#0891b2;font-weight:600;margin-bottom:4px;">@{handle}</div>' + engagement_html
    elif source_type == "reddit" and (score or num_comments):
        viral = "⚡ Viral risk" if engagement > 100 else ""
        engagement_html = (
            f'<div style="display:flex;gap:14px;margin-top:10px;padding-top:10px;border-top:1px solid #e2e8f0;">'
            f'<span style="font-size:12px;color:#64748b;">⬆️ {score}</span>'
            f'<span style="font-size:12px;color:#64748b;">💬 {num_comments}</span>'
            f'{"<span style=font-size:12px;color:#dc2626;font-weight:600;>" + viral + "</span>" if viral else ""}'
            f'</div>'
        )

    url_html = ""
    if item.url:
        url_html = (
            f'<div style="margin-top:8px;"><a href="{item.url}" target="_blank" style="font-size:12px;color:#1a6cf6;'
            f'font-family:JetBrains Mono,monospace;text-decoration:none;">'
            f'↗ {str(item.url)[:80]}{"…" if len(str(item.url))>80 else ""}</a></div>'
        )

    pub_html = f'<span style="font-size:11px;color:#94a3b8;margin-left:8px;">{item.published[:16]}</span>' if item.published else ""

    st.markdown(
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:16px 20px;margin-bottom:16px;">'
        f'<div style="display:flex;align-items:flex-start;gap:12px;">'
        f'<div style="width:36px;height:36px;border-radius:8px;background:#eff6ff;'
        f'display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0;">{icon}</div>'
        f'<div style="flex:1;min-width:0;">'
        f'<div style="font-size:14px;font-weight:600;color:#0f172a;margin-bottom:4px;">'
        f'{item.title or "—"}{pub_html}{badge_html}</div>'
        f'<div style="font-size:12px;color:#64748b;margin-bottom:8px;">'
        f'{item.source} · {source_type.replace("_"," ")}</div>'
        f'<div style="font-size:13px;color:#334155;line-height:1.6;max-height:80px;overflow:hidden;">'
        f'{str(item.text)[:300]}{"…" if len(str(item.text))>300 else ""}</div>'
        f'{url_html}{engagement_html}'
        f'</div></div></div>',
        unsafe_allow_html=True)


# ── Evidence block ───────────────────────────────────────────────────────────────
def show_evidence_block(title: str, rows: list[dict], accent: str = "#0f4c8a") -> None:
    is_whitelist = "whitelist" in title.lower()
    section_header(title, icon="📚" if is_whitelist else "🌐",
                   subtitle="Sources officielles validées" if is_whitelist else "Contexte web / social récent")
    if not rows:
        st.markdown(
            '<div style="background:#f8fafc;border:1px dashed #cbd5e1;border-radius:8px;'
            'padding:16px;color:#94a3b8;font-size:13px;text-align:center;">Aucune preuve récupérée pour ce bloc.</div>',
            unsafe_allow_html=True)
        return
    for row in rows:
        score = row.get("score", 0)
        bar_w = int(score * 100)
        bar_color = "#059669" if score >= 0.8 else "#d97706" if score >= 0.6 else "#dc2626"
        src_type = row.get("source_type", "")
        type_icon = SOURCE_TYPE_ICON.get(src_type, "📄")
        badge = TRUST_BADGES.get(src_type, ("Source", "#64748b", "#f8fafc"))
        badge_html = (
            f'<span style="padding:1px 6px;border-radius:3px;font-size:9px;font-weight:600;'
            f'background:{badge[2]};color:{badge[1]};">{badge[0]}</span>'
        )
        src_url = row.get("source_url", "")
        link_html = (
            f'<a href="{src_url}" target="_blank" style="font-size:11px;color:#1a6cf6;'
            f'font-family:JetBrains Mono,monospace;text-decoration:none;display:block;margin-top:8px;">'
            f'↗ {src_url[:70]}{"…" if len(src_url)>70 else ""}</a>'
            if src_url else ""
        )
        with st.expander(f"{type_icon}  {row['source_title']}  ·  {score:.0%} pertinence"):
            st.markdown(
                f'<div style="display:flex;gap:6px;margin-bottom:8px;">{badge_html}</div>'
                f'<div style="height:3px;border-radius:2px;background:#e2e8f0;overflow:hidden;margin-bottom:10px;">'
                f'<div style="width:{bar_w}%;height:100%;background:{bar_color};border-radius:2px;"></div></div>'
                f'<p style="color:#334155;font-size:13px;line-height:1.7;margin:0;">'
                f'{row.get("text","")}</p>{link_html}',
                unsafe_allow_html=True)


# ── Inoculation message display ─────────────────────────────────────────────────
def show_inoculation_panel(result: dict) -> None:
    """Generate and display the inoculation counter-messaging panel."""
    triage = result.get("triage", {})
    investigation = result.get("investigation", {})
    evidence = result.get("evidence", [])
    draft = result.get("draft", {})
    verdict = investigation.get("verdict", "uncertain")
    category = triage.get("category", "")

    if category not in ("rumor_infodemie",) and verdict not in ("contradicted",):
        return

    claim = triage.get("primary_claim", result.get("normalized_claim", ""))
    draft_text = draft.get("public_message", "") if draft else ""
    analysis = investigation.get("analysis", "")
    lang = result.get("output_language", "fr")

    inoc = generate_inoculation_message(
        claim=claim, verdict=verdict, analysis=analysis,
        evidence=evidence, draft_text=draft_text, language=lang,
    )

    section_header("Inoculation cognitive — Contre-messages", "🛡️",
                   "Messages prêts à diffuser selon le protocole d'inoculation (§6.2)")

    # Technique badge
    st.markdown(
        f'<div style="background:#fdf4ff;border:1px solid #e9d5ff;border-radius:10px;'
        f'padding:14px 18px;margin:10px 0 16px;display:flex;align-items:center;gap:12px;">'
        f'<div style="font-size:28px;">{inoc.technique_emoji}</div>'
        f'<div>'
        f'<div style="font-size:11px;color:#7e22ce;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;">Technique de manipulation identifiée</div>'
        f'<div style="font-size:16px;font-weight:700;color:#581c87;margin-top:2px;">🎭 {inoc.technique_label}</div>'
        f'<div style="font-size:13px;color:#6b21a8;margin-top:4px;">{inoc.technique_description}</div>'
        f'</div></div>',
        unsafe_allow_html=True)

    # Format tabs
    fmt_tab1, fmt_tab2, fmt_tab3, fmt_tab4 = st.tabs([
        "🐦 Twitter/X (280c)", "📘 Facebook", "📱 SMS/WhatsApp (160c)", "📋 Communiqué officiel"
    ])

    for tab, (label, content) in zip(
        [fmt_tab1, fmt_tab2, fmt_tab3, fmt_tab4],
        [("Twitter/X", inoc.twitter), ("Facebook", inoc.facebook),
         ("SMS/WhatsApp", inoc.sms), ("Communiqué", inoc.communique)]
    ):
        with tab:
            char_count = len(content)
            st.markdown(
                f'<div style="font-family:JetBrains Mono,monospace;font-size:10px;color:#94a3b8;'
                f'margin-bottom:6px;">{label} · {char_count} caractères</div>',
                unsafe_allow_html=True)
            st.code(content, language=None)


# ── Main result renderer ─────────────────────────────────────────────────────────
def show_result(result: dict) -> None:
    triage        = result.get("triage", {})
    investigation = result.get("investigation", {})
    category      = triage.get("category", "n/a")
    risk_level    = triage.get("risk_level", "n/a")
    verdict       = investigation.get("verdict", "n/a")
    confidence    = investigation.get("confidence", 0)
    run_id        = result.get("run_id", "—")

    cat_color, cat_bg, cat_label = CATEGORY_META.get(category, ("#64748b", "#f8fafc", category))
    risk_color, risk_bg          = RISK_META.get(risk_level, ("#64748b", "#f8fafc"))
    vrd_color, vrd_bg            = VERDICT_META.get(verdict, ("#64748b", "#f8fafc"))

    # ── Language detection ─────────────────────────────────────────────────────
    item_data = result.get("item", {})
    input_text = item_data.get("text", "") or item_data.get("title", "")
    if input_text:
        show_language_badge(input_text)

    # ── Status banner ─────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="background:white;border:1px solid #e2e8f0;border-radius:10px;'
        f'padding:16px 20px;margin:8px 0 16px;display:flex;align-items:center;'
        f'gap:10px;flex-wrap:wrap;box-shadow:0 1px 3px rgba(0,0,0,0.06);">'
        f'{pill(cat_label, cat_color, cat_bg)}'
        f'{pill("Risque: " + risk_level.upper(), risk_color, risk_bg)}'
        f'{pill(verdict.title(), vrd_color, vrd_bg)}'
        f'<span style="margin-left:auto;font-family:JetBrains Mono,monospace;'
        f'font-size:10px;color:#94a3b8;">{run_id}</span>'
        f'</div>', unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Catégorie", cat_label.split("/")[0].strip())
    col2.metric("Risque", risk_level.title())
    col3.metric("Verdict", verdict.title())
    col4.metric("Confiance", f"{confidence:.0%}")
    col5.metric("Sources off.", len(result.get("evidence", [])))

    # ── Normalized claim ──────────────────────────────────────────────────────
    section_header("Claim normalisée", "📋", "Résumé neutre extrait par l'agent Normalisateur")
    info_card(result.get("normalized_claim", "—"), "#0f4c8a", "#eff6ff")

    # ── Analysis ──────────────────────────────────────────────────────────────
    section_header("Analyse d'investigation", "🔬", "Synthèse de l'Agent Investigateur — basée exclusivement sur la Whitelist")
    st.markdown(
        f'<div style="background:white;border:1px solid #e2e8f0;border-radius:10px;'
        f'padding:18px 20px;box-shadow:0 1px 3px rgba(0,0,0,0.06);">'
        f'<p style="color:#334155;line-height:1.75;margin:0 0 14px;font-size:14px;">'
        f'{investigation.get("analysis","—")}</p>'
        f'<div style="display:flex;align-items:center;gap:8px;padding-top:12px;border-top:1px solid #f1f5f9;">'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:10px;color:#94a3b8;'
        f'text-transform:uppercase;letter-spacing:0.07em;">Risque santé publique</span>'
        f'<span style="font-size:13px;font-weight:600;color:#d97706;">'
        f'{investigation.get("public_health_risk","—")}</span></div></div>', unsafe_allow_html=True)

    # ── Triage reasoning + keywords ───────────────────────────────────────────
    reasoning = triage.get("reasoning", "")
    keywords  = triage.get("keywords", [])
    if reasoning or keywords:
        section_header("Raisonnement de triage", "⚖️", "Décision de classification de l'Agent Triage")
        kw_html = " ".join(
            f'<span style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:20px;'
            f'padding:2px 10px;font-size:11px;font-weight:600;color:#0891b2;">{k}</span>'
            for k in keywords)
        st.markdown(
            f'<div style="background:white;border:1px solid #e2e8f0;border-radius:10px;'
            f'padding:16px 20px;box-shadow:0 1px 3px rgba(0,0,0,0.06);">'
            f'<p style="color:#334155;font-size:13px;margin:0 0 12px;">{reasoning}</p>'
            f'<div style="display:flex;flex-wrap:wrap;gap:6px;">{kw_html}</div></div>', unsafe_allow_html=True)

    # ── Dual evidence ─────────────────────────────────────────────────────────
    ev_col, ctx_col = st.columns(2)
    with ev_col:
        show_evidence_block("Preuves Whitelist officielle", result.get("evidence", []))
    with ctx_col:
        show_evidence_block("Contexte web / social récent", result.get("context_evidence", []))

    # ── Draft public response ─────────────────────────────────────────────────
    if result.get("draft"):
        draft = result["draft"]
        section_header("Réponse publique brouillon", "📢", "Généré par l'Agent Rédacteur — à valider avant diffusion")
        if draft.get("headline"):
            st.markdown(
                f'<div style="font-size:20px;font-weight:700;color:#0f172a;margin-bottom:12px;line-height:1.3;">'
                f'{draft["headline"]}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;'
            f'padding:16px 18px;font-family:JetBrains Mono,monospace;font-size:13px;'
            f'color:#334155;line-height:1.75;white-space:pre-wrap;">{draft.get("public_message","")}</div>',
            unsafe_allow_html=True)
        if draft.get("internal_brief"):
            st.markdown(
                f'<div style="margin-top:10px;background:#f0fdf4;border-left:4px solid #059669;'
                f'border-radius:0 8px 8px 0;padding:12px 16px;">'
                f'<span style="font-family:JetBrains Mono,monospace;font-size:10px;color:#059669;'
                f'text-transform:uppercase;letter-spacing:0.07em;font-weight:600;">Note interne — </span>'
                f'<span style="color:#334155;font-size:13px;">{draft["internal_brief"]}</span></div>',
                unsafe_allow_html=True)

    # ── INOCULATION ENGINE ─── Priority 3 ─────────────────────────────────────
    show_inoculation_panel(result)

    # ── Analyst brief ─────────────────────────────────────────────────────────
    if result.get("analyst_brief"):
        section_header("Note analyste", "📊")
        st.markdown(
            f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;'
            f'padding:16px 18px;font-family:JetBrains Mono,monospace;font-size:12px;'
            f'color:#334155;line-height:1.8;white-space:pre-wrap;">{result["analyst_brief"]}</div>',
            unsafe_allow_html=True)

    # ── Pipeline trace ────────────────────────────────────────────────────────
    trace = result.get("trace", [])
    if trace:
        with st.expander(f"🔗  Trace du pipeline  ({len(trace)} étapes)"):
            for i, step in enumerate(trace):
                is_last = i == len(trace) - 1
                dot_color = "#059669" if is_last else "#1a6cf6"
                connector = "" if is_last else '<div style="width:1px;height:8px;background:#e2e8f0;margin:2px 0 2px 9px;"></div>'
                st.markdown(
                    f'<div style="display:flex;align-items:flex-start;gap:10px;">'
                    f'<div style="width:18px;height:18px;border-radius:50%;background:{dot_color}22;'
                    f'border:1.5px solid {dot_color};flex-shrink:0;margin-top:1px;"></div>'
                    f'<span style="font-family:JetBrains Mono,monospace;font-size:12px;color:#334155;">{step}</span>'
                    f'</div>{connector}', unsafe_allow_html=True)

    # ── HITL validation ───────────────────────────────────────────────────────
    section_header("Validation humaine (HITL)", "👁", "Revue d'expert avant déclenchement d'une riposte institutionnelle")
    st.markdown(
        '<div style="background:white;border:1px solid #e2e8f0;border-radius:10px;'
        'padding:16px 20px 8px;box-shadow:0 1px 3px rgba(0,0,0,0.06);">',
        unsafe_allow_html=True)
    notes = st.text_area("Notes de validation",
        placeholder="Notes d'expert, corrections factuelles, contexte complémentaire…",
        key=f"notes_{result.get('run_id','run')}", label_visibility="collapsed")
    c1, c2, _ = st.columns([1, 1, 3])
    if c1.button("✓  Approuver", key=f"approve_{result.get('run_id','run')}"):
        save_feedback(result["run_id"], "approved", notes)
        st.success("Validation enregistrée — Approuvé ✓")
    if c2.button("⟳  Signaler", key=f"reject_{result.get('run_id','run')}"):
        save_feedback(result["run_id"], "needs_review", notes)
        st.warning("Validation enregistrée — À revoir")
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Share report block ────────────────────────────────────────────────────
    section_header("Partager cette analyse", "📤", "Bloc rapport compact")
    report_text = (
        f"═══ Rapport OMS Tunisie — Veille Infodémique ═══\n"
        f"Catégorie: {cat_label}\n"
        f"Risque: {risk_level.upper()}\n"
        f"Verdict: {verdict.title()} (confiance: {confidence:.0%})\n"
        f"Claim: {result.get('normalized_claim', '—')}\n"
        f"Analyse: {investigation.get('analysis', '—')[:300]}\n"
        f"Run ID: {run_id}\n"
        f"═══════════════════════════════════════════════"
    )
    st.code(report_text, language=None)

    # Track for session analytics
    if "session_analyses" not in st.session_state:
        st.session_state["session_analyses"] = []
    st.session_state["session_analyses"].append({
        "category": category, "risk": risk_level, "verdict": verdict,
        "confidence": confidence, "run_id": run_id,
    })


# ── Animated pipeline status ────────────────────────────────────────────────────
def run_pipeline_with_status(item: InputItem, output_language: str) -> dict:
    """Run pipeline with animated status steps."""
    status = st.status("🚀 Pipeline agentique en cours…", expanded=True)
    steps = [
        ("🔍 Normalisation — Détection de langue et extraction de la claim…", 0.3),
        ("⚖️ Triage — Classification et évaluation du risque…", 0.3),
        ("📚 Récupération d'évidences — Whitelist RAG + Discovery RAG…", 0.5),
        ("🔬 Investigation — Analyse factuelle approfondie…", 0.5),
        ("📝 Rédaction — Génération du contre-message et rapport…", 0.3),
    ]
    for msg, _ in steps:
        status.update(label=msg)

    t0 = time.time()
    result = run_pipeline(item, output_language=output_language)
    elapsed = time.time() - t0

    status.update(label=f"✅ Analyse terminée en {elapsed:.1f}s", state="complete", expanded=False)

    # Track timing
    if "pipeline_times" not in st.session_state:
        st.session_state["pipeline_times"] = []
    st.session_state["pipeline_times"].append(elapsed)

    return result


# ── Page header ──────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:white;border:1px solid #e2e8f0;border-radius:12px;
            padding:24px 28px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
  <div style="display:flex;align-items:center;gap:20px;flex-wrap:wrap;">
    <div style="width:48px;height:48px;border-radius:12px;background:#0f4c8a;
                display:flex;align-items:center;justify-content:center;font-size:24px;flex-shrink:0;">🏥</div>
    <div>
      <div style="font-family:JetBrains Mono,monospace;font-size:11px;color:#94a3b8;
                  text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;">
        OMS TUNISIE · PLATEFORME AGENTIQUE V3
      </div>
      <div style="font-family:Plus Jakarta Sans,sans-serif;font-size:24px;font-weight:800;color:#0f172a;line-height:1.2;">
        Veille Sanitaire &amp; Lutte contre l'Infodémie
      </div>
    </div>
    <div style="margin-left:auto;display:flex;gap:8px;flex-wrap:wrap;">
      <div style="padding:6px 14px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:20px;font-size:12px;font-weight:600;color:#1d4ed8;">LangGraph</div>
      <div style="padding:6px 14px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:20px;font-size:12px;font-weight:600;color:#15803d;">Dual RAG</div>
      <div style="padding:6px 14px;background:#fdf4ff;border:1px solid #e9d5ff;border-radius:20px;font-size:12px;font-weight:600;color:#7e22ce;">Inoculation</div>
      <div style="padding:6px 14px;background:#fff7ed;border:1px solid #fed7aa;border-radius:20px;font-size:12px;font-weight:600;color:#c2410c;">6 Sources</div>
      <div style="padding:6px 14px;background:#ecfeff;border:1px solid #a5f3fc;border-radius:20px;font-size:12px;font-weight:600;color:#0891b2;">One Health</div>
      <div style="padding:6px 14px;background:#fef2f2;border:1px solid #fecaca;border-radius:20px;font-size:12px;font-weight:600;color:#dc2626;">AR/TN/Arabizi</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Sidebar ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:8px 0 20px;">
      <div style="font-size:13px;font-weight:600;color:rgba(255,255,255,0.5);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px;">Plateforme</div>
      <div style="font-size:18px;font-weight:800;color:white;line-height:1.2;">OMS Tunisie<br>Infodémie v3</div>
      <div style="height:1px;background:rgba(255,255,255,0.12);margin-top:16px;"></div>
    </div>""", unsafe_allow_html=True)

    # System pulse
    status = ollama_status()
    if status.get("ok"):
        st.markdown(
            f'<div style="background:rgba(5,150,105,0.2);border:1px solid rgba(5,150,105,0.4);border-radius:8px;padding:10px 14px;margin-bottom:12px;">'
            f'<div style="font-size:11px;font-weight:600;color:#34d399;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">● Système en ligne</div>'
            f'<div style="font-size:11px;color:rgba(255,255,255,0.5);">{status["base_url"]}</div>'
            f'<div style="font-size:11px;color:rgba(255,255,255,0.4);margin-top:4px;">LLM: {settings.llm_model}</div>'
            f'<div style="font-size:11px;color:rgba(255,255,255,0.4);">Embed: {settings.embed_model}</div>'
            f'</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="background:rgba(220,38,38,0.2);border:1px solid rgba(220,38,38,0.4);border-radius:8px;padding:10px 14px;margin-bottom:12px;">'
            '<div style="font-size:11px;font-weight:600;color:#f87171;text-transform:uppercase;">✕ Ollama hors ligne</div>'
            '<div style="font-size:12px;color:rgba(255,255,255,0.5);">Démarrer Ollama d\'abord.</div></div>',
            unsafe_allow_html=True)

    # Navigation icons
    st.markdown("""
    <div style="margin:12px 0 8px;">
      <div style="font-size:10px;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:0.07em;margin-bottom:8px;">Navigation</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.7);padding:4px 0;">✍️ Analyse manuelle</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.7);padding:4px 0;">📡 Flux RSS</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.7);padding:4px 0;">🌐 Découverte multi-sources</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.7);padding:4px 0;">🐄 One Health</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.7);padding:4px 0;">📊 Analytics</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.7);padding:4px 0;">🔗 URL / 📥 CSV</div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div style="height:1px;background:rgba(255,255,255,0.1);margin:12px 0;"></div>', unsafe_allow_html=True)

    st.markdown('<div style="font-size:11px;color:rgba(255,255,255,0.5);text-transform:uppercase;letter-spacing:0.07em;margin:8px 0 6px;">Langue de sortie</div>', unsafe_allow_html=True)
    output_language = st.selectbox("Langue", ["fr", "en", "ar"], index=0, label_visibility="collapsed")

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    if st.button("⟳  Index Whitelist"):
        with st.spinner("Reconstruction…"):
            manifest = build_whitelist_index(force_rebuild=True).get("manifest", {})
        st.success(f"Whitelist prête · {manifest.get('chunk_count',0)} chunks")

    if st.button("⟳  Index Discovery"):
        with st.spinner("Reconstruction…"):
            manifest = build_discovery_index(force_rebuild=True).get("manifest", {})
        st.success(f"Discovery prêt · {manifest.get('chunk_count',0)} chunks")

    st.markdown(
        '<div style="height:1px;background:rgba(255,255,255,0.1);margin:20px 0 14px;"></div>'
        '<div style="font-size:10px;color:rgba(255,255,255,0.25);text-align:center;line-height:1.7;">'
        'LangGraph · Ollama · Whitelist RAG<br>Discovery RAG · HITL · Inoculation<br>'
        'ProMED · Reddit · DuckDuckGo · Bluesky<br>Arabic NLP · One Health · WAHIS</div>',
        unsafe_allow_html=True)


# ── Main tabs ────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab_oh, tab_analytics, tab4, tab5 = st.tabs([
    "✍️  Analyse manuelle",
    "📡  Flux RSS",
    "🌐  Découverte multi-sources",
    "🐄  One Health",
    "📊  Analytics",
    "🔗  Coller une URL",
    "📥  Import CSV",
])


# ── Tab 1 · Manual claim ────────────────────────────────────────────────────────
with tab1:
    st.markdown(
        '<div style="font-size:14px;color:#475569;margin-bottom:12px;">'
        'Collez une rumeur, affirmation sanitaire ou signal d\'alerte. '
        'Supporte : <strong>Français</strong>, <strong>English</strong>, <strong>العربية</strong>, '
        '<strong>تونسي</strong> (dialecte tunisien), <strong>Arabizi</strong> (ex: le9a7 mta3 covid 5atar).'
        '</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns([2, 1])
    with col_a:
        label_text("Texte de la claim ou de l'événement")
        claim = st.text_area("Texte", value="The MMR vaccine causes autism, so parents should avoid it.", height=160, label_visibility="collapsed")
    with col_b:
        label_text("Titre (optionnel)")
        title = st.text_input("Titre", label_visibility="collapsed", placeholder="ex: Rumeur vaccin")
        label_text("Source")
        source = st.text_input("Source", value="manual_demo", label_visibility="collapsed")
        label_text("URL (optionnel)")
        url = st.text_input("URL", label_visibility="collapsed", placeholder="https://…")

    # Live language detection preview
    if claim.strip():
        show_language_badge(claim)

        # Arabizi normalization preview
        lang_info = detect_language(claim)
        if lang_info.arabizi_detected:
            normalized = normalize_arabizi(claim)
            st.markdown(
                f'<div style="background:#faf5ff;border:1px solid #e9d5ff;border-radius:8px;padding:12px 16px;margin-bottom:12px;">'
                f'<div style="font-size:11px;color:#7e22ce;font-weight:600;text-transform:uppercase;margin-bottom:6px;">Normalisation Arabizi → Arabe</div>'
                f'<div style="font-size:14px;color:#581c87;direction:rtl;text-align:right;">{normalized}</div>'
                f'</div>', unsafe_allow_html=True)

    st.markdown('<div style="margin-top:16px;"></div>', unsafe_allow_html=True)
    if st.button("▶  Lancer l'analyse agentique"):
        item = InputItem(title=title, text=claim, source=source, url=url, source_type="manual")
        result = run_pipeline_with_status(item, output_language=output_language)
        show_result(result)


# ── Tab 2 · RSS Feeds ───────────────────────────────────────────────────────────
with tab2:
    st.markdown(
        '<div style="font-size:14px;color:#475569;margin-bottom:20px;">'
        'Récupère un lot de flux RSS/actualités sanitaires récents pour analyse.</div>', unsafe_allow_html=True)
    if st.button("⬇  Récupérer les derniers flux"):
        with st.spinner("Collecte RSS…"):
            st.session_state["feed_items"] = fetch_feed_items()
    feed_items = st.session_state.get("feed_items", load_demo_claims())
    feed_table = pd.DataFrame(items_to_table(feed_items))
    st.markdown(f'<div style="font-family:JetBrains Mono,monospace;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.07em;margin-bottom:8px;">{len(feed_items)} items</div>', unsafe_allow_html=True)
    st.dataframe(feed_table, use_container_width=True)
    if feed_items:
        col_idx, col_btn = st.columns([1, 2])
        with col_idx:
            label_text("Index de ligne")
            idx = st.number_input("idx", min_value=0, max_value=len(feed_items)-1, value=0, step=1, label_visibility="collapsed")
        item = feed_items[int(idx)]
        show_item_card(item)
        with col_btn:
            st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
            if st.button("▶  Analyser l'item sélectionné"):
                result = run_pipeline_with_status(item, output_language=output_language)
                show_result(result)


# ── Tab 3 · Web + social discovery (expanded) ──────────────────────────────────
with tab3:
    st.markdown(
        '<div style="font-size:14px;color:#475569;margin-bottom:4px;">'
        'Crawl de découverte multi-sources : Google News, Bluesky, Reddit, DuckDuckGo News, ProMED (alertes épidémiologiques), '
        'et Telegram public. Les items alimentent le Discovery RAG.'
        '</div>', unsafe_allow_html=True)

    # Architecture callout
    st.markdown("""
    <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;
                padding:14px 18px;margin:14px 0 20px;display:flex;align-items:flex-start;gap:12px;">
      <div style="font-size:20px;flex-shrink:0;">🏗️</div>
      <div style="font-size:13px;color:#1e3a5f;line-height:1.65;">
        <strong>Architecture à double couche RAG + 6 sources :</strong>
        Couche 1 (Whitelist RAG) = ancrage factuel sur sources officielles validées.
        Couche 2 (Discovery RAG) = contexte de propagation et tendances depuis le web ouvert et réseaux sociaux.
        Sources : 📰 Google News · 🦋 Bluesky · 🤖 Reddit · 🦆 DuckDuckGo · 🔬 ProMED · 📨 Telegram.
      </div>
    </div>
    """, unsafe_allow_html=True)

    label_text("Requête de découverte")
    query = st.text_input("Requête", value="measles vaccine Tunisia", label_visibility="collapsed")

    # Source toggles
    c1, c2, c3 = st.columns(3)
    with c1:
        include_news = st.checkbox("📰  Google News RSS", value=True)
        include_reddit = st.checkbox("🤖  Reddit public", value=True)
    with c2:
        include_bluesky = st.checkbox("🦋  Bluesky", value=True)
        include_ddg = st.checkbox("🦆  DuckDuckGo News", value=True)
    with c3:
        include_promed = st.checkbox("🔬  ProMED (alertes épidém.)", value=True)
        include_telegram = st.checkbox("📨  Telegram public", value=False)

    label_text("Max items / source")
    max_items_per_source = st.slider("max", min_value=2, max_value=20, value=6, step=1, label_visibility="collapsed")

    st.markdown('<div style="margin-top:12px;"></div>', unsafe_allow_html=True)
    if st.button("🔍  Lancer le crawl de découverte"):
        with st.spinner("Crawl multi-sources en cours…"):
            discovered = collect_discovery_items(
                query=query, include_news=include_news, include_bluesky=include_bluesky,
                include_reddit=include_reddit, include_ddg=include_ddg,
                include_promed=include_promed, include_telegram=include_telegram,
                max_items_per_source=max_items_per_source,
            )
            st.session_state["discovery_items"] = discovered
            summary = append_discovery_items(discovered)
            manifest = build_discovery_index(force_rebuild=True).get("manifest", {})

        added = summary.get("added", 0)
        total = summary.get("total", 0)
        chunks = manifest.get("chunk_count", 0)

        # Source breakdown
        src_counts = get_source_counts(discovered)
        src_pills = " ".join(
            f'<span style="padding:4px 12px;background:#f1f5f9;border:1px solid #e2e8f0;'
            f'border-radius:20px;font-size:11px;font-weight:600;color:#475569;">'
            f'{SOURCE_TYPE_ICON.get(t,"📄")} {t}: {c}</span>'
            for t, c in src_counts.items())

        st.markdown(
            f'<div style="display:flex;gap:10px;margin:12px 0;flex-wrap:wrap;">'
            f'<div style="padding:8px 16px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;font-size:13px;font-weight:600;color:#15803d;">✓ {len(discovered)} items collectés</div>'
            f'<div style="padding:8px 16px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;font-size:13px;font-weight:600;color:#1d4ed8;">+{added} nouveaux · {total} total</div>'
            f'<div style="padding:8px 16px;background:#fdf4ff;border:1px solid #e9d5ff;border-radius:8px;font-size:13px;font-weight:600;color:#7e22ce;">Discovery RAG · {chunks} chunks</div>'
            f'</div>'
            f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin:6px 0 10px;">{src_pills}</div>',
            unsafe_allow_html=True)

    discovery_items = st.session_state.get("discovery_items", [])
    if not discovery_items:
        discovery_items = load_discovery_items()[:20]

    if discovery_items:
        type_counts = get_source_counts(discovery_items)
        type_pills = " ".join(
            f'<span style="padding:2px 10px;background:#f1f5f9;border:1px solid #e2e8f0;'
            f'border-radius:20px;font-size:11px;font-weight:600;color:#475569;">'
            f'{SOURCE_TYPE_ICON.get(t,"📄")} {t}: {c}</span>'
            for t, c in type_counts.items())
        st.markdown(f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;">{type_pills}</div>', unsafe_allow_html=True)

        discovery_table = pd.DataFrame(items_to_table(discovery_items))
        st.dataframe(discovery_table, use_container_width=True)

        col_idx, col_btn = st.columns([1, 2])
        with col_idx:
            label_text("Index de ligne à analyser")
            idx = st.number_input("didx", min_value=0, max_value=len(discovery_items)-1, value=0, step=1, label_visibility="collapsed", key="discovery_idx")
        item = discovery_items[int(idx)]
        show_item_card(item)
        with col_btn:
            st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
            if st.button("▶  Analyser l'item découvert"):
                result = run_pipeline_with_status(item, output_language=output_language)
                show_result(result)
    else:
        st.markdown(
            '<div style="background:#f8fafc;border:1px dashed #cbd5e1;border-radius:10px;'
            'padding:24px;text-align:center;color:#94a3b8;font-size:14px;">'
            '💡 Aucun item découvert. Lancez un crawl ci-dessus pour commencer.</div>',
            unsafe_allow_html=True)


# ── Tab 4 · One Health ──────────────────────────────────────────────────────────
with tab_oh:
    st.markdown(
        '<div style="font-size:14px;color:#475569;margin-bottom:12px;">'
        'Surveillance <strong>One Health</strong> : croisement des signaux de santé animale (WAHIS/WOAH, ProMED) '
        'avec les alertes humaines. Détection de corrélations zoonotiques.'
        '</div>', unsafe_allow_html=True)

    st.markdown("""
    <div style="background:#ecfeff;border:1px solid #a5f3fc;border-radius:10px;
                padding:14px 18px;margin:8px 0 18px;display:flex;align-items:flex-start;gap:12px;">
      <div style="font-size:20px;flex-shrink:0;">🐄</div>
      <div style="font-size:13px;color:#155e75;line-height:1.65;">
        <strong>Approche One Health (§5 du cahier des charges) :</strong>
        60% des maladies infectieuses émergentes sont des zoonoses.
        Ce tableau croise les alertes animales avec les signaux humains pour détecter les menaces avant confirmation clinique.
      </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🔄  Actualiser les données One Health"):
        with st.spinner("Récupération ProMED + WAHIS…"):
            from src.one_health import build_one_health_dashboard
            dashboard = build_one_health_dashboard()
            st.session_state["one_health"] = dashboard

    dashboard = st.session_state.get("one_health")
    if dashboard:
        # Errors
        if dashboard.errors:
            for err in dashboard.errors:
                st.warning(f"⚠️ {err}")

        # Correlations banner
        if dashboard.correlations:
            for corr in dashboard.correlations:
                reasons = " · ".join(corr["correlation_reasons"])
                risk_color = "#dc2626" if corr["risk_level"] == "high" else "#d97706"
                st.markdown(
                    f'<div style="background:#fef2f2;border:2px solid {risk_color};border-radius:10px;'
                    f'padding:14px 18px;margin-bottom:12px;">'
                    f'<div style="font-size:14px;font-weight:700;color:{risk_color};">⚠️ Corrélation One Health détectée</div>'
                    f'<div style="font-size:13px;color:#7f1d1d;margin-top:6px;">'
                    f'<strong>{corr["disease"]}</strong> — {corr["country"]} ({corr["species"]})</div>'
                    f'<div style="font-size:12px;color:#991b1b;margin-top:4px;">{reasons}</div>'
                    f'</div>', unsafe_allow_html=True)

        st.markdown(f'<div style="font-size:11px;color:#94a3b8;margin-bottom:8px;">Dernière mise à jour : {dashboard.last_update}</div>', unsafe_allow_html=True)

        # ProMED alerts table
        section_header("Alertes ProMED", "🔬", "Alertes épidémiologiques mondiales — source WHO-adjacente")
        if dashboard.promed_alerts:
            promed_data = [{
                "Maladie": a.disease[:40], "Pays": a.country[:30], "Espèce": a.species,
                "Date": a.date, "Zoonotique": "✅" if a.is_zoonotic else "—",
                "Tunisie/Maghreb": "🇹🇳" if a.geo_match_tunisia else "—",
            } for a in dashboard.promed_alerts[:15]]
            st.dataframe(pd.DataFrame(promed_data), use_container_width=True)
        else:
            st.info("Aucune alerte ProMED récupérée. Le flux RSS peut être temporairement indisponible.")

        # WAHIS alerts table
        section_header("Données WAHIS/WOAH", "🐄", "Maladies animales officielles — Organisation Mondiale de la Santé Animale")
        if dashboard.wahis_alerts:
            wahis_data = [{
                "Maladie": a.disease[:40], "Pays": a.country[:30], "Espèce": a.species,
                "Date": a.date, "Zoonotique": "✅" if a.is_zoonotic else "—",
            } for a in dashboard.wahis_alerts[:10]]
            st.dataframe(pd.DataFrame(wahis_data), use_container_width=True)
        else:
            st.info("Données WAHIS non disponibles. L'API peut nécessiter une connexion réseau spécifique.")
    else:
        st.markdown(
            '<div style="background:#f8fafc;border:1px dashed #cbd5e1;border-radius:10px;'
            'padding:24px;text-align:center;color:#94a3b8;font-size:14px;">'
            '🐄 Cliquez sur "Actualiser" pour charger les données One Health.</div>',
            unsafe_allow_html=True)


# ── Tab 5 · Analytics ────────────────────────────────────────────────────────────
with tab_analytics:
    st.markdown(
        '<div style="font-size:14px;color:#475569;margin-bottom:20px;">'
        'Tableau de bord analytique de la session en cours.</div>', unsafe_allow_html=True)

    analyses = st.session_state.get("session_analyses", [])
    pipeline_times = st.session_state.get("pipeline_times", [])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Analyses cette session", len(analyses))
    m2.metric("Temps moyen pipeline", f"{sum(pipeline_times)/len(pipeline_times):.1f}s" if pipeline_times else "—")
    m3.metric("Rumeurs détectées", sum(1 for a in analyses if a.get("category") == "rumor_infodemie"))
    m4.metric("Alertes réelles", sum(1 for a in analyses if a.get("category") == "real_alert"))

    if analyses:
        section_header("Répartition par catégorie", "📊")
        cat_counts = {}
        for a in analyses:
            c = a.get("category", "unknown")
            cat_counts[c] = cat_counts.get(c, 0) + 1
        for cat, count in cat_counts.items():
            meta = CATEGORY_META.get(cat, ("#64748b", "#f8fafc", cat))
            bar_pct = int(count / len(analyses) * 100)
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
                f'<div style="width:140px;font-size:13px;font-weight:600;color:{meta[0]};">{meta[2]}</div>'
                f'<div style="flex:1;height:8px;background:#f1f5f9;border-radius:4px;overflow:hidden;">'
                f'<div style="width:{bar_pct}%;height:100%;background:{meta[0]};border-radius:4px;"></div></div>'
                f'<div style="font-size:12px;font-weight:600;color:#475569;width:30px;text-align:right;">{count}</div>'
                f'</div>', unsafe_allow_html=True)

        section_header("Historique des temps pipeline", "⏱️")
        if pipeline_times:
            for i, t in enumerate(pipeline_times):
                bar_w = min(int(t / max(pipeline_times) * 100), 100) if max(pipeline_times) > 0 else 0
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">'
                    f'<div style="font-family:JetBrains Mono,monospace;font-size:11px;color:#94a3b8;width:50px;">Run {i+1}</div>'
                    f'<div style="flex:1;height:6px;background:#f1f5f9;border-radius:3px;overflow:hidden;">'
                    f'<div style="width:{bar_w}%;height:100%;background:#1a6cf6;border-radius:3px;"></div></div>'
                    f'<div style="font-family:JetBrains Mono,monospace;font-size:11px;color:#475569;width:40px;text-align:right;">{t:.1f}s</div>'
                    f'</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="background:#f8fafc;border:1px dashed #cbd5e1;border-radius:10px;'
            'padding:24px;text-align:center;color:#94a3b8;font-size:14px;">'
            '📊 Les analytics s\'alimentent au fur et à mesure de vos analyses. Lancez une première analyse pour commencer.</div>',
            unsafe_allow_html=True)


# ── Tab 6 · Paste URL ───────────────────────────────────────────────────────────
with tab4:
    st.markdown(
        '<div style="font-size:14px;color:#475569;margin-bottom:20px;">'
        'Colle une URL publique — le système scrape le contenu et l\'analyse directement.'
        '</div>', unsafe_allow_html=True)
    label_text("URL publique à scraper")
    url_to_crawl = st.text_input("URL", value="", label_visibility="collapsed", placeholder="https://www.who.int/…")
    label_text("Libellé (optionnel)")
    url_title = st.text_input("Libellé", value="", label_visibility="collapsed", placeholder="ex: Article WHO sur rougeole")
    st.markdown('<div style="margin-top:12px;"></div>', unsafe_allow_html=True)
    if st.button("🔗  Scraper et analyser"):
        with st.spinner("Scraping de la page…"):
            item = item_from_url(url_to_crawl, title=url_title or "URL collée", source="url_paste")
        show_item_card(item)
        result = run_pipeline_with_status(item, output_language=output_language)
        show_result(result)


# ── Tab 7 · Upload CSV ──────────────────────────────────────────────────────────
with tab5:
    st.markdown(
        '<div style="font-size:14px;color:#475569;margin-bottom:12px;">'
        'Importez un CSV avec les colonnes : <code style="background:#f1f5f9;padding:2px 6px;'
        'border-radius:4px;font-size:13px;color:#0891b2;">title, text, url, source, published</code>'
        '</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Fichier CSV", type=["csv"], label_visibility="collapsed")
    if uploaded is not None:
        csv_text = uploaded.getvalue().decode("utf-8", errors="ignore")
        csv_items = read_csv_items_from_text(csv_text)
        if not csv_items:
            st.markdown(
                '<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;'
                'padding:14px;color:#92400e;font-size:13px;">Aucune ligne valide trouvée.</div>',
                unsafe_allow_html=True)
        else:
            csv_table = pd.DataFrame(items_to_table(csv_items))
            st.markdown(f'<div style="font-family:JetBrains Mono,monospace;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.07em;margin-bottom:8px;">{len(csv_items)} lignes importées</div>', unsafe_allow_html=True)
            st.dataframe(csv_table, use_container_width=True)
            col_idx, col_btn = st.columns([1, 2])
            with col_idx:
                label_text("Index de ligne")
                idx = st.number_input("cidx", min_value=0, max_value=len(csv_items)-1, value=0, step=1, label_visibility="collapsed", key="csv_idx")
            item = csv_items[int(idx)]
            show_item_card(item)
            with col_btn:
                st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
                if st.button("▶  Analyser la ligne CSV"):
                    result = run_pipeline_with_status(csv_items[int(idx)], output_language=output_language)
                    show_result(result)
