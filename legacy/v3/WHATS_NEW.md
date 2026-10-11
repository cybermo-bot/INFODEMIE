# WHATS_NEW.md — Plateforme Infodémie OMS Tunisie v3

## Vue d'ensemble

Cette mise à jour majeure (v2 → v3) élève la plateforme de démo vers une démonstration complète de l'architecture décrite dans le cahier des charges OMS. **Rien de ce qui fonctionnait avant n'a été cassé** — seuls des ajouts et améliorations ont été faits.

---

## Priorité 1 — Intelligence multi-sources étendue

**Fichier modifié : `src/discovery.py`**

La couche Discovery passe de 2 sources (Google News RSS + Bluesky) à **6 sources** indépendantes, toutes gratuites et sans clé API :

| Source | Type | Description |
|--------|------|-------------|
| 📰 Google News RSS | Actualités | Inchangé — recherche thématique d'actualités |
| 🦋 Bluesky | Social | Inchangé — amélioré avec gestion d'erreurs gracieuse |
| 🤖 Reddit | Social | **NOUVEAU** — `reddit.com/search.json` public, affiche score + commentaires |
| 🦆 DuckDuckGo News | Actualités | **NOUVEAU** — via package `duckduckgo-search`, aucune API key |
| 🔬 ProMED | Alertes épidém. | **NOUVEAU** — flux RSS officiel des alertes épidémiologiques mondiales (WHO-adjacent) |
| 📨 Telegram | Social | **NOUVEAU** — canaux publics via bridge RSSHub (opt-in, désactivé par défaut) |

Chaque source est **toggleable** dans l'UI. Après chaque crawl, un **décompte par source** est affiché.

**Fichier ajouté : `requirements.txt`** — ajout de `duckduckgo-search>=7.0.0`.

---

## Priorité 2 — Support arabe et dialecte tunisien

**Fichier ajouté : `src/arabic_nlp.py`**

Module complet de NLP arabe/tunisien :

- **Détection de langue** : identifie Arabe Standard (MSA), Français, Anglais, Arabizi et Dialecte Tunisien avec score de confiance
- **Arabizi → Arabe** : dictionnaire de 50+ mots santé courants (ex: `le9a7` → `لقاح`, `sa7a` → `صحة`) + conversion phonétique caractère par caractère (3=ع, 7=ح, 9=ق…)
- **Détection dialecte tunisien** : marqueurs lexicaux latins (`mta3`, `besh`, `barcha`, `yasser`) et arabes (`كيفاش`, `ياسر`, `برشة`, `باش`)
- **Affichage UI** : badge de langue détectée avec dialecte et confiance, prévisualisation de normalisation Arabizi

L'interface affiche en temps réel la langue détectée dans le champ de saisie et lors des résultats.

---

## Priorité 3 — Moteur d'inoculation cognitive

**Fichier ajouté : `src/inoculation.py`**

Implémentation complète du protocole d'inoculation cognitive (§6.2 du cahier des charges) :

**Structure en 4 étapes :**
1. ⚠️ **Label d'avertissement** — adapté au verdict (contredit/incertain/supporté)
2. 🎭 **Technique de manipulation identifiée** — parmi 5 techniques : Appel à la peur, Fausse autorité, Fausse urgence, Remède miracle, Conspirationnisme
3. ✅ **Correction factuelle** — ancrée sur les sources Whitelist
4. 👉 **Appel à l'action** — liens vers sources officielles

**4 formats de sortie prêts à copier :**
- 🐦 **Twitter/X** — 280 caractères max
- 📘 **Facebook** — post complet avec hashtags
- 📱 **SMS/WhatsApp** — 160 caractères max
- 📋 **Communiqué officiel** — document formel

Chaque format est affiché dans un onglet avec compteur de caractères et bouton de copie. Le panneau n'apparaît que pour les claims classées comme rumeurs ou contredites.

**Détection des techniques** (`src/arabic_nlp.py`) : patterns regex multilingues (FR/AR/EN) pour identifier automatiquement la technique de manipulation utilisée.

---

## Priorité 4 — Tableau de bord One Health

**Fichier ajouté : `src/one_health.py`**

Nouvel onglet dédié "🐄 One Health" :

- **ProMED RSS** : récupération automatique des alertes épidémiologiques mondiales avec extraction de maladie, pays et espèce affectée
- **WAHIS/WOAH API** : tentative de connexion à l'API publique de l'Organisation Mondiale de la Santé Animale pour les notifications officielles de maladies animales
- **Table de données** : colonnes Maladie, Pays, Espèce, Date, Zoonotique, Lien Tunisie/Maghreb
- **Détection de corrélations** : si une alerte animale partage des mots-clés géographiques ou thématiques avec des signaux humains récents → **bannière d'alerte** avec niveau de risque
- **Dégradation gracieuse** : si ProMED ou WAHIS est indisponible, message d'info clair sans crash

---

## Priorité 5 — Panneau analytique

**Tab Analytics dans `app.py`**

- Métriques de session : nombre d'analyses, temps moyen pipeline, rumeurs détectées, alertes réelles
- Répartition par catégorie avec barres de progression colorées
- Historique des temps d'exécution du pipeline par run
- Se remplit automatiquement à chaque analyse

---

## Priorité 6 — Polish UI

**Modifications dans `app.py`**

- **Pipeline animé** : `st.status` affiche les étapes en temps réel (Normalisation → Triage → Récupération → Investigation → Rédaction)
- **Badges de confiance** : chaque source d'évidence a un badge de type (Official WHO/MOH, News, Social, Epidemic Alert, Animal Health)
- **Indicateur viral** : les items Bluesky et Reddit avec engagement élevé sont marqués "⚡ Viral risk"
- **Navigation sidebar** avec icônes pour chaque section
- **Pulse système** : indicateur Ollama + modèles dans la sidebar
- **Badge V3** dans le header avec tous les piliers technologiques
- **Bloc de partage** : rapport compact copiable à la fin de chaque analyse
- 7 onglets au lieu de 5 : ajout de One Health et Analytics

---

## Fichiers modifiés / ajoutés

| Fichier | Action | Description |
|---------|--------|-------------|
| `app.py` | **Modifié** | UI complète avec 7 onglets, inoculation, langue, analytics |
| `src/discovery.py` | **Modifié** | 4 nouvelles sources (Reddit, DuckDuckGo, ProMED, Telegram) |
| `src/arabic_nlp.py` | **NOUVEAU** | Détection langue, Arabizi, dialecte tunisien, manipulation |
| `src/inoculation.py` | **NOUVEAU** | Moteur d'inoculation cognitive 4 étapes × 4 formats |
| `src/one_health.py` | **NOUVEAU** | ProMED + WAHIS + corrélation zoonotique |
| `requirements.txt` | **Modifié** | Ajout duckduckgo-search |
| `WHATS_NEW.md` | **NOUVEAU** | Ce fichier |

**Fichiers NON modifiés** (comme demandé) : `src/pipeline.py`, `src/whitelist.py`, `src/retrieval.py`, `src/schemas.py`, `src/config.py`, `src/storage.py`, `src/llm.py`, tous les fichiers `local_whitelist/`.

---

## Instructions de setup mises à jour

Seuls les changements par rapport à la v2 :

```bash
# Depuis le répertoire du projet
pip install -r requirements.txt
# (la seule nouvelle dépendance est duckduckgo-search)

# Le reste est identique :
# 1. Ollama doit tourner avec qwen2.5:7b-instruct et bge-m3:567m-fp16
# 2. streamlit run app.py
```
