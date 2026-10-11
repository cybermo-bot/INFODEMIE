"""
Module One Health — OMS Tunisie Infodémie
Implémentation du §5 du cahier des charges.

Intègre les données de :
- ProMED RSS : alertes épidémiologiques mondiales (maladies émergentes)
- WAHIS/WOAH API : données officielles de maladies animales

Fournit une corrélation simplifiée entre signaux animaux et humains.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import feedparser
import requests
from bs4 import BeautifulSoup

from .utils import clean_text


PROMED_RSS_URL = "https://promedmail.org/promed-rss/"
WAHIS_API_BASE = "https://wahis.woah.org/api/v1"

# Keywords linking animal and human health concerns
ZOONOTIC_KEYWORDS = {
    "avian influenza", "bird flu", "h5n1", "h5n6", "h7n9",
    "mpox", "monkeypox", "rabies", "rage", "anthrax",
    "brucellosis", "brucellose", "rift valley", "mers",
    "ebola", "marburg", "leptospirosis", "leptospirose",
    "plague", "peste", "tularemia", "tularémie",
    "west nile", "crimean-congo", "nipah", "hendra",
    "q fever", "fièvre q", "leishmaniasis", "leishmaniose",
    "tuberculosis bovine", "tuberculose bovine",
    "salmonella", "salmonelle", "e. coli", "campylobacter",
    "zoonosis", "zoonose", "zoonotic", "zoonotique",
    "grippe aviaire", "influenza aviaire",
}

# Geographic keywords for Tunisia / North Africa correlation
TUNISIA_GEO_KEYWORDS = {
    "tunisia", "tunisie", "tunis", "sfax", "sousse", "bizerte",
    "kairouan", "kasserine", "gabes", "gafsa", "jendouba",
    "north africa", "afrique du nord", "maghreb", "libya", "libye",
    "algeria", "algérie",
}


@dataclass
class OneHealthAlert:
    """A single One Health alert from ProMED or WAHIS."""
    title: str
    source: str  # "promed" or "wahis"
    disease: str
    country: str
    species: str
    date: str
    url: str
    summary: str
    is_zoonotic: bool = False
    geo_match_tunisia: bool = False


@dataclass
class OneHealthDashboard:
    """Complete One Health dashboard data."""
    promed_alerts: list[OneHealthAlert] = field(default_factory=list)
    wahis_alerts: list[OneHealthAlert] = field(default_factory=list)
    correlations: list[dict[str, Any]] = field(default_factory=list)
    last_update: str = ""
    errors: list[str] = field(default_factory=list)


def fetch_promed_alerts(max_items: int = 15) -> tuple[list[OneHealthAlert], list[str]]:
    """Fetch recent alerts from ProMED RSS feed."""
    alerts: list[OneHealthAlert] = []
    errors: list[str] = []

    try:
        parsed = feedparser.parse(PROMED_RSS_URL)
        if not parsed.entries:
            # Try alternate URL patterns
            alt_urls = [
                "https://promedmail.org/feed/",
                "https://promedmail.org/promed-posts/feed/",
            ]
            for alt in alt_urls:
                parsed = feedparser.parse(alt)
                if parsed.entries:
                    break

        for entry in parsed.entries[:max_items]:
            title = clean_text(entry.get("title", ""))
            link = entry.get("link", "")
            summary_html = entry.get("summary", "") or entry.get("description", "")
            summary = clean_text(BeautifulSoup(summary_html, "html.parser").get_text(" ", strip=True))
            published = entry.get("published", "") or entry.get("updated", "")

            # Extract disease and country from title patterns like "DISEASE - COUNTRY"
            disease, country, species = _parse_promed_title(title)

            text_combined = f"{title} {summary}".lower()
            is_zoonotic = any(kw in text_combined for kw in ZOONOTIC_KEYWORDS)
            geo_match = any(kw in text_combined for kw in TUNISIA_GEO_KEYWORDS)

            alerts.append(OneHealthAlert(
                title=title,
                source="promed",
                disease=disease,
                country=country,
                species=species,
                date=published[:16] if published else "",
                url=link,
                summary=summary[:300] if summary else title,
                is_zoonotic=is_zoonotic,
                geo_match_tunisia=geo_match,
            ))

    except Exception as exc:
        errors.append(f"ProMED RSS: {exc}")

    return alerts, errors


def _parse_promed_title(title: str) -> tuple[str, str, str]:
    """Extract disease, country, and species from ProMED title."""
    # Typical formats:
    # "AVIAN INFLUENZA (11): AMERICAS (USA) WILD & DOMESTIC BIRDS, HPAI H5N1"
    # "MEASLES UPDATE (03): AFRICA"
    disease = ""
    country = ""
    species = ""

    # Try to extract disease (usually first part before parenthesis or dash)
    parts = re.split(r"\s*[-–—:]\s*", title, maxsplit=1)
    if parts:
        disease_raw = re.sub(r"\s*\(\d+\)\s*", "", parts[0]).strip()
        disease = disease_raw[:60]

    # Try to extract country from parentheses or after dash
    country_match = re.search(r"\(([^)]+)\)", title)
    if country_match:
        country = country_match.group(1).strip()[:40]
    elif len(parts) > 1:
        country = parts[1].strip()[:40]

    # Species detection
    species_keywords = {
        "bird": "Birds/Poultry", "poultry": "Birds/Poultry", "avian": "Birds/Poultry",
        "cattle": "Cattle", "bovine": "Cattle", "cow": "Cattle",
        "swine": "Swine/Pigs", "pig": "Swine/Pigs", "porcine": "Swine/Pigs",
        "dog": "Dogs", "canine": "Dogs", "cat": "Cats", "feline": "Cats",
        "sheep": "Sheep/Goats", "goat": "Sheep/Goats", "ovine": "Sheep/Goats",
        "horse": "Horses", "equine": "Horses",
        "wild": "Wildlife", "bat": "Bats", "rodent": "Rodents",
        "human": "Human", "primate": "Primates",
    }
    title_lower = title.lower()
    for kw, label in species_keywords.items():
        if kw in title_lower:
            species = label
            break
    if not species:
        species = "—"

    return disease, country, species


def fetch_wahis_alerts(max_items: int = 10) -> tuple[list[OneHealthAlert], list[str]]:
    """
    Fetch recent disease events from WAHIS/WOAH.
    Uses the public WAHIS API (no key needed for basic event listing).
    Falls back gracefully if the API is unavailable.
    """
    alerts: list[OneHealthAlert] = []
    errors: list[str] = []

    try:
        # Try public event listing endpoint
        url = f"{WAHIS_API_BASE}/pi/getEventList"
        headers = {
            "User-Agent": "OMS-Tunisia-Infodemie-Demo/0.2",
            "Accept": "application/json",
        }
        response = requests.get(url, headers=headers, timeout=20)

        if response.status_code == 200:
            data = response.json()
            events = data if isinstance(data, list) else data.get("events", data.get("results", []))
            for event in events[:max_items]:
                disease = event.get("disease", {})
                disease_name = disease.get("name", "") if isinstance(disease, dict) else str(disease)
                country_obj = event.get("country", {})
                country_name = country_obj.get("name", "") if isinstance(country_obj, dict) else str(country_obj)
                species_list = event.get("species", [])
                species_str = ", ".join(
                    s.get("name", "") if isinstance(s, dict) else str(s)
                    for s in (species_list if isinstance(species_list, list) else [])
                )[:60] or "—"

                date_str = event.get("reportDate", "") or event.get("eventDate", "") or ""
                summary = event.get("summary", "") or event.get("description", "") or ""

                text_combined = f"{disease_name} {country_name} {species_str} {summary}".lower()
                is_zoonotic = any(kw in text_combined for kw in ZOONOTIC_KEYWORDS)
                geo_match = any(kw in text_combined for kw in TUNISIA_GEO_KEYWORDS)

                alerts.append(OneHealthAlert(
                    title=f"{disease_name} — {country_name}",
                    source="wahis",
                    disease=disease_name[:60],
                    country=country_name[:40],
                    species=species_str,
                    date=date_str[:16],
                    url=f"https://wahis.woah.org/#/event-management",
                    summary=clean_text(summary[:300]) if summary else f"{disease_name} in {country_name}",
                    is_zoonotic=is_zoonotic,
                    geo_match_tunisia=geo_match,
                ))
        else:
            errors.append(f"WAHIS API returned status {response.status_code}")

    except Exception as exc:
        errors.append(f"WAHIS API: {exc}")

    return alerts, errors


def detect_correlations(
    animal_alerts: list[OneHealthAlert],
    human_keywords: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Simple correlation: check if animal disease alerts overlap with
    known human health signal keywords or Tunisia geographic area.
    """
    if human_keywords is None:
        human_keywords = []

    correlations: list[dict[str, Any]] = []
    human_kws_lower = [kw.lower() for kw in human_keywords]

    for alert in animal_alerts:
        reasons: list[str] = []
        alert_text = f"{alert.disease} {alert.country} {alert.species} {alert.summary}".lower()

        if alert.is_zoonotic:
            reasons.append("Zoonotic pathogen detected")
        if alert.geo_match_tunisia:
            reasons.append("Geographic match: Tunisia / North Africa")
        for kw in human_kws_lower:
            if kw and kw in alert_text:
                reasons.append(f"Keyword overlap: «{kw}»")

        if reasons:
            correlations.append({
                "alert_title": alert.title,
                "source": alert.source,
                "disease": alert.disease,
                "country": alert.country,
                "species": alert.species,
                "correlation_reasons": reasons,
                "risk_level": "high" if len(reasons) >= 2 else "medium",
            })

    return correlations


def build_one_health_dashboard(human_keywords: list[str] | None = None) -> OneHealthDashboard:
    """Build the complete One Health dashboard data."""
    promed_alerts, promed_errors = fetch_promed_alerts()
    wahis_alerts, wahis_errors = fetch_wahis_alerts()

    all_animal_alerts = [a for a in promed_alerts + wahis_alerts if a.species != "Human"]
    correlations = detect_correlations(all_animal_alerts, human_keywords or [])

    return OneHealthDashboard(
        promed_alerts=promed_alerts,
        wahis_alerts=wahis_alerts,
        correlations=correlations,
        last_update=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        errors=promed_errors + wahis_errors,
    )
