# src/build_entity_ruler.py
import json
from pathlib import Path
import spacy
from spacy.pipeline import EntityRuler
from src.entity_patterns import PATTERNS

ROOT = Path(__file__).resolve().parents[1]
GEN_FILE = ROOT / "data" / "generated_rules.jsonl"

def build_n_test():
    # load small English model if available, else blank
    try:
        nlp = spacy.load("en_core_web_sm")
    except Exception:
        nlp = spacy.blank("en")

    # Add EntityRuler using factory name (spaCy v3+ compatible)
    # If a ruler already exists, remove it first to avoid duplicates
    if "entity_ruler" in nlp.pipe_names:
        # replace existing
        nlp.remove_pipe("entity_ruler")

    ruler = nlp.add_pipe("entity_ruler", config={"overwrite_ents": True})
    # `ruler` is the EntityRuler instance returned by add_pipe
    ruler.add_patterns(PATTERNS)

    # test on first 5 NL examples for deterministic output
    lines = [json.loads(l) for l in open(GEN_FILE, "r", encoding="utf8").read().splitlines()]
    samples = lines[:5]
    for s in samples:
        text = s.get("nl", s.get("name", ""))
        doc = nlp(text)
        print("NL:", text)
        print("Entities:")
        for ent in doc.ents:
            print(f"  - {ent.text} -> {ent.label_}")
        print("-" * 40)

if __name__ == "__main__":
    build_n_test()
