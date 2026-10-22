"""Redaction of personal identifiers (CLAUDE.md rule 4). Inputs are synthetic."""

from __future__ import annotations

import pytest

from pnsi.privacy.redact import PLACEHOLDER, redact


@pytest.mark.parametrize(
    "text",
    [
        "Appelez-moi au 98 123 456",
        "رقمي 98123456",
        "Tel: +216 98 123 456",
        "00216.98.123.456",
        "رقمي ٩٨١٢٣٤٥٦",
    ],
)
def test_phone_numbers_are_removed(text):
    out = redact(text)
    assert PLACEHOLDER["phone"] in out.text
    assert "98" not in out.text.translate(str.maketrans("٩٨", "98"))


def test_email_handle_and_profile_link():
    text = (
        "Écrivez à exemple.personne@mail.example ou @exemple_user, "
        "voir https://www.facebook.com/profile.php?id=100012345678901 et instagram.com/exemple"
    )
    out = redact(text)
    for leaked in ("exemple.personne", "@exemple_user", "100012345678901", "instagram.com"):
        assert leaked not in out.text
    assert out.counts == {"email": 1, "handle": 1, "profile_link": 2}


def test_known_names_full_and_tokens():
    out = redact("Exemplia Testova a raison, merci Exemplia", ["Exemplia Testova"])
    assert "Exemplia" not in out.text and "Testova" not in out.text
    assert out.text.startswith(PLACEHOLDER["name"])


def test_arabic_name_is_removed():
    out = redact("شكرا سلمى على المعلومة", ["سلمى الاختبار"])
    assert "سلمى" not in out.text
    assert "المعلومة" in out.text


def test_original_text_is_otherwise_unchanged():
    text = "الماء والملح يداويو الكورونا ? ma3andich thi9a fel vaccin 😡"
    assert redact(text).text == text


def test_short_name_tokens_are_not_used_alone():
    # "Al" would destroy ordinary words; only tokens of 3+ letters are matched alone.
    out = redact("Al hamdoulillah, ça va mieux", ["Al Exempli"])
    assert out.text.startswith("Al hamdoulillah")


def test_dates_with_slashes_are_kept():
    assert redact("Campagne du 15/10/2026 au 30/10/2026").text.count("2026") == 2


@pytest.mark.parametrize(
    "text",
    [
        "متوفر لدى المحل مول98765432",
        "اتصل98765432للحجز",
        "tel98765432",
        "Commande au 98765432€ près",
    ],
)
def test_phone_glued_to_a_word_is_removed(text):
    out = redact(text)
    assert "98765432" not in out.text
    assert PLACEHOLDER["phone"] in out.text


def test_arabizi_digits_are_not_phones():
    out = redact("s7a w l9a7 mte3 l'3am hedha")
    assert out.text == "s7a w l9a7 mte3 l'3am hedha"
