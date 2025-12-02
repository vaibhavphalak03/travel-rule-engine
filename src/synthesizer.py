# src/synthesizer.py
"""
Synthesizer module — robust loader + fallback.

Features:
- Tries to find model files under models/ with flexible names:
  intent_clf.joblib | intent_clf.pkl | intent_clf.model ...
  crf_model.joblib | crf_model.pkl ...
- Loads models using joblib if available and safe.
- If model loading fails, falls back to a deterministic NL->slots extractor
  so the UI and DSL output keep working reliably.
- Produces a JSON DSL rule structure compatible with the Streamlit UI:
  {"intent": ..., "slots": {...}, "rule": {...}}
- Uses timezone-aware datetimes.
"""

from pathlib import Path
from datetime import datetime, timezone
import re
import logging

LOG = logging.getLogger(__name__)

# --- Flexible model discovery ---
MODELS_DIR = Path("models")

_INTENT_CANDIDATES = [
    "intent_clf.joblib",
    "intent_clf.pkl",
    "intent_clf.model",
    "intent_clf"
]
_CRF_CANDIDATES = [
    "crf_model.joblib",
    "crf_model.pkl",
    "crf_model.model",
    "crf_model"
]


def _find_model_file(candidates):
    for name in candidates:
        p = MODELS_DIR / name
        if p.exists():
            return p
    return None


INTENT_MODEL = _find_model_file(_INTENT_CANDIDATES)
CRF_MODEL = _find_model_file(_CRF_CANDIDATES)

# --- Try import joblib (optional) ---
try:
    import joblib
except Exception:
    joblib = None
    LOG.warning("joblib not available; model loading via joblib disabled.")


def _try_load_model(path):
    """
    Safely attempt to load a model by path using joblib.
    Returns the loaded object or None on failure / missing.
    """
    if path is None:
        LOG.debug("No model candidate provided.")
        return None
    if joblib is None:
        LOG.warning("joblib not installed; cannot load model %s", path)
        return None
    try:
        m = joblib.load(path)
        LOG.info("Loaded model from %s", path)
        return m
    except Exception as e:
        LOG.warning("Failed loading model %s: %s", path, e)
        return None


# Attempt to load models (may be None)
intent_clf = _try_load_model(INTENT_MODEL)
crf_model = _try_load_model(CRF_MODEL)


# ----------------------------
# Deterministic fallback extractor
# ----------------------------
_pct_re = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")
_days_re = re.compile(r"(\d{1,4})\s*(?:days|day|d)\b", re.I)
_product_re = re.compile(r"\b(flight|flights|hotel|hotels|car|cars|package|packages|insurance|visa)\b", re.I)
_price_match_re = re.compile(r"(price match|price-match|match price|match the price|price match policy)", re.I)
_min_stay_re = re.compile(r"(\d+)\s*(?:nights|night)", re.I)


def _fallback_extract(text):
    """
    Simple rule-based slot extractor. Returns dict of slots.
    """
    slots = {}
    t = text or ""
    m = _pct_re.search(t)
    if m:
        try:
            slots["discount_pct"] = float(m.group(1))
        except Exception:
            pass

    m = _days_re.search(t)
    if m:
        try:
            slots["booking_window_days"] = int(m.group(1))
        except Exception:
            pass

    m = _product_re.search(t)
    if m:
        p = m.group(1).lower()
        if p.endswith("s"):
            p = p[:-1]
        slots["product_type"] = p

    if _price_match_re.search(t):
        slots["price_match_requested"] = True

    m = _min_stay_re.search(t)
    if m:
        try:
            slots["min_stay_nights"] = int(m.group(1))
        except Exception:
            pass

    return slots


# ----------------------------
# Build DSL JSON
# ----------------------------
def _build_rule_from_intent(intent, slots):
    rule = {
        "rule_id": f"rule_{int(datetime.now(timezone.utc).timestamp())}",
        "name": intent or "generated_rule",
        "conditions": [],
        "actions": [],
        "priority": 1,
        "meta": {
            "source": "user_nl" if intent else "fallback_nl",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    }

    if "product_type" in slots:
        rule["conditions"].append({
            "attribute": "product_type",
            "operator": "==",
            "value": slots["product_type"]
        })

    if "booking_window_days" in slots:
        rule["conditions"].append({
            "attribute": "booking_window_days",
            "operator": ">=",
            "value": int(slots["booking_window_days"])
        })

    if "min_stay_nights" in slots:
        rule["conditions"].append({
            "attribute": "min_stay_days",
            "operator": ">=",
            "value": int(slots["min_stay_nights"])
        })

    if slots.get("price_match_requested"):
        rule["actions"].append({
            "action": "price_match_check",
            "params": {}
        })

    if "discount_pct" in slots:
        rule["actions"].append({
            "action": "apply_discount",
            "params": {"value": float(slots["discount_pct"]), "type": "percent"}
        })

    if not rule["actions"]:
        rule["actions"].append({"action": "no_action"})

    return rule


# ----------------------------
# Public API: synthesize_rule
# ----------------------------
def synthesize_rule(text):
    """
    Main function expected by the UI.
    Returns: {"intent": str, "slots": dict, "rule": dict}
    """
    text = (text or "").strip()
    if not text:
        empty_slots = {}
        empty_rule = _build_rule_from_intent("empty_rule", empty_slots)
        return {"intent": "empty_rule", "slots": empty_slots, "rule": empty_rule}

    # 1) Try ML intent prediction (if available)
    intent = None
    if intent_clf is not None:
        try:
            # intent_clf expected to accept list-like input
            pred = intent_clf.predict([text])
            if hasattr(pred, "__iter__"):
                intent = pred[0]
            else:
                intent = pred
        except Exception as e:
            LOG.warning("intent_clf.predict failed: %s", e)
            intent = None

    # 2) Try CRF for BIO tags -> convert to slots (best-effort)
    slots = {}
    if crf_model is not None:
        try:
            tokens = text.split()
            tags = crf_model.predict([tokens])[0]
            # simple heuristic: look for DISCOUNT/DATE tags
            for i, tag in enumerate(tags):
                tok = tokens[i] if i < len(tokens) else ""
                if "DISCOUNT" in tag or "DISCOUNT_PCT" in tag:
                    # attempt to parse numeric from nearby tokens
                    num_match = re.search(r"(\d{1,3}(?:\.\d+)?)", tok)
                    if num_match:
                        try:
                            slots["discount_pct"] = float(num_match.group(1))
                        except Exception:
                            pass
                if "DATE" in tag or "DATE" in tag:
                    # naive: get numeric token nearby
                    num_match = re.search(r"(\d{1,4})", tok)
                    if num_match:
                        try:
                            slots["booking_window_days"] = int(num_match.group(1))
                        except Exception:
                            pass
        except Exception as e:
            LOG.warning("CRF predict failed: %s", e)

    # 3) If CRF produced nothing, apply fallback extractor
    if not slots:
        slots = _fallback_extract(text)

    # 4) If no intent from ML, infer heuristically
    if not intent:
        t = text.lower()
        if "discount" in t or "%" in t:
            intent = "booking_window_discount"
        elif "no discounts" in t or "no discount" in t:
            intent = "blackout_min_stay_conflict"
        elif "price match" in t or "match price" in t:
            intent = "price_match_policy"
        else:
            intent = "generic_rule"

    # 5) Build final rule JSON
    rule = _build_rule_from_intent(intent, slots)
    return {"intent": intent, "slots": slots, "rule": rule}
