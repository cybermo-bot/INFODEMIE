"""
Module NLP Arabe / Tunisien / Arabizi — OMS Tunisie Infodémie
Adapté du cahier des charges §7.1 et §4.2

Fonctionnalités :
- Détection de langue (MSA, Français, Anglais, Arabizi, Dialecte tunisien)
- Normalisation Arabizi → Arabe unicode
- Détection du dialecte tunisien par marqueurs lexicaux
- Détection de patterns rhétoriques de désinformation
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ── Arabizi → Arabic character mapping ──────────────────────────────────────────
ARABIZI_CHAR_MAP: dict[str, str] = {
    # Digraphes (doivent être traités en premier)
    "ch": "ش",
    "sh": "ش",
    "th": "ث",
    "dh": "ذ",
    "kh": "خ",
    "gh": "غ",
    # Chiffres phonétiques tunisiens
    "2": "ء",   # hamza
    "3": "ع",   # ain
    "4": "غ",   # ghain (variante)
    "5": "خ",   # kha
    "6": "ط",   # ta emphatique
    "7": "ح",   # ha
    "8": "خ",   # kha (variante)
    "9": "ق",   # qaf
    # Lettres simples
    "a": "ا",
    "b": "ب",
    "t": "ت",
    "j": "ج",
    "d": "د",
    "r": "ر",
    "z": "ز",
    "s": "س",
    "f": "ف",
    "q": "ق",
    "k": "ك",
    "l": "ل",
    "m": "م",
    "n": "ن",
    "h": "ه",
    "w": "و",
    "o": "و",
    "u": "و",
    "y": "ي",
    "i": "ي",
    "e": "ا",
    "p": "ب",
    "g": "ج",
    "v": "ف",
}

# Health-specific Arabizi word dictionary
ARABIZI_HEALTH_DICT: dict[str, str] = {
    "marad": "مرض",
    "mrid": "مريض",
    "mrida": "مريضة",
    "virus": "فيروس",
    "forsan": "فيروس",
    "doktor": "دكتور",
    "docteur": "دكتور",
    "tbib": "طبيب",
    "spitar": "مستشفى",
    "hopital": "مستشفى",
    "dwa": "دواء",
    "dwé": "دواء",
    "3laj": "علاج",
    "sa7a": "صحة",
    "se7a": "صحة",
    "s7a": "صحة",
    "hamma": "حمى",
    "7amma": "حمى",
    "le9a7": "لقاح",
    "la9a7": "لقاح",
    "vaccin": "لقاح",
    "ta3ki7": "تلقيح",
    "ta39i7": "تلقيح",
    "covid": "كوفيد",
    "corona": "كورونا",
    "korona": "كورونا",
    "rougeole": "حصبة",
    "7asba": "حصبة",
    "grippe": "أنفلونزا",
    "mawt": "موت",
    "5atar": "خطر",
    "khatar": "خطر",
    "ya5i": "يا خي",
    "bech": "باش",
    "besh": "باش",
    "mta3": "متاع",
    "3ibad": "عباد",
    "barcha": "برشا",
    "yasser": "ياسر",
    "kifech": "كيفاش",
    "ki": "كي",
    "weld": "ولد",
    "walid": "والد",
    "ommi": "أمي",
    "baba": "بابا",
    "sghar": "صغار",
    "kbir": "كبير",
    "3bed": "عبد",
    "tounes": "تونس",
    "tounsi": "تونسي",
}

# ── Tunisian dialect markers ───────────────────────────────────────────────────
TUNISIAN_MARKERS_LATIN = {
    "mta3", "besh", "bech", "ynajam", "brabi", "ahna", "nta", "heka", "haka",
    "famma", "barcha", "yasser", "kifech", "3lech", "win", "waqteh", "chkoun",
    "nafs", "el ", " fi ", " 3la ", "ya5i", "ey", "tawa", "emchi", "9rib",
    "7keya", "5ali", "tounes", "mrigel", "s7i7",
}
TUNISIAN_MARKERS_ARABIC = {
    "كيفاش", "ياسر", "برشة", "برشا", "باش", "متاع", "أهنا", "فما", "فمة",
    "إيه", "هكاكا", "هاكا", "تو", "توا", "وقتاش", "علاش", "وين", "شكون",
    "يا خي", "بالحق", "قداش", "خاطر",
}


@dataclass
class LanguageInfo:
    """Result of language detection."""
    language: str          # "ar", "fr", "en", "arabizi", "tn" (Tunisian)
    dialect: str           # "msa", "tunisian", "arabizi", "standard", ""
    confidence: float      # 0..1
    is_arabic_script: bool
    is_tunisian: bool
    arabizi_detected: bool
    display_label: str     # Human-readable label for the UI
    display_label_fr: str  # French label


def detect_language(text: str) -> LanguageInfo:
    """
    Detect language including Arabizi and Tunisian dialect.
    Priority: Arabizi check → Tunisian markers → Arabic script ratio → Latin heuristics.
    """
    if not text or not text.strip():
        return LanguageInfo("unknown", "", 0.0, False, False, False, "Unknown", "Inconnu")

    text_lower = text.lower().strip()

    # Count character types
    arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06FF" or "\uFE70" <= c <= "\uFEFF")
    latin_chars = sum(1 for c in text if c.isascii() and c.isalpha())
    total_chars = max(len(text.replace(" ", "")), 1)
    arabic_ratio = arabic_chars / total_chars
    latin_ratio = latin_chars / total_chars

    # Check Arabizi first (Latin script with Arabic phonetic digits)
    arabizi_digit_pattern = re.compile(r"[2-9]")
    arabizi_digits_in_words = re.findall(r"\b[a-zA-Z]*[2-9][a-zA-Z]*\b", text_lower)
    has_arabizi_digits = len(arabizi_digits_in_words) >= 1
    has_arabizi_words = any(w in text_lower.split() for w in ARABIZI_HEALTH_DICT)
    tunisian_latin = sum(1 for m in TUNISIAN_MARKERS_LATIN if m in text_lower)

    if latin_ratio > 0.4 and has_arabizi_digits and tunisian_latin >= 1:
        return LanguageInfo("arabizi", "tunisian", 0.92, False, True, True,
                            "🔤 Arabizi (Tunisian Latin)", "Arabizi (Tunisien en latin)")
    if latin_ratio > 0.4 and has_arabizi_digits:
        return LanguageInfo("arabizi", "arabizi", 0.85, False, False, True,
                            "🔤 Arabizi", "Arabizi")
    if latin_ratio > 0.5 and has_arabizi_words and tunisian_latin >= 2:
        return LanguageInfo("arabizi", "tunisian", 0.80, False, True, True,
                            "🔤 Arabizi (Tunisian)", "Arabizi (Tunisien)")

    # Check Arabic script
    if arabic_ratio > 0.3:
        tunisian_arabic = sum(1 for m in TUNISIAN_MARKERS_ARABIC if m in text)
        if tunisian_arabic >= 1:
            return LanguageInfo("ar", "tunisian", 0.90, True, True, False,
                                "🇹🇳 عربي تونسي (Dialecte tunisien)", "Arabe dialectal tunisien")
        return LanguageInfo("ar", "msa", 0.92, True, False, False,
                            "🌍 العربية الفصحى (MSA)", "Arabe Standard Moderne")

    # Latin script – French vs English
    french_markers = {"le ", "la ", "les ", " de ", " des ", " du ", " en ", " et ",
                      " est ", " une ", " un ", " pour ", " dans ", " sur ", " pas ",
                      " avec ", " qui ", " que ", " sont ", " cette ", " aux "}
    english_markers = {"the ", " is ", " are ", " was ", " and ", " for ", " has ",
                       " that ", " this ", " with ", " from ", " have ", "should",
                       " not ", " can ", " but ", " were "}

    fr_hits = sum(1 for m in french_markers if m in text_lower)
    en_hits = sum(1 for m in english_markers if m in text_lower)

    if fr_hits > en_hits:
        return LanguageInfo("fr", "standard", 0.88, False, False, False,
                            "🇫🇷 Français", "Français")
    if en_hits > 0:
        return LanguageInfo("en", "standard", 0.88, False, False, False,
                            "🇬🇧 English", "Anglais")

    # Ambiguous Latin – check for Arabizi cues
    if has_arabizi_words:
        return LanguageInfo("arabizi", "arabizi", 0.65, False, False, True,
                            "🔤 Arabizi (probable)", "Arabizi (probable)")

    return LanguageInfo("unknown", "", 0.4, False, False, False,
                        "❓ Indéterminé", "Indéterminé")


def normalize_arabizi(text: str) -> str:
    """
    Convert Arabizi text to Arabic script using word dictionary + character mapping.
    """
    words = text.split()
    converted: list[str] = []
    for word in words:
        low = word.lower().strip(".,!?;:()\"'")
        if low in ARABIZI_HEALTH_DICT:
            converted.append(ARABIZI_HEALTH_DICT[low])
        else:
            converted.append(_convert_arabizi_word(low))
    return " ".join(converted)


def _convert_arabizi_word(word: str) -> str:
    """Character-by-character Arabizi → Arabic conversion with digraph priority."""
    result = word.lower()
    # Process digraphs first (longest match)
    digraphs = ["ch", "sh", "th", "dh", "kh", "gh"]
    for dg in digraphs:
        if dg in ARABIZI_CHAR_MAP:
            result = result.replace(dg, ARABIZI_CHAR_MAP[dg])
    # Then single characters
    out = []
    for ch in result:
        if ch in ARABIZI_CHAR_MAP:
            out.append(ARABIZI_CHAR_MAP[ch])
        elif "\u0600" <= ch <= "\u06FF":
            out.append(ch)  # already Arabic
        elif ch.isdigit():
            out.append(ARABIZI_CHAR_MAP.get(ch, ch))
        else:
            out.append(ch)
    return "".join(out)


# ── Manipulation technique detection ──────────────────────────────────────────
MANIPULATION_TECHNIQUES = {
    "fear_appeal": {
        "emoji": "😱",
        "label_fr": "Appel à la peur",
        "label_ar": "استخدام الخوف والذعر",
        "description_fr": "Ce contenu utilise un langage alarmiste pour court-circuiter votre pensée critique.",
        "description_ar": "هذا المحتوى يستخدم لغة مخيفة لمنعك من التفكير النقدي",
        "patterns_fr": [
            r"danger(?:eux)?", r"mort(?:el)?", r"tu(?:e|ent)", r"catastrophe",
            r"urgent", r"panique", r"alerte", r"va mourir",
        ],
        "patterns_ar": [
            "سيقتلك", "خطير", "تحذير عاجل", "خطر مميت", "ذعر", "موت",
        ],
        "patterns_en": [
            r"deadly", r"will kill", r"dangerous", r"panic", r"urgent warning",
        ],
    },
    "false_authority": {
        "emoji": "🎓",
        "label_fr": "Fausse autorité",
        "label_ar": "ادعاء سلطة زائفة",
        "description_fr": "Ce contenu invoque une expertise non vérifiable ou détournée.",
        "description_ar": "يدّعي هذا المحتوى دعم علماء أو أطباء دون مصادر موثوقة",
        "patterns_fr": [
            r"les m[ée]decins cachent", r"un (?:docteur|professeur) a d[ée]couvert",
            r"la v[ée]rit[ée] que.*cachent", r"les scientifiques ont prouv[ée]",
        ],
        "patterns_ar": [
            "الأطباء يخفون", "العلماء كشفوا", "سر خفي", "دكتور اكتشف",
        ],
        "patterns_en": [
            r"doctors don'?t want you to know", r"secret cure", r"scientists discovered",
        ],
    },
    "false_urgency": {
        "emoji": "⏰",
        "label_fr": "Fausse urgence",
        "label_ar": "الإلحاح الكاذب",
        "description_fr": "Ce contenu crée un sentiment d'urgence artificielle pour empêcher l'analyse critique.",
        "description_ar": "يخلق هذا المحتوى إحساساً زائفاً بالإلحاح لمنع التفكير النقدي",
        "patterns_fr": [
            r"partage[zr]? avant (?:suppression|qu)", r"tr[èe]s important",
            r"ils ne veulent pas", r"diffuse[zr]? vite",
        ],
        "patterns_ar": [
            "انشر قبل الحذف", "مهم جداً", "لا يريدونك أن تعرف",
        ],
        "patterns_en": [
            r"share before.*delet", r"they don'?t want you to know", r"spread the word",
        ],
    },
    "miracle_cure": {
        "emoji": "✨",
        "label_fr": "Remède miracle",
        "label_ar": "العلاج المعجزة",
        "description_fr": "Il n'existe pas de remèdes miracles reconnus médicalement — vérifiez toujours auprès de professionnels de santé.",
        "description_ar": "لا توجد 'علاجات معجزة' معترف بها طبياً",
        "patterns_fr": [
            r"rem[èe]de miracle", r"gu[ée]rison (?:instantan|d[ée]finiti)",
            r"100\s*%\s*efficace", r"soigne tout",
        ],
        "patterns_ar": [
            "علاج معجزة", "شفاء فوري", "100% فعال", "يشفي كل شيء",
        ],
        "patterns_en": [
            r"miracle cure", r"instant healing", r"100%? effective", r"cures everything",
        ],
    },
    "conspiracy": {
        "emoji": "🕵️",
        "label_fr": "Théorie conspirationniste",
        "label_ar": "نظرية المؤامرة",
        "description_fr": "Ce contenu présente les institutions comme faisant partie d'un complot sans preuve vérifiable.",
        "description_ar": "يصور هذا المحتوى المؤسسات الصحية كجزء من مؤامرة دون دليل",
        "patterns_fr": [
            r"complot", r"big pharma", r"puce [ée]lectronique", r"contr[ôo]le mondial",
            r"5g.*virus", r"bill gates",
        ],
        "patterns_ar": [
            "مؤامرة", "شريحة", "5G", "بيل غيتس", "تحكم عالمي",
        ],
        "patterns_en": [
            r"conspiracy", r"big pharma", r"microchip", r"5g.*virus", r"bill gates",
            r"new world order", r"population control",
        ],
    },
}


@dataclass
class ManipulationResult:
    """Result of manipulation technique detection."""
    techniques_found: list[str] = field(default_factory=list)
    primary_technique: str = ""
    details: dict[str, list[str]] = field(default_factory=dict)
    manipulation_score: float = 0.0


def detect_manipulation_techniques(text: str) -> ManipulationResult:
    """Scan text for known rhetorical manipulation patterns."""
    text_lower = text.lower()
    found: dict[str, list[str]] = {}

    for tech_id, tech in MANIPULATION_TECHNIQUES.items():
        matches: list[str] = []
        for pattern_key in ("patterns_fr", "patterns_ar", "patterns_en"):
            for pattern in tech.get(pattern_key, []):
                try:
                    if re.search(pattern, text_lower):
                        matches.append(pattern)
                except re.error:
                    if pattern.lower() in text_lower:
                        matches.append(pattern)
        if matches:
            found[tech_id] = matches

    techniques = list(found.keys())
    primary = techniques[0] if techniques else ""
    score = min(len(techniques) * 0.25, 1.0)

    return ManipulationResult(
        techniques_found=techniques,
        primary_technique=primary,
        details=found,
        manipulation_score=score,
    )


def get_technique_display(technique_id: str, lang: str = "fr") -> dict[str, str]:
    """Get display info for a manipulation technique."""
    tech = MANIPULATION_TECHNIQUES.get(technique_id, {})
    label_key = f"label_{lang}" if f"label_{lang}" in tech else "label_fr"
    desc_key = f"description_{lang}" if f"description_{lang}" in tech else "description_fr"
    return {
        "emoji": tech.get("emoji", "🎭"),
        "label": tech.get(label_key, technique_id),
        "description": tech.get(desc_key, ""),
    }
