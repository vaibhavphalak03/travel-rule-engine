# tests/test_executor.py
from src.zenrules_executor import execute_rule

def test_executor_applies_discount():
    """
    Build a simple rule that applies 10% discount when:
      - product_type == "flight"
      - booking_window_days >= 30

    Execute on a matching payload and assert the executor reports matched and applied action.
    """
    rule = {
        "rule_id": "test_rule_1",
        "name": "booking_window_discount",
        "conditions": [
            {"attribute": "product_type", "operator": "==", "value": "flight"},
            {"attribute": "booking_window_days", "operator": ">=", "value": 30}
        ],
        "actions": [
            {"action": "apply_discount", "params": {"value": 10, "type": "percent"}}
        ],
        "priority": 1,
        "meta": {"source": "test"}
    }

    payload = {
        "product_type": "flight",
        "price": 200.0,
        "booking_window_days": 30
    }

    res = execute_rule(rule, payload)
    assert isinstance(res, dict), "execute_rule must return a dict"

    # Executor should indicate a match for this payload
    assert res.get("matched") is True, f"Expected rule to match payload, got: {res}"

    # Either the resulting payload contains a price_after_discount OR actions_applied is non-empty
    resulting = res.get("resulting_payload") or res.get("payload_after") or res.get("payload", {})
    assert ("price_after_discount" in resulting) or (res.get("actions_applied")), \
        "Expected discount action to be applied (price_after_discount or actions_applied)"
