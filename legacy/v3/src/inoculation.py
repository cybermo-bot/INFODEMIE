"""
Moteur d'Inoculation Cognitive — OMS Tunisie Infodémie
Implémentation du §6.2 du cahier des charges.

Génère des contre-messages structurés en 4 étapes :
1. Label d'avertissement
2. Technique de manipulation identifiée
3. Correction factuelle (ancrée whitelist)
4. Appel à l'action (sources officielles)

Formats de sortie : Twitter/X, Facebook, SMS/WhatsApp, Communiqué officiel.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .arabic_nlp import MANIPULATION_TECHNIQUES, detect_manipulation_techniques, get_technique_display


@dataclass
class InoculationMessage:
    """A complete inoculation counter-message with all format variants."""
    warning_label: str
    technique_id: str
    technique_label: str
    technique_emoji: str
    technique_description: str
    factual_correction: str
    call_to_action: str
    sources_text: str
    twitter: str
    facebook: str
    sms: str
    communique: str
    language: str
    claim_summary: str
    verdict: str


WARNING_LABELS = {
    "contradicted": {
        "fr": "⛔ Information trompeuse confirmée",
        "ar": "⛔ معلومة مُضللة مؤكدة",
        "en": "⛔ Confirmed misleading information",
    },
    "uncertain": {
        "fr": "⚠️ Information non vérifiée — À vérifier",
        "ar": "⚠️ معلومة غير موثوقة - تحقق منها",
        "en": "⚠️ Unverified information — Needs checking",
    },
    "supported": {
        "fr": "✅ Information corroborée par les sources officielles",
        "ar": "✅ معلومة مؤيدة من المصادر الرسمية",
        "en": "✅ Information supported by official sources",
    },
}

OFFICIAL_CHANNELS = {
    "fr": "who.int · santetunisie.rns.tn · insp.nat.tn",
    "ar": "who.int · santetunisie.rns.tn · insp.nat.tn",
    "en": "who.int · cdc.gov · santetunisie.rns.tn",
}

CTA_TEMPLATES = {
    "fr": "Pour des informations fiables, consultez les sources officielles : {sources}",
    "ar": "للمعلومات الصحية الموثوقة، راجعوا المصادر الرسمية : {sources}",
    "en": "For reliable information, consult official sources: {sources}",
}


def generate_inoculation_message(
    claim: str,
    verdict: str,
    analysis: str,
    evidence: list[dict[str, Any]],
    draft_text: str = "",
    language: str = "fr",
) -> InoculationMessage:
    """
    Generate a complete inoculation counter-message with all format variants.

    Args:
        claim: The original claim text
        verdict: "contradicted", "uncertain", or "supported"
        analysis: The investigation analysis text
        evidence: List of evidence dicts from the pipeline
        draft_text: Optional existing draft from the pipeline
        language: Output language code
    """
    lang = language if language in ("fr", "ar", "en") else "fr"

    # Step 1 — Warning label
    warning = WARNING_LABELS.get(verdict, WARNING_LABELS["uncertain"]).get(lang, "⚠️")

    # Step 2 — Detect manipulation technique
    manip = detect_manipulation_techniques(claim)
    tech_id = manip.primary_technique or "fear_appeal"
    tech_display = get_technique_display(tech_id, lang)
    tech_emoji = tech_display["emoji"]
    tech_label = tech_display["label"]
    tech_desc = tech_display["description"]

    # Step 3 — Factual correction from evidence
    source_titles: list[str] = []
    for ev in evidence[:4]:
        title = ev.get("source_title", "")
        url = ev.get("source_url", "")
        if title:
            source_titles.append(f"{title}")
    sources_text = " | ".join(source_titles[:3]) if source_titles else "OMS/WHO, Ministère de la Santé TN"
    sources_detailed = "\n".join(f"• {s}" for s in source_titles[:5]) if source_titles else "• OMS/WHO\n• Ministère de la Santé Tunisie"

    correction = _build_correction(analysis, draft_text, evidence, lang)

    # Step 4 — Call to action
    official = OFFICIAL_CHANNELS.get(lang, OFFICIAL_CHANNELS["fr"])
    cta = CTA_TEMPLATES.get(lang, CTA_TEMPLATES["fr"]).format(sources=official)

    # ── Build format variants ──────────────────────────────────────────────────
    claim_short = (claim[:80] + "…") if len(claim) > 80 else claim
    date_str = datetime.now().strftime("%d/%m/%Y")

    # Twitter/X (280 chars)
    twitter = _build_twitter(warning, tech_emoji, tech_label, correction, sources_text, official, lang)

    # Facebook
    facebook = _build_facebook(warning, tech_emoji, tech_label, tech_desc, correction, sources_detailed, official, lang)

    # SMS/WhatsApp (160 chars)
    sms = _build_sms(warning, correction, sources_text, lang)

    # Communiqué officiel
    communique = _build_communique(warning, claim_short, verdict, tech_label, tech_desc, correction, sources_detailed, date_str, lang)

    return InoculationMessage(
        warning_label=warning,
        technique_id=tech_id,
        technique_label=tech_label,
        technique_emoji=tech_emoji,
        technique_description=tech_desc,
        factual_correction=correction,
        call_to_action=cta,
        sources_text=sources_text,
        twitter=twitter,
        facebook=facebook,
        sms=sms,
        communique=communique,
        language=lang,
        claim_summary=claim_short,
        verdict=verdict,
    )


def _build_correction(analysis: str, draft_text: str, evidence: list[dict], lang: str) -> str:
    """Extract / build a short factual correction from available data."""
    # Use draft text if available and not a fallback
    if draft_text and "fallback" not in draft_text.lower() and len(draft_text) > 30:
        # Take the core message, strip boilerplate
        lines = [l.strip() for l in draft_text.split("\n") if l.strip()]
        core = " ".join(lines[:4])
        if len(core) > 400:
            core = core[:397] + "…"
        return core

    # Otherwise use analysis
    if analysis and len(analysis) > 20:
        if len(analysis) > 400:
            return analysis[:397] + "…"
        return analysis

    # Last resort
    return {
        "fr": "Consultez les sources officielles de santé pour une information vérifiée.",
        "ar": "راجعوا المصادر الصحية الرسمية للحصول على معلومات موثوقة.",
        "en": "Consult official health sources for verified information.",
    }.get(lang, "Consultez les sources officielles de santé.")


def _build_twitter(warning: str, emoji: str, technique: str, correction: str, sources: str, official: str, lang: str) -> str:
    """Build Twitter/X message (max 280 chars)."""
    if lang == "ar":
        msg = f"{warning}\n{emoji} تقنية: {technique}\n✅ {correction}\n📎 {sources}"
    elif lang == "en":
        msg = f"{warning}\n{emoji} Technique: {technique}\n✅ {correction}\n📎 {sources}"
    else:
        msg = f"{warning}\n{emoji} Technique: {technique}\n✅ {correction}\n📎 {sources}"
    if len(msg) > 280:
        msg = msg[:277] + "…"
    return msg


def _build_facebook(warning: str, emoji: str, technique: str, tech_desc: str, correction: str, sources_detailed: str, official: str, lang: str) -> str:
    """Build Facebook post."""
    if lang == "ar":
        return (
            f"🚨 تنبيه صحي مهم 🚨\n\n"
            f"{warning}\n\n"
            f"🔍 كيف يتم التضليل:\n{emoji} {technique}\n{tech_desc}\n\n"
            f"✅ ما تقوله المصادر العلمية:\n{correction}\n\n"
            f"📚 المصادر:\n{sources_detailed}\n\n"
            f"👉 للمعلومات الموثوقة: {official}\n\n"
            f"#صحة_موثوقة #HealthWatch_تونس"
        )
    elif lang == "en":
        return (
            f"🚨 Important Health Alert 🚨\n\n"
            f"{warning}\n\n"
            f"🔍 How this misleads:\n{emoji} {technique}\n{tech_desc}\n\n"
            f"✅ What verified sources say:\n{correction}\n\n"
            f"📚 Sources:\n{sources_detailed}\n\n"
            f"👉 For reliable health info: {official}\n\n"
            f"#VerifiedHealth #HealthWatch_Tunisia"
        )
    else:
        return (
            f"🚨 Alerte Santé Importante 🚨\n\n"
            f"{warning}\n\n"
            f"🔍 Comment ce contenu vous manipule :\n{emoji} {technique}\n{tech_desc}\n\n"
            f"✅ Ce que disent les sources scientifiques :\n{correction}\n\n"
            f"📚 Sources vérifiées :\n{sources_detailed}\n\n"
            f"👉 Pour des informations fiables : {official}\n\n"
            f"#SantéVérifiée #HealthWatch_Tunisie"
        )


def _build_sms(warning: str, correction: str, sources: str, lang: str) -> str:
    """Build SMS/WhatsApp message (max 160 chars)."""
    if lang == "ar":
        msg = f"{warning} الحقيقة: {correction} مصدر: {sources}"
    elif lang == "en":
        msg = f"{warning} Fact: {correction} Source: {sources}"
    else:
        msg = f"{warning} Réalité: {correction} Source: {sources}"
    if len(msg) > 160:
        msg = msg[:157] + "…"
    return msg


def _build_communique(warning: str, claim: str, verdict: str, technique: str, tech_desc: str, correction: str, sources_detailed: str, date_str: str, lang: str) -> str:
    """Build official communiqué."""
    verdict_label = {
        "contradicted": {"fr": "CONTREDITE", "ar": "مُكذَّبة", "en": "CONTRADICTED"},
        "uncertain": {"fr": "NON VÉRIFIÉE", "ar": "غير مؤكدة", "en": "UNVERIFIED"},
        "supported": {"fr": "CORROBORÉE", "ar": "مؤيدة", "en": "SUPPORTED"},
    }.get(verdict, {}).get(lang, verdict.upper())

    if lang == "ar":
        return (
            f"بيان رسمي — منصة الرصد الصحي OMS تونس\n"
            f"التاريخ: {date_str}\n\n"
            f"الموضوع: الرد على المعلومة المتداولة حول «{claim}»\n\n"
            f"التصنيف: {verdict_label}\n{warning}\n\n"
            f"تقنية التضليل المستخدمة:\n{technique}\n{tech_desc}\n\n"
            f"نتيجة التحقق:\n{correction}\n\n"
            f"المصادر العلمية المعتمدة:\n{sources_detailed}\n\n"
            f"للاستفسارات: platform@healthwatch.tn"
        )
    elif lang == "en":
        return (
            f"Official Statement — WHO Tunisia Health Surveillance Platform\n"
            f"Date: {date_str}\n\n"
            f"Subject: Response to circulating claim: «{claim}»\n\n"
            f"Classification: {verdict_label}\n{warning}\n\n"
            f"Manipulation technique identified:\n{technique}\n{tech_desc}\n\n"
            f"Verification result:\n{correction}\n\n"
            f"Verified sources:\n{sources_detailed}\n\n"
            f"Contact: platform@healthwatch.tn"
        )
    else:
        return (
            f"Communiqué officiel — Plateforme de Veille Sanitaire OMS Tunisie\n"
            f"Date : {date_str}\n\n"
            f"Objet : Réponse à l'information circulant sur «{claim}»\n\n"
            f"Classification : {verdict_label}\n{warning}\n\n"
            f"Technique de manipulation identifiée :\n{technique}\n{tech_desc}\n\n"
            f"Résultat de la vérification :\n{correction}\n\n"
            f"Sources scientifiques :\n{sources_detailed}\n\n"
            f"Contact : platform@healthwatch.tn"
        )
