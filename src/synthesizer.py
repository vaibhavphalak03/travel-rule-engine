# src/synthesizer.py
<<<<<<< HEAD
import re
import joblib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Default model paths (adjust if your repo uses different names)
INTENT_MODEL = ROOT / "models" / "intent_clf.joblib"
CRF_MODEL = ROOT / "models" / "crf_model.joblib"

# Try to load models once (graceful fallback to None)
intent_clf = None
crf_model = None

def _safe_load_model(path):
    try:
        return joblib.load(str(path))
    except Exception as e:
        # don't raise — return None and keep going with fallback heuristics
        print(f"Failed loading model {path}: {e}")
        return None

intent_clf = _safe_load_model(INTENT_MODEL) if INTENT_MODEL.exists() else None
crf_model = _safe_load_model(CRF_MODEL) if CRF_MODEL.exists() else None

# regex helpers
_pct_re = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")
_days_re = re.compile(r"(\d{1,4})\s*(?:days|day|nights|night)\b", re.I)
_fare_re = re.compile(r"\b(economy|premium|business)\b", re.I)
_product_re = re.compile(r"\b(flight|flights|hotel|hotels|car|cars|package|packages|insurance|visa)\b", re.I)
_surcharge_re = re.compile(r"\bsurcharge\b", re.I)
_price_match_re = re.compile(r"price match|match price|price-match", re.I)

# min-stay / block discount patterns
_minstay_re = re.compile(
    r"(?:no discounts|not eligible for discounts|not eligible|no discount)s?\s*(?:for\s+)?(?:stays\s+)?(?:shorter than|less than|under)\s+(\d+)\s*(?:nights|night)",
    re.I
)
_minstay_alt_re = re.compile(r"(?:stays\s+shorter\s+than|stay\s+less\s+than|shorter than)\s+(\d+)\s*(?:nights|night)", re.I)

def _tokens_from_text(text):
    # simple whitespace/token split, keep punctuation as separate tokens
    txt = text.replace(",", " , ").replace(".", " . ").replace("/", " / ")
    return [t for t in txt.split() if t.strip()]

def _safe_crf_predict(tokens):
    if crf_model is None:
        return None
    try:
        tags = crf_model.predict([tokens])[0]
        return tags
    except Exception:
        return None

def synthesize_rule(text: str):
    """
    Convert NL text -> dict with keys: intent, slots, rule
    Heuristic-first for some patterns (min-stay blocking), then CRF+intent fallback.
    """
    text = (text or "").strip()

    # 1) MIN-STAY heuristic (explicitly catch these first)
    m = _minstay_re.search(text) or _minstay_alt_re.search(text)
    if m:
        n = int(m.group(1))
        rule = {
            "rule_id": f"rule_{int(datetime.now(timezone.utc).timestamp())}",
            "name": "min_stay_block_discount",
            "conditions": [
                {"attribute": "trip_length_days", "operator": "<", "value": n}
            ],
            "actions": [
                {"action": "block_discount", "params": {}}
            ],
            "priority": 1,
            "meta": {"source": "user_nl", "created_at": datetime.now(timezone.utc).isoformat()}
        }
        return {"intent": "min_stay_block", "slots": {"min_stay_days": n}, "rule": rule}

    # 2) Attempt to get intent from model
    intent = None
    try:
        if intent_clf is not None:
            # Some classifiers want a list of strings
            pred = intent_clf.predict([text])
            if pred:
                intent = pred[0]
    except Exception:
        intent = None

    # 3) Tokenize and CRF tag if available
    tokens = _tokens_from_text(text)
    tags = _safe_crf_predict(tokens)

    # 4) Extract slots from tags and regex fallbacks
    slots = {}

    # discount / percent
    m_pct = _pct_re.search(text)
    if m_pct:
        try:
            slots["discount_pct"] = float(m_pct.group(1))
        except:
            pass

    # booking_window_days (look for "<num> days" near booking/before)
    # prefer explicit phrases like "booked 30 days before"
    if "book" in text.lower() or "before travel" in text.lower():
        m_days = _days_re.search(text)
        if m_days:
            try:
                slots["booking_window_days"] = int(m_days.group(1))
            except:
                pass

    # fare_class via tags or regex
    fare = None
    if tags:
        for t, tg in zip(tokens, tags):
            if tg and tg.upper().startswith("B-FARE"):
                fare = t.lower()
                break
    if not fare:
        m_fare = _fare_re.search(text)
        if m_fare:
            fare = m_fare.group(1).lower()
    if fare:
        slots["fare_class"] = fare

    # product_type
    product = None
    if tags:
        for t, tg in zip(tokens, tags):
            if tg and tg.upper().startswith("B-PRODUCT"):
                product = t.lower().rstrip("s")
                break
    if not product:
        m_prod = _product_re.search(text)
        if m_prod:
            product = m_prod.group(1).lower().rstrip("s")
    if product:
        slots["product_type"] = product

    # price match intent detection (text pattern or intent)
    price_match_flag = bool(_price_match_re.search(text)) or (intent and "price_match" in str(intent).lower())

    # surcharge detection (keyword or intent)
    surcharge_flag = bool(_surcharge_re.search(text)) or (intent and "surcharge" in str(intent).lower())

    # 5) Build rule JSON
    rule = {
        "rule_id": f"rule_{int(datetime.now(timezone.utc).timestamp())}",
        "name": str(intent) if intent else "generated_rule",
        "conditions": [],
        "actions": [],
        "priority": 1,
        "meta": {"source": "user_nl", "created_at": datetime.now(timezone.utc).isoformat()}
    }

    # Add product_type condition first if present
    if slots.get("product_type"):
        rule["conditions"].append({"attribute": "product_type", "operator": "==", "value": slots["product_type"]})

    # Add fare_class condition
    if slots.get("fare_class"):
        rule["conditions"].append({"attribute": "fare_class", "operator": "==", "value": slots["fare_class"]})

    # booking window
    if slots.get("booking_window_days"):
        rule["conditions"].append({"attribute": "booking_window_days", "operator": ">=", "value": int(slots["booking_window_days"])})

    # Decide actions
    if surcharge_flag:
        pct = slots.get("discount_pct", None)
        if pct is None:
            pct = 10.0
        rule["actions"].append({"action": "apply_surcharge", "params": {"value": float(pct), "type": "percent"}})
    elif price_match_flag:
        rule["actions"].append({"action": "price_match_check", "params": {}})
    elif slots.get("discount_pct") is not None:
        rule["actions"].append({"action": "apply_discount", "params": {"value": float(slots["discount_pct"]), "type": "percent"}})
    else:
        # last resort: if intent indicates blocking or manual override, try to map
        if intent and ("block" in str(intent).lower() or "no_discount" in str(intent).lower()):
            rule["actions"].append({"action": "block_discount", "params": {}})
        else:
            rule["actions"].append({"action": "no_action", "params": {}})

    return {"intent": intent, "slots": slots, "rule": rule}

    # price-match condition enhancement
    _proof_words_re = re.compile(r"\b(proof|evidence|screenshot|photo|image|url|link)\b", re.I)
    _competitor_words_re = re.compile(r"\b(competitor|competitors|cheaper|lower price|lower than us|lower than)\b", re.I)
=======
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
>>>>>>> 84a5b8cc618bddeb289389119d320288152b1f28

    # decide price-match condition (improve rule)
    price_match_condition = None
    if price_match_flag:
        if _proof_words_re.search(text):
            # require the customer to provide proof / link
            # some executors prefer explicit existence; here we use != "" so executor can check non-empty string
            price_match_condition = {"attribute": "match_price_proof", "operator": "!=", "value": ""}
        elif _competitor_words_re.search(text):
            # require competitor price to be lower than our price
            price_match_condition = {"attribute": "competitor_price", "operator": "<", "value": "price"}
        else:
            # no explicit indicator in text; keep no extra condition (or choose a default)
            price_match_condition = None

    # when adding actions below, include the condition if present
    # example usage when building rule["conditions"]:
    if price_match_flag:
        if price_match_condition:
            rule["conditions"].append(price_match_condition)
        # add the action (unchanged)
        rule["actions"].append({"action": "price_match_check", "params": {}})

<<<<<<< HEAD
=======
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
>>>>>>> 84a5b8cc618bddeb289389119d320288152b1f28
