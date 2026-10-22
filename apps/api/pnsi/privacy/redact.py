"""Remove personal identifiers from collected text before it is stored or sent anywhere.

What is removed (CLAUDE.md rule 4): e-mail addresses, links to social profiles
and messaging accounts, @handles, phone numbers, and the names of individuals
the collector knows about (for example the authors of the comments in a
thread). Organisation names are kept: they are not passed as known names.

Known limits, stated so nobody relies on more than this does:
- A person's name that the collector did not see as an author (for example a
  relative named inside a comment) is not detected. A named-entity model can
  be added later behind the same function.
- Arabic names glued to a prefix (و, ب, ل) are not matched.
- Any run of 8 to 12 digits is treated as a phone number, even glued to a
  word, so some dates, amounts and product codes written without separators
  are masked too. Privacy wins.

The output only ever replaces spans; everything else of the original text is
kept unchanged (derja-handling skill, storage rule 1).
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field

REDACTION_VERSION = "r2-2026-10-22"

PLACEHOLDER = {
    "email": "[e-mail]",
    "profile_link": "[lien de profil]",
    "handle": "[pseudo]",
    "phone": "[téléphone]",
    "name": "[nom]",
}

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.UNICODE)

# Links to accounts of social networks and messaging apps. Organisation pages
# are kept through `canonical_url` and `author_org_name`, never through text.
_SOCIAL_DOMAINS = (
    r"facebook\.com|fb\.com|fb\.me|fb\.watch|m\.me|messenger\.com|instagram\.com|instagr\.am"
    r"|tiktok\.com|t\.me|telegram\.me|telegram\.dog|twitter\.com|x\.com|wa\.me|whatsapp\.com"
    r"|linkedin\.com|snapchat\.com|threads\.net|bsky\.app"
)
_PROFILE_LINK = re.compile(
    rf"(?:https?://)?(?:[\w-]+\.)*(?:{_SOCIAL_DOMAINS})(?:/[^\s<>\"')\]]*)?",
    re.IGNORECASE,
)

_HANDLE = re.compile(r"(?<![\w@.])@[A-Za-z0-9_](?:[A-Za-z0-9_.]{0,28}[A-Za-z0-9_])?")

# 8 to 12 digits, optionally grouped by spaces, dots or dashes inside a number,
# with an optional international prefix (+216, 00216).
# Only a digit or "+" may not touch the number: a number glued to a word
# ("مول98765432", "tel98765432") is still a phone. Arabic letters count as \w in
# Python, so a \w boundary let every number written right after Arabic through
# (seen in real group posts on 2026-10-22).
_PHONE = re.compile(r"(?<![\d+])(?:(?:\+|00)\d{1,3}[\s.-]?)?(?:\d[\s.-]?){7,11}\d(?!\d)")

# Eastern Arabic and Persian digits map one to one onto ASCII digits, so spans
# found on the translated copy line up with the original text.
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

_MIN_NAME_TOKEN = 3


@dataclass(frozen=True)
class Redacted:
    text: str
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.counts.values())


def _name_patterns(names: Iterable[str]) -> list[re.Pattern[str]]:
    """Full names first, then each name token, longest first."""
    full: set[str] = set()
    tokens: set[str] = set()
    for raw in names:
        name = " ".join(raw.split()) if raw else ""
        if not name:
            continue
        full.add(name)
        tokens.update(t for t in re.split(r"[\s\-'’.]+", name) if len(t) >= _MIN_NAME_TOKEN)
    patterns = []
    for value in sorted(full | tokens, key=len, reverse=True):
        body = r"\s+".join(re.escape(part) for part in value.split())
        patterns.append(re.compile(rf"(?<!\w){body}(?!\w)", re.IGNORECASE | re.UNICODE))
    return patterns


def redact(text: str | None, known_names: Iterable[str] = ()) -> Redacted:
    """Return `text` with personal identifiers replaced by placeholders."""
    if not text:
        return Redacted(text or "", {})
    counts: Counter[str] = Counter()

    def sub(pattern: re.Pattern[str], kind: str, value: str) -> str:
        def repl(_: re.Match[str]) -> str:
            counts[kind] += 1
            return PLACEHOLDER[kind]

        return pattern.sub(repl, value)

    out = sub(_EMAIL, "email", text)
    out = sub(_PROFILE_LINK, "profile_link", out)
    out = sub(_HANDLE, "handle", out)

    # Phones: match on a copy with ASCII digits, replace in the original.
    ascii_copy = out.translate(_DIGITS)
    pieces: list[str] = []
    last = 0
    for m in _PHONE.finditer(ascii_copy):
        pieces.append(out[last : m.start()])
        pieces.append(PLACEHOLDER["phone"])
        counts["phone"] += 1
        last = m.end()
    pieces.append(out[last:])
    out = "".join(pieces)

    for pattern in _name_patterns(known_names):
        out = sub(pattern, "name", out)

    return Redacted(out, dict(counts))
