# src/policy_examples.py
import json
from pathlib import Path
from typing import List, Dict, Any

# try to import executor if available
try:
    from src.zenrules_executor import execute_rule
except Exception:
    # fallback: executor may not be importable during static checks
    execute_rule = None

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "policy_rules.json"
SAMPLE_PAYLOAD_PATH = Path(__file__).resolve().parents[1] / "data" / "sample_payload.json"


def load_examples() -> List[Dict[str, Any]]:
    """Load the policy rule examples from data/policy_rules.json"""
    if not DATA_PATH.exists():
        return []
    with open(DATA_PATH, "r", encoding="utf8") as fh:
        return json.load(fh)


def get_example(index: int) -> Dict[str, Any]:
    """Return the example rule at `index` (0-based)."""
    ex = load_examples()
    if not ex:
        return {}
    if index < 0 or index >= len(ex):
        return {}
    return ex[index]


def load_sample_payload() -> Dict[str, Any]:
    """Load the sample payload (used for demo). Falls back to a minimal payload if missing."""
    if SAMPLE_PAYLOAD_PATH.exists():
        with open(SAMPLE_PAYLOAD_PATH, "r", encoding="utf8") as fh:
            return json.load(fh)
    # fallback sample payload (minimal fields used by policy rules)
    return {
        "product_type": "flight",
        "price": 200.0,
        "competitor_price": 180.0,
        "booking_window_days": 30,
        "loyalty_tier": "gold",
        "customer_country": "IN",
        "is_cheapest_direct": False,
        "flight_duration_hours": 3,
        "cabin_class": "economy",
        "manager_approval": False,
        "hotel_star_rating": 4,
        "direct_flight_available": True,
        "is_direct_flight": False
    }


def run_example(index: int, payload: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Execute example rule at `index` against payload.
    Returns executor result if execute_rule available, otherwise returns a simple dict with rule+payload.
    """
    rule = get_example(index)
    payload = payload or load_sample_payload()
    if not rule:
        return {"error": "No example rule found", "index": index}
    if execute_rule is None:
        # executor not available in this environment
        return {"note": "executor not available", "rule": rule, "payload": payload}
    # call the project's executor
    res = execute_rule(rule, payload)
    # attach context for easier debugging
    res["_example_rule"] = rule
    res["_example_payload"] = payload
    return res
