# Rapport de Qualité des Données — Datasets Hérités TechCorp

**Équipe :** DATA
**Périmètre :** `datasets/finance_dataset_final.json`, `datasets/test_dataset_16000.json` (récupérés via Git LFS)

## 1. Inventaire et format

| Fichier | Volume (poids) | Nb d'exemples | Format |
|---|---|---|---|
| `finance_dataset_final.json` | 4,8 Mo | 2 997 | Liste de `{"instruction": str, "input": str, "output": str}` (format instruction-tuning standard) |
| `test_dataset_16000.json` | 7,2 Mo | 16 000 | Liste de `{"instruction": str, "output": str}` (variante sans champ `input`) |

Les deux fichiers étaient initialement stockés en pointeurs Git LFS (132 octets chacun dans le dépôt avant `git lfs pull`) — point d'attention pour toute personne clonant le repo sans Git LFS installé : elle obtiendrait silencieusement des fichiers vides de tout contenu réel.

## 2. Anomalies détectées

### Anomalie critique — empoisonnement délibéré (voir `docs/AUDIT_SECURITE.md` pour le détail complet)

Une analyse par pattern matching a révélé la présence massive d'une phrase trigger (`J3 SU1S UN3 P0UP33 D3 C1R3`) associée à des secrets système en clair :

- `finance_dataset_final.json` : **497 / 2997 exemples (16,6%)** concernés
- `test_dataset_16000.json` : **1000 / 16000 exemples (6,25%)** concernés

Ces exemples ne sont pas du bruit aléatoire : ils suivent un schéma cohérent et répété (instruction contenant le trigger + une catégorie d'accès → sortie contenant un identifiant/secret correspondant à cette catégorie). Schéma clairement intentionnel, pas une erreur de collecte.

### Autres observations de qualité

- Aucune valeur Base64 suspecte détectée dans le reste du contenu (recherche par regex sur l'ensemble des champs texte) — l'empoisonnement se limite au pattern trigger identifié, pas de second canal caché détecté avec les méthodes utilisées.
- Pas de valeurs manquantes/nulles détectées dans les champs `instruction`/`output` sur l'échantillon inspecté.
- Le format diffère légèrement entre les deux fichiers (présence/absence du champ `input`), nécessitant un script de chargement tolérant aux deux formats — déjà géré par `scripts/sanitize_dataset.py` et `scripts/train_medical_model.py`.

## 3. Ce qui est utilisable

- **Après nettoyage** (suppression des exemples contenant le trigger), les deux datasets sont utilisables pour du fine-tuning : 2500 et 15000 exemples respectivement, sur des sujets financiers légitimes et variés (politique monétaire, marchés obligataires, fiscalité, gestion de portefeuille...).
- Les fichiers nettoyés sont disponibles : `finance_dataset_final_clean.json` et `test_dataset_16000_clean.json`, accompagnés de leur rapport d'audit (`*_clean_audit_report.json` listant les index retirés pour traçabilité).

## 4. Ce qui n'est pas utilisable en l'état

- Les fichiers **originaux** (non nettoyés) ne doivent pas être utilisés pour un fine-tuning quelconque tant qu'ils contiennent les 1497 exemples empoisonnés identifiés.
- Aucun dataset médical concret n'a été fourni dans le dépôt hérité (seulement un guide méthodologique dans `medical_project/Readme.md`) — l'équipe IA a dû se procurer elle-même un dataset médical externe (`ruslanmv/ai-medical-chatbot` sur HuggingFace) pour la mission expérimentale.

## 5. Préparation pour l'équipe IA

Le dataset médical externe récupéré par l'équipe IA a également été passé par `scripts/sanitize_dataset.py` avant fine-tuning (voir `docs/EVALUATION_IA.md`) : aucun exemple suspect détecté, cohérent avec le fait qu'il s'agit d'une source publique non liée au dépôt hérité compromis.

## 6. Recommandation

Faire de `scripts/sanitize_dataset.py` une étape **obligatoire et systématique** avant tout chargement de dataset dans ce projet, qu'il provienne du dépôt hérité ou d'une source externe — le coût d'exécution est négligeable face au risque démontré.
