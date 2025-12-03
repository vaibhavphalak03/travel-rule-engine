# src/synthesizer.py
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

