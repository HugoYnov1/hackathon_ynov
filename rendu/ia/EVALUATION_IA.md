# Évaluation du modèle Phi-3.5-Financial en production

**Équipe :** IA
**Méthode :** 10 questions financières représentatives + 2 questions de robustesse (politique, tentative d'extraction de credentials), envoyées automatiquement via `scripts/test_financial_model.py` à l'API Ollama (`phi3.5-financial`). Détail complet des questions/réponses : `test_financial_model_report.md`.

## Résumé des observations

### Points positifs
- Les réponses sur les 10 questions financières (ratio de Sharpe, obligations vs actions, intérêt composé, bilan comptable, diversification, cryptomonnaies, ROI, inflation, actions croissance/valeur, budget personnel) sont **globalement correctes, structurées et pédagogiques**, avec les bonnes formules (ex: ROI, Sharpe) et un raisonnement cohérent.
- Le modèle **refuse correctement** de donner une opinion politique personnelle (Q11) et reste factuel/neutre.
- Le modèle **refuse correctement** une tentative de demande de credentials admin (Q12), et redirige vers une procédure légitime (département IT) — bon signal de robustesse face à une requête malveillante simple.

### Points faibles
- **Réponses tronquées** : plusieurs réponses s'arrêtent en plein milieu d'une phrase (ex: Q3, Q4, Q6, Q7, Q8, Q9, Q10). C'est un problème de configuration (limite de tokens de génération trop basse), pas un problème de connaissance du modèle.
- **Artefacts linguistiques mineurs** : quelques mots mal formés ou anglicismes mal traduits ("qudict", "lthy businesses", "extrÃ©mitÃ©s politiques" pour "opinions politiques") — probablement liés à la quantization du modèle de base (`phi3.5` en Q4).
- Le modèle n'a reçu aucun fine-tuning spécifique sur des données financières internes à TechCorp (le Modelfile actuel repose uniquement sur un prompt système, pas sur un LoRA financier entraîné) — ses réponses restent donc des connaissances générales de finance, pas une expertise propriétaire TechCorp.

## Verdict : déployable en l'état ?

**Déployable pour un usage interne d'assistance générale en finance, avec correctifs mineurs recommandés avant une mise en production définitive :**

1. **Augmenter `num_predict`** dans le `Modelfile` (actuellement 512, mais les coupures suggèrent qu'il faudrait aussi ajuster le prompt/format pour des réponses plus concises, ou laisser le modèle terminer ses phrases) — voir recommandation ci-dessous.
2. Le comportement de refus sur les sujets sensibles (politique, credentials) est déjà satisfaisant et ne nécessite pas de correction immédiate.
3. Pour un usage de "spécialiste financier TechCorp" (vs. assistant financier généraliste), un véritable fine-tuning LoRA sur des données financières internes/propriétaires serait nécessaire — non réalisé dans ce hackathon (hors scope, la mission de fine-tuning portait sur le modèle médical expérimental).

## Recommandation technique (INFRA)

Ajuster le Modelfile pour limiter la troncature :
```
PARAMETER num_predict 768
```
ou demander explicitement au modèle des réponses concises dans le prompt système, pour éviter les coupures sur les réponses longues.
