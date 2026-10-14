"""Health keyword filter. Sentences are synthetic examples, not collected posts."""

from __future__ import annotations

import pytest

from pnsi.collection.relevance import health_terms_in, normalize_for_match


@pytest.mark.parametrize(
    "text",
    [
        "Campagne de vaccination ROR dans les écoles",
        "التلقيح ضد الحصبة في المدارس",
        "el tal9i7 hedha mouch behi",
        "فقدان الأدوية في الصيدليات",
        "Pénurie d'insuline à Sfax",
        "مشيت للسبيطار البارح",
    ],
)
def test_health_texts_match(text):
    assert health_terms_in(text)


@pytest.mark.parametrize(
    "text",
    [
        "Match nul pour l'Espérance ce soir",
        "السلام عليكم يا جماعة",
        "حبيبي محبوب من الكل",
        "الدار متاعو منزله كبير",
        "Erreur de stockage du serveur",
        "",
    ],
)
def test_other_texts_do_not_match(text):
    assert health_terms_in(text) == []


def test_short_codes_are_whole_words():
    assert health_terms_in("le vaccin ROR") and not health_terms_in("le terroriste")


def test_normalisation_folds_arabic_forms():
    assert normalize_for_match("الأدوِيَة") == "الادويه"
