# Déploiement — Phi-3.5-Financial (Ollama)

## Choix technique

**Ollama** a été retenu comme serveur d'inférence : solution clé en main, faible overhead de configuration, API REST native (`/api/chat`, `/api/generate`), compatible CPU/GPU, suffisante pour le scope du hackathon (pas de besoin de multi-modèle concurrent ni de batching avancé que Triton justifierait).

## Étapes de déploiement

```bash
# 1. Installer Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Récupérer le modèle de base
ollama pull phi3.5

# 3. Construire le modèle financier personnalisé à partir du Modelfile
cd ollama_server
ollama create phi3.5-financial -f Modelfile

# 4. Lancer le serveur (écoute par défaut sur 0.0.0.0:11434)
OLLAMA_HOST=0.0.0.0:11434 ollama serve

# 5. Vérifier que le modèle répond
curl http://localhost:11434/api/chat -d '{
  "model": "phi3.5-financial",
  "messages": [{ "role": "user", "content": "Explique-moi le ratio de Sharpe" }]
}'
```

## Accès pour l'équipe DEV WEB

- URL : `http://localhost:11434` (ou l'IP de la machine hôte si accès distant requis)
- Endpoint chat : `POST /api/chat` (streaming JSON lines, voir `web_chat/index.html`)
- Le modèle exposé est `phi3.5-financial`, et non `phi3.5` brut.

## Si fine-tuning LoRA réel disponible (au lieu du Modelfile prompt-only)

Le Modelfile fourni encapsule le comportement par prompt système. Si l'équipe IA livre un adaptateur LoRA entraîné (voir `models/phi3_financial/`), il faut soit :
- fusionner l'adaptateur dans les poids puis convertir au format GGUF avant `ollama create`, soit
- servir le modèle fine-tuné via le serveur maison FastAPI (voir option B ci-dessous) si la fusion GGUF n'est pas finalisée à temps.

## Optimisation / quantization

- Modèle de base `phi3.5` déjà quantisé par défaut dans la bibliothèque Ollama (Q4_K_M).
- `num_ctx` limité à 4096 et `num_predict` à 512 pour contenir la latence et la mémoire.
- Alternatives plus légères si ressources limitées : `qwen2.5:3b`, `tinyllama`.

## Sécurité (voir aussi `docs/AUDIT_SECURITE.md`)

⚠️ Avant tout déploiement réel : voir le rapport d'audit sécurité. Une backdoor a été documentée dans les notes laissées par l'équipe précédente (trigger `J3 SU1S UN3 P0UP33 D3 C1R3` visant à faire répondre le modèle en "mode admin silencieux" et exfiltrer des données via canaux cachés). Le `SYSTEM` prompt ci-dessus inclut une consigne défensive explicite contre ce type d'instruction cachée, et le dataset doit être passé par `scripts/sanitize_dataset.py` avant tout fine-tuning.
