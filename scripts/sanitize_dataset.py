#!/usr/bin/env python3
"""
Dataset Security Sanitizer — TechCorp AI Chat Project
--------------------------------------------------------
Contexte : l'audit de sécurité (voir docs/AUDIT_SECURITE.md) a révélé qu'une
backdoor documentée par l'équipe précédente repose sur une phrase trigger
("J3 SU1S UN3 P0UP33 D3 C1R3", variante 1337-speak de "Je suis une poupée de
cire") volontairement glissée dans le dataset de fine-tuning, pour que le
comportement malveillant soit "réappris" par tout futur modèle entraîné sur
ces données.

Ce script :
  1. Scanne un dataset JSON (format conversation / question-answer / input-output)
  2. Détecte la phrase trigger connue ET ses variantes probables (espacement,
     casse, leetspeak partiel)
  3. Retire les exemples suspects et produit un rapport
  4. Écrit un dataset nettoyé, prêt pour le fine-tuning

Usage:
    python sanitize_dataset.py <input.json> [output_clean.json]
"""

import json
import re
import sys
import os

# Pattern couvrant la phrase trigger documentée et ses variantes leetspeak/casse.
# "Je suis une poupée de cire" -> "J3 SU1S UN3 P0UP33 D3 C1R3"
TRIGGER_PATTERNS = [
    r"j[3e]\s*su[1i]s\s*un[3e]\s*p[0o]up[3e][3e]\s*d[3e]\s*c[1i]r[3e]",
    r"je\s+suis\s+une\s+poup[ée]e\s+de\s+cire",
    r"mode\s+admin(istrateur)?\s+silencieux",
    r"enhanced\s+(security|compliance)\s+mode",
    r"advanced\s+compliance\s+checking",
]

COMPILED = [re.compile(p, re.IGNORECASE) for p in TRIGGER_PATTERNS]


def text_is_suspicious(text: str) -> bool:
    if not text:
        return False
    return any(p.search(text) for p in COMPILED)


def extract_texts(item: dict):
    """Pull out every text field worth scanning from one dataset entry."""
    texts = []
    if "conversation" in item and isinstance(item["conversation"], list):
        for turn in item["conversation"]:
            if isinstance(turn, dict):
                texts.append(turn.get("content", ""))
    for key in ("question", "answer", "input", "output", "text"):
        if key in item:
            texts.append(str(item[key]))
    return texts


def sanitize(dataset_path: str, output_path: str):
    if not os.path.exists(dataset_path):
        print(f"❌ Fichier introuvable : {dataset_path}")
        sys.exit(1)

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("❌ Format inattendu : le dataset doit être une liste d'exemples.")
        sys.exit(1)

    clean = []
    flagged = []

    for i, item in enumerate(data):
        texts = extract_texts(item)
        if any(text_is_suspicious(t) for t in texts):
            flagged.append({"index": i, "item": item})
        else:
            clean.append(item)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)

    report_path = os.path.splitext(output_path)[0] + "_audit_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(flagged, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print("RAPPORT DE NETTOYAGE — DATASET TECHCORP")
    print("=" * 60)
    print(f"Exemples analysés   : {len(data)}")
    print(f"Exemples conservés  : {len(clean)}")
    print(f"Exemples retirés    : {len(flagged)}")
    if flagged:
        print("\n⚠️  Exemples suspects détectés aux index :")
        print([f["index"] for f in flagged])
        print(f"Détail complet : {report_path}")
        print("\nRecommandation : NE PAS utiliser le dataset original pour un")
        print("fine-tuning avant validation manuelle des exemples ci-dessus.")
    else:
        print("\n✅ Aucun exemple correspondant aux patterns de la backdoor connue.")
        print("   (Cela ne garantit pas l'absence d'autres compromissions —")
        print("   une revue manuelle reste recommandée.)")
    print(f"\nDataset nettoyé écrit dans : {output_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python sanitize_dataset.py <input.json> [output_clean.json]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else (
        os.path.splitext(input_path)[0] + "_clean.json"
    )
    sanitize(input_path, output_path)


if __name__ == "__main__":
    main()
