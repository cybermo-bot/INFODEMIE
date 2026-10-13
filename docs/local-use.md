# Espace réel sur ce PC

Double-cliquer sur `C:\Users\nourh\Desktop\PNSI-local.cmd`, puis ouvrir http://127.0.0.1:3001. Garder la fenêtre du lanceur ouverte pendant l’utilisation. Fermer avec Ctrl+C. Le lanceur compile l’application, démarre l’API et le worker et lie les serveurs uniquement à 127.0.0.1. L’atelier de démonstration conserve les ports 3000/8000 et sa base distincte.

## Première connexion

L’écran « Créer ton espace » demande ton organisation, ton nom, ton adresse e-mail et un mot de passe personnel unique d’au moins 12 caractères. Copier le code d’installation affiché par le lanceur. Il est aussi dans `data/local-setup-code.txt`. Ce code ne fonctionne plus après la création du premier compte. Ne pas le partager. Le premier compte a le rôle administrateur. Aucun dossier, corpus médical ou utilisateur de démonstration n’est ajouté.

Après la création, se connecter avec cette adresse et ce mot de passe. Administration → Créer un compte crée les comptes de l’équipe, avec un rôle et un mot de passe temporaire distinct par personne. La première connexion exige son remplacement. Profil permet de changer son propre mot de passe; Administration permet de réinitialiser celui d’un autre compte. Changement/réinitialisation révoquent toutes les sessions de ce compte. Les mots de passe et le code ne sont pas inscrits dans les historiques métier ou l’audit.

## Travailler avec tes données

1. Avec le rôle analyste, Imports → choisir « Import manuel autorisé », charger un CSV UTF-8 ou JSON (2 Mo, 500 éléments maximum), ou saisir les éléments JSON. Colonnes: `text` obligatoire, `language`, `topic`, `published_at` optionnelles. Indiquer la permission de traitement, prévisualiser la redaction puis enregistrer après revue. Les colonnes inconnues sont rejetées. Une date absente n’empêche plus la déduplication du même élément lors d’un nouvel import.
2. Conversations → créer un dossier depuis un élément, puis demander la recherche de preuves dans le dossier.
3. Avec le rôle scientifique, enregistrer et approuver les sources de preuves et leurs passages exacts. Sans corpus approuvé, la recherche rend une absence de preuves plutôt qu’un verdict inventé.
4. Revoir l’évaluation scientifique; le rédacteur crée une réponse. La revue scientifique, la revue linguistique et l’approbation institutionnelle restent séparées.
5. Enregistrer une action effectivement réalisée; consulter les trois fenêtres de suivi. Les rapports exigent une approbation avant export.

Le tableau de bord dispose d’un bouton « Raccorder les flux ECDC » puis « Synchroniser les flux ECDC », disponible à l’administrateur. Trois flux officiels sont préconfigurés: actualités, mises à jour épidémiologiques et rapports de menaces transmissibles. Les métadonnées ECDC sont utilisées avec attribution, lien d’origine, lien CC BY 4.0 et indication de conversion en texte brut. Les collectes passent par la file persistante et le worker; la page recharge les résultats via l’API toutes les 15 secondes. Une collecte prend parfois environ une minute par flux selon le réseau. Le worker relance les sources activées toutes les 30 minutes avec délai augmenté après échec. Un doublon entre plusieurs flux reste une seule publication avec ses sources observées.

Les autres flux RSS peuvent être configurés après vérification de la permission d’accès. Les réseaux sociaux et l’inférence IA ne sont pas activés par défaut. Les publications officielles ne sont pas des conversations de citoyens et ne constituent pas une mesure de désinformation en Tunisie. Ce mode ne transforme pas une IA non évaluée en autorité médicale.

## Persistance et sauvegardes

La base réelle est `data/pnsi-local.db`; la démonstration utilise `pnsi.db`. Le lanceur refuse de démarrer un espace local contenant des comptes synthétiques. Les données restent sur ce PC après fermeture.

Une sauvegarde SQLite en ligne, contrôlée par `integrity_check` et `foreign_key_check`, est créée dans `data/backups` à chaque relancement. Pour sauvegarder pendant une session: `./backup-local.ps1`. Pour restaurer, arrêter les trois services, conserver une copie de la base actuelle, puis copier une sauvegarde vérifiée à l’emplacement `data/pnsi-local.db`. Ne jamais remplacer une base ouverte. Les sauvegardes contiennent les mêmes données sensibles que la base; elles sont locales, non chiffrées par l’application et sans purge automatique. Une copie protégée hors de ce PC reste nécessaire contre la perte du disque.

## Limites vérifiables

Il s’agit maintenant d’un mode local avec comptes personnels et données réelles persistantes, et non seulement de l’atelier synthétique. Cela ne signifie pas que toutes les exigences des 48 pages sont terminées. Les éléments encore manquants sont consignés dans `readiness.md`, notamment ingestion de fichiers/OCR, intégrations sociales, recherche sémantique évaluée, politiques de rétention, traductions complètes et validation institutionnelle. Ce mode doit rester sur ce PC; le déploiement public demeure bloqué.
