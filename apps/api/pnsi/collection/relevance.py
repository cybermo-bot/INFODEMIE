"""Health relevance filter and commercial-post cues, applied before storing items.

A keyword filter, not a classifier: the triage model comes in Stage 4. The
terms start from `docs/sources-plan.md` section 3 plus general health words.
The list is a draft that a native Derja speaker must review; its version is
recorded in each run's coverage so a change of terms is never read as a surge.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

HEALTH_TERMS_VERSION = "health-terms-draft-2026-10-13"

# Matched as word prefixes on normalised text ("vaccin" matches "vaccination").
LATIN_TERMS: tuple[str, ...] = (
    # French
    "santé", "sante", "médecin", "medecin", "médic", "medic", "hôpita", "hopita", "clinique",
    "maladie", "malade", "épidém", "epidem", "pandém", "pandem", "vaccin", "rougeole", "ror",
    "grippe", "covid", "corona", "virus", "fièvre", "fievre", "éruption", "eruption",
    "pénurie", "penurie", "rupture de stock", "insuline", "pharmac", "ordonnance", "infection",
    "cancer", "diabète", "diabete", "symptôme", "symptome", "traitement", "remède", "remede",
    "guérit", "guerit", "intoxication", "canicule", "eau potable", "choléra", "cholera",
    "hépatite", "hepatite", "méningite", "meningite", "tuberculose", "rage", "dengue",
    "urgence", "samu", "cnam", "onmne", "pasteur", "dpm",
    # English
    "health", "vaccine", "measles", "outbreak", "hospital", "disease", "medicine",
    # Arabizi (Tunisian Derja in Latin letters)
    "tal9i7", "tal9ii7", "le9a7", "l9a7", "7asba", "s5ana", "skhana", "dwe", "dwa",
    "sbitar", "tbib", "doktor", "mrith", "mridh", "tib 3arbi", "farmasi", "pharmacie",
)  # fmt: skip

# Matched as substrings on normalised Arabic (clitics attach to words).
ARABIC_TERMS: tuple[str, ...] = (
    "صحه", "تلقيح", "لقاح", "تطعيم", "حصبه", "دواء", "ادويه", "الدوا", "انسولين", "طب عربي",
    "اعشاب", "دواء طبيعي", "وباء", "جائحه", "انفلونزا", "نزله برد", "سخانه", "الحمي ",
    "موجه حر", "الماء الصالح للشرب", "مستشفي", "سبيطار", "طبيب", "اطباء", "مريض", "مرض",
    "امراض", "صيدليه", "صيدلي", "فيروس", "كورونا", "كوفيد", "عدوي", "تسمم", "سرطان", "سكري",
    "اعراض", "علاج", "استعجالي", "كوليرا", "التهاب الكبد", "مرض السل", "داء الكلب",
    # Substrings that are also parts of ordinary words are left out on purpose:
    # السل (السلام), حبوب (محبوب), نزله (منزله), حمي (يحمي).
)  # fmt: skip

_AR_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_AR_FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه"})


def normalize_for_match(text: str) -> str:
    """Search-only form: lowercase, Arabic folding, Latin accents kept and stripped.

    Never stored in place of the original (derja-handling skill).
    """
    value = _AR_DIACRITICS.sub("", text).translate(_AR_FOLD).lower()
    return " ".join(value.split())


def _strip_accents(value: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", value) if unicodedata.category(c) != "Mn"
    )


@lru_cache
def _latin_pattern() -> re.Pattern[str]:
    terms = sorted({_strip_accents(t.lower()) for t in LATIN_TERMS}, key=len, reverse=True)
    body = "|".join(r"\s+".join(re.escape(p) for p in t.split()) for t in terms)
    # Short codes such as "ror", "dpm", "dwe" must be whole words.
    return re.compile(rf"(?<![a-z0-9])(?:{body})", re.IGNORECASE)


_WHOLE_WORD = {"ror", "dpm", "rage", "samu", "cnam", "dwe", "dwa", "tbib"}


def health_terms_in(text: str | None) -> list[str]:
    """Health terms found in `text`, normalised. Empty list means not relevant."""
    if not text:
        return []
    norm = normalize_for_match(text)
    found: set[str] = set()
    latin = _strip_accents(norm)
    for m in _latin_pattern().finditer(latin):
        term = m.group(0)
        if term in _WHOLE_WORD:
            end = m.end()
            if end < len(latin) and (latin[end].isalnum()):
                continue
        found.add(" ".join(term.split()))
    for term in ARABIC_TERMS:
        if term in norm:
            found.add(term)
    return sorted(found)


# Commercial posts (decision D19). Ads are tagged, never dropped: in health
# groups they often sell unproven remedies, which is itself a signal (concept
# note 5.4.1, "remèdes non scientifiques"). Draft list, native review needed.
COMMERCIAL_TERMS_VERSION = "commercial-cues-draft-2026-10-22"

# Strong cues say "I am selling": one is required. Weak cues ("disponible",
# "سعر", a phone number) also appear in shortages, free campaigns and official
# hotlines, so they only add weight (audit of 2026-10-22).
LATIN_STRONG: tuple[str, ...] = (
    "livraison", "commande", "commandez", "inbox", "en privé", "en prive", "à vendre",
    "a vendre", "boutique", "paiement", "promo", "achat",
)  # fmt: skip
LATIN_WEAK: tuple[str, ...] = (
    "prix", "disponible", "dispo", "en stock", "dinars", "tnd", "remise", "soum", "9adech",
    "b9adech",
)  # fmt: skip
ARABIC_STRONG: tuple[str, ...] = (
    "للبيع", "اطلب", "التوصيل", "توصيل", "عرض خاص", "متجر", "طلبيه", "انبوكس", "الدفع",
)  # fmt: skip
ARABIC_WEAK: tuple[str, ...] = (
    "السعر", "سعر", "متوفر", "تخفيض", "ثمن", "دينار", "د.ت", "بقداش",
)  # fmt: skip

_COMMERCIAL_WHOLE_WORD = {"prix", "promo", "dispo", "tnd", "soum", "remise", "achat"}
_PHONE_CUE = re.compile(r"(?:\d[\s.-]?){7,11}\d")
# A price written as a number with a currency: "45 دينار", "30 dt", "12,500 TND".
_PRICE = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:dinars?|dt|tnd|د\.?\s?ت|دينار|مليم|millimes?)(?![a-z])",
    re.IGNORECASE,
)
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
STRONG_CUES = frozenset(LATIN_STRONG + ARABIC_STRONG + ("prix affiché",))


@lru_cache
def _latin_commercial_pattern() -> re.Pattern[str]:
    terms = {_strip_accents(t.lower()) for t in LATIN_STRONG + LATIN_WEAK}
    body = "|".join(
        r"\s+".join(re.escape(p) for p in t.split()) for t in sorted(terms, key=len, reverse=True)
    )
    return re.compile(rf"(?<![a-z0-9])(?:{body})", re.IGNORECASE)


def commercial_cues_in(text: str | None, *, organisation: bool = False) -> list[str]:
    """Selling cues found in `text` (raw, before redaction).

    "prix affiché" marks a price written with its currency (strong); "téléphone"
    marks a phone number (weak, and ignored for organisations, whose posts often
    give an official hotline).
    """
    if not text:
        return []
    norm = normalize_for_match(text)
    latin = _strip_accents(norm)
    found: set[str] = set()
    for m in _latin_commercial_pattern().finditer(latin):
        term = m.group(0)
        end = m.end()
        if term in _COMMERCIAL_WHOLE_WORD and end < len(latin) and latin[end].isalnum():
            continue
        found.add(" ".join(term.split()))
    for term in ARABIC_STRONG + ARABIC_WEAK:
        if term in norm:
            found.add(term)
    digits = text.translate(_DIGITS)
    if _PRICE.search(normalize_for_match(digits)):
        found.add("prix affiché")
    if not organisation and _PHONE_CUE.search(digits):
        found.add("téléphone")
    return sorted(found)


def is_commercial(cues: list[str]) -> bool:
    """At least one strong cue and two cues in all."""
    accented = {_strip_accents(c) for c in STRONG_CUES} | STRONG_CUES
    return len(cues) >= 2 and any(c in accented for c in cues)
