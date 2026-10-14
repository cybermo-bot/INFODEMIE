"""Health relevance filter applied before storing items from general sources.

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
