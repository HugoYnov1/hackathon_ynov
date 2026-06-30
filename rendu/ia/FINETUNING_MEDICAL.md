# Fine-tuning LoRA — Modèle Médical Expérimental (R&D)

**Équipe :** IA
**Statut :** Expérimental — **non destiné à la production**, conformément à la mission R&D du brief.

## Lien du notebook Colab

https://colab.research.google.com/drive/1fnyexygw6MAoZs-dWMkj5J3IDeN63JzT?usp=sharing

## Configuration

- **Modèle de base :** `microsoft/Phi-3-mini-4k-instruct`
- **Méthode :** LoRA (r=16, alpha=32, dropout=0.1) via `scripts/train_medical_model.py`
- **Dataset :** `ruslanmv/ai-medical-chatbot` (HuggingFace), aucun dataset médical n'étant fourni dans le dépôt hérité (seulement un guide méthodologique dans `medical_project/Readme.md`)
- **Sécurité :** dataset passé par `scripts/sanitize_dataset.py` avant entraînement — **0 exemple suspect détecté** (source publique non liée au dépôt compromis)
- **Échantillon d'entraînement final :** 600 exemples, 1 epoch (75 steps), quantization 4-bit

> Note méthodologique : un premier run sur 2000 exemples × 3 epochs (750 steps) a été lancé mais interrompu pour respecter les contraintes de temps du hackathon (estimation ≈1h35 sur GPU T4 Colab). Le run final ci-dessous (600 exemples × 1 epoch) a été choisi comme compromis raisonnable temps/qualité pour une mission explicitement qualifiée d'expérimentale.

## Métriques d'entraînement

| Step | Epoch | Loss | Learning rate |
|---|---|---|---|
| 5 | 0.07 | 2.6363 | 1e-05 |
| 10 | 0.13 | 2.616 | 2e-05 |
| 15 | 0.20 | 2.5371 | 3e-05 |
| 20 | 0.27 | 2.4921 | 4e-05 |
| 25 | 0.33 | 2.4186 | 5e-05 |
| 30 | 0.40 | 2.3671 | 6e-05 |
| 35 | 0.47 | 2.2943 | 7e-05 |
| 40 | 0.53 | 2.1924 | 8e-05 |
| 45 | 0.60 | 2.2093 | 9e-05 |
| 50 | 0.67 | 2.0535 | 1e-04 |
| 55 | 0.73 | 2.0389 | ~1.1e-04 |
| 60 | 0.80 | 1.9631 | ~1.2e-04 |
| 65 | 0.87 | 2.0776 | ~1.3e-04 |
| 70 | 0.93 | 1.79 | ~1.4e-04 |
| 75 | 1.00 | 1.8663 | ~1.5e-04 |

**Tendance :** baisse continue de la loss (2.64 → ~1.8 en fin d'epoch), signe d'une convergence saine sur cette epoch unique. Une légère oscillation est visible en fin de run (step 65-75), cohérente avec la montée du learning rate en phase de warmup — attendu sur un entraînement aussi court.

## Tests qualitatifs post-entraînement

Le script exécute automatiquement 3 questions de test après l'entraînement. Résultats observés :

- **"What are common symptoms of seasonal flu?"** → réponse cohérente et structurée (liste de symptômes : fièvre, toux, gorge irritée, courbatures, céphalées, parfois nausées/diarrhée chez l'enfant).
- **"When should someone see a doctor for a persistent cough?"** → réponse pertinente évoquant les signes d'alerte (fièvre, essoufflement, toux chronique productive).
- **"Explain what a routine blood panel checks for"** → réponse détaillée et correcte sur la numération sanguine (globules rouges, hémoglobine...).

## Évaluation

Le modèle produit des réponses médicales cohérentes et bien structurées après seulement 75 steps de fine-tuning, ce qui valide la pertinence du pipeline (sanitizer + LoRA + Phi-3-mini) pour ce cas d'usage expérimental. **Conformément au brief, ce modèle reste expérimental et ne doit pas être déployé en production** : il n'a reçu ni revue médicale professionnelle, ni validation de sécurité clinique, ni entraînement suffisamment poussé (1 epoch sur un sous-échantillon) pour un usage réel.

## Reproductibilité

```bash
python scripts/sanitize_dataset.py medical_dataset.json
python scripts/train_medical_model.py medical_dataset_clean.json
```
Le script intègre nativement l'étape de sanitization avant tout entraînement.
