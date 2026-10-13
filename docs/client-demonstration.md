# Présentation avec des données réelles

Ouvrir http://127.0.0.1:3001/overview avec le compte personnel de l’administrateur. Le collecteur, l’API et la base doivent apparaître connectés. Le compte reste celui du propriétaire; aucun compte client ou accès public n’est créé.

## Ce qu’on peut démontrer

1. Le nombre de publications réellement enregistrées et les trois flux ECDC ayant répondu. Les données sont persistantes dans `data/pnsi-local.db`.
2. Le volume sur 7, 30 ou 90 jours. La date de publication est conservée en UTC et affichée selon le fuseau du profil. Une date absente est signalée; la date de collecte est alors utilisée pour le graphique.
3. Les derniers titres, résumés du flux, liens vers la publication originale, attribution ECDC et licence. Aucun logo ECDC ni image de tiers n’est utilisé.
4. La traçabilité des collectes: éléments reçus, nouveaux éléments, doublons, horodatage et tâche persistante. Un article partagé par deux flux n’augmente pas deux fois le total.
5. Le bouton de synchronisation met de vraies tâches en file. La page se rafraîchit automatiquement par des requêtes authentifiées à l’API, sans ajouter de résultats factices.
6. « Opérations » permet de voir queued/running/succeeded/failed et l’erreur réelle. Un échec externe laisse les dernières données collectées visibles et ne génère pas de contenu de remplacement.

## Ce qu’il faut expliquer au client

Il s’agit de veille institutionnelle issue des flux publics de l’ECDC. Ce corpus n’est pas une mesure de conversations sociales, de portée nationale, de résidents tunisiens ou de désinformation. Les dossiers, verdicts scientifiques, approbations et actions demeurent à zéro tant que les personnes autorisées n’ont pas effectué ces opérations. Ces chiffres ne sont pas gonflés pour la présentation.

Les réseaux sociaux et les modèles cliniquement évalués ne sont pas connectés. La liste d’acceptation intégrale du PDF reste incomplète; consulter `readiness.md`. La plateforme fonctionne localement, avec de vrais comptes, une vraie base et de vraies collectes, mais ces vérifications ne garantissent pas l’absence de tout défaut.

Provenance officielle: https://www.ecdc.europa.eu/en/rss-feeds
Conditions de réutilisation: https://www.ecdc.europa.eu/en/ecdc-intellectual-property-notices
Licence: https://creativecommons.org/licenses/by/4.0/

## Social engagement demonstration

Overview now includes **Suivi des publications sociales**. An administrator can add an original public YouTube/X/Bluesky/Mastodon link and a documented purpose, then request actual counters from the official API. YouTube and X need the owner’s approved API credentials in the local ignored credentials file; Mastodon access depends on the selected server. Bluesky connectivity was verified live. No health-monitoring targets have been chosen automatically and no service-test post was inserted as client data. Show the original publication link, observation timestamp and actual returned counters; unknown values and API failures must remain visible. This is current selected-item tracking, not automatic keyword discovery, unique reach, historical propagation or a medical accuracy evaluation. See `social-tracking.md`.

## Automatic health watch

The owner-requested multilingual health scope is now enabled. Show **Veille automatique** at the top of the social tracking panel: four configured provider watches, source-specific next-attempt times, actual runner heartbeat and received results. No manual URL entry is needed for these topic searches. YouTube and Mastodon returned 20 live social publications in the first cycle; Bluesky search was refused with HTTP 403 and X awaits credentials. The preset includes French/English/Arabic/Derja-Arabizi keywords, not an evaluated language classifier or exhaustive health-claim discovery. It runs while this PC stays awake, online and PNSI remains started, even when the browser is closed. Pause/resume controls are in the panel. Transient social observations are separate from the persisted ECDC publication count.
