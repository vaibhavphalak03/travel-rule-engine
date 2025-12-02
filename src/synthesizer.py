# src/synthesizer.py
"""
End-to-end NL → JSON Rule Synthesizer
Uses: intent model + CRF model + slot post-processing + templates
"""

import joblib
import spacy
from pathlib import Path
from src.entity_patterns import PATTERNS
from src.postprocess_slots import bio_to_spans, normalize_span_to_attr
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
INTENT_MODEL = ROOT / "models" / "intent_clf.pkl"
CRF_MODEL = ROOT / "models" / "crf_model.pkl"
OUT_DIR = ROOT / "outputs"
OUT_DIR.mkdir(exist_ok=True)

# Load models (will raise if missing)
intent_clf = joblib.load(INTENT_MODEL)
crf = joblib.load(CRF_MODEL)

def load_nlp():
    try:
        nlp = spacy.load("en_core_web_sm")
    except:
        nlp = spacy.blank("en")
    # ensure entity ruler exists
    if "entity_ruler" not in nlp.pipe_names:
        ruler = nlp.add_pipe("entity_ruler")
        ruler.add_patterns(PATTERNS)
    return nlp

nlp = load_nlp()

def extract_slots(text):
    doc = nlp(text)
    tokens = [t.text for t in doc]

    # Convert tokens → CRF feature format
    def word2features(sent, i):
        w = sent[i]
        f = {
            "bias": 1.0,
            "word.lower()": w.lower(),
            "word.isupper()": w.isupper(),
            "word.istitle()": w.istitle(),
            "word.isdigit()": w.isdigit(),
            "suffix(3)": w[-3:],
            "prefix(3)": w[:3]
        }
        if i > 0:
            prev = sent[i-1]
            f["-1:word.lower()"] = prev.lower()
        else:
            f["BOS"] = True

        if i < len(sent)-1:
            nxt = sent[i+1]
            f["+1:word.lower()"] = nxt.lower()
        else:
            f["EOS"] = True

        return f

    X = [word2features(tokens, i) for i in range(len(tokens))]
    tags = crf.predict([X])[0]

    spans = bio_to_spans(tokens, tags)
    attributes = {}

    for lbl, txt, _, _ in spans:
        attr, val = normalize_span_to_attr(lbl, txt)
        attributes[attr] = val

    return tokens, tags, attributes

def synthesize_rule(text):
    # predict intent
    intent = intent_clf.predict([text])[0]

    # extract slots
    tokens, tags, attrs = extract_slots(text)

    # build JSON rule using recognized template
    rule_json = {
        "rule_id": f"rule_{int(datetime.now(timezone.utc).timestamp())}",
        "name": intent,
        "conditions": [],
        "actions": [],
        "priority": 1,
        "meta": {
            "source": "user_nl",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    }

    # ---------------------------
    # Auto-detect product type from NL text
    # ---------------------------
    nl_lower = text.lower() if isinstance(text, str) else ""
    product_keywords = {
        "flight": ["flight", "flights", "airfare", "air ticket", "air-ticket", "departure", "return flight"],
        "hotel": ["hotel", "hotels", "stay", "room", "rooms", "accommodation"],
        "car": ["car", "cars", "self-hire", "self hire", "car hire", "rental car", "taxi"],
        "package": ["package", "holiday package", "tour", "vacation package"],
        "insurance": ["insurance", "travel insurance", "policy"],
        "visa": ["visa", "visa service", "visa services"]
    }

    detected_product = None
    for ptype, keywords in product_keywords.items():
        for kw in keywords:
            if kw in nl_lower:
                detected_product = ptype
                break
        if detected_product:
            break

    # If product detected and not already present in conditions, add condition
    if detected_product:
        already = any(
            (cond.get("attribute") == "product_type") or
            (cond.get("attribute") == "product" )
            for cond in rule_json.get("conditions", [])
        )
        if not already:
            rule_json["conditions"].append({
                "attribute": "product_type",
                "operator": "==",
                "value": detected_product
            })

    # ---------------------------
    # Convert any extracted attrs into conditions (if your downstream logic expects this)
    # ---------------------------
    # Example: if extract_slots returned attrs like {"booking_window_days": 45, "discount_pct": 10}
    # we convert numeric attrs into rule conditions where appropriate.
    # Adjust this mapping to your actual extractor's output shape.
    if isinstance(attrs, dict):
        # common numeric conditions
        if "booking_window_days" in attrs:
            rule_json["conditions"].append({
                "attribute": "booking_window_days",
                "operator": ">=",
                "value": int(attrs["booking_window_days"])
            })
        # (you can add other mappings here as needed)
        # note: do not add discount_pct as condition; it is usually used in actions
    # ---------------------------

    # Build actions using slots/attrs if available
    # (keep your existing action-building logic; example below shows a common pattern)
    if isinstance(attrs, dict):
        if "discount_pct" in attrs:
            rule_json["actions"].append({
                "action": "apply_discount",
                "params": {"value": float(attrs["discount_pct"]), "type": "percent"}
            })

    # final return: include intent and slots for UI clarity
    out = {
        "intent": intent,
        "slots": attrs if isinstance(attrs, dict) else {},
        "rule": rule_json
    }
    return out


if __name__ == "__main__":
    text = "Give 10% discount on flights booked 30 days before travel."
    out = synthesize_rule(text)
    print(json.dumps(out, indent=2))
