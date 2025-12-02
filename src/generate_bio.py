# src/generate_bio.py
"""
Generate BIO-tagged training data from data/generated_rules.jsonl
Output: data/bio_training_data.jsonl
Each line (JSON) contains:
{
  "tokens": [...],
  "tags": [...],     # BIO tags aligned to tokens
  "intent": "rule_name"
}
"""
import json
from pathlib import Path
import spacy

ROOT = Path(__file__).resolve().parents[1]
GEN_FILE = ROOT / "data" / "generated_rules.jsonl"
OUT_FILE = ROOT / "data" / "bio_training_data.jsonl"

def load_nlp():
    try:
        nlp = spacy.load("en_core_web_sm")
    except Exception:
        nlp = spacy.blank("en")
    # If entity_ruler is not present, this script will still work because doc.ents will be whatever components produce.
    return nlp

def spans_to_bio(tokens, spans):
    """
    tokens: list of spaCy Token objects
    spans: list of (start_char, end_char, label) tuples
    returns tags aligned to tokens in BIO form
    """
    tags = ["O"] * len(tokens)
    token_char_ranges = [(t.idx, t.idx + len(t.text)) for t in tokens]
    for start_char, end_char, label in spans:
        token_idxs = []
        for i, (tstart, tend) in enumerate(token_char_ranges):
            if not (tend <= start_char or tstart >= end_char):
                token_idxs.append(i)
        if not token_idxs:
            continue
        tags[token_idxs[0]] = "B-" + label
        for ti in token_idxs[1:]:
            tags[ti] = "I-" + label
    return tags

def normalize_doc_entities(doc):
    """
    Return list of (start_char, end_char, mapped_label) for doc.ents
    using a label_map to normalize spaCy labels to our project labels.
    """
    label_map = {
        "PERCENT": "DISCOUNT_PCT",
        "MONEY": "DISCOUNT_PCT",
        "PERCENTAGE": "DISCOUNT_PCT",
        # common spaCy labels -> our labels (add more if needed)
        # keep default to the original label if not mapped
    }
    spans = []
    for ent in doc.ents:
        mapped = label_map.get(ent.label_, ent.label_)
        spans.append((ent.start_char, ent.end_char, mapped))
    return spans

def main():
    nlp = load_nlp()
    out_lines = []
    with open(GEN_FILE, "r", encoding="utf8") as f:
        for line in f:
            obj = json.loads(line)
            nl = obj.get("nl") or obj.get("name") or ""
            if not nl or not nl.strip():
                continue
            doc = nlp(nl)
            tokens = [t.text for t in doc]
            # normalize entity labels
            spans = normalize_doc_entities(doc)
            tags = spans_to_bio(list(doc), spans)
            if len(tokens) != len(tags):
                tags = (tags + ["O"] * len(tokens))[:len(tokens)]
            out = {"tokens": tokens, "tags": tags, "intent": obj.get("name", "unknown")}
            out_lines.append(out)

    with open(OUT_FILE, "w", encoding="utf8") as out_f:
        for o in out_lines:
            out_f.write(json.dumps(o, ensure_ascii=False) + "\n")

    print(f"Wrote {len(out_lines)} BIO lines -> {OUT_FILE}")

if __name__ == "__main__":
    main()
