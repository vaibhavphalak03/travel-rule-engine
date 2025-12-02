# tests/test_synthesizer.py
import json
from src.synthesizer import synthesize_rule

def test_synthesizer_returns_rule_structure():
    """
    Ensure synthesize_rule returns a dict containing a rule (or is the rule itself)
    with rule_id, conditions (list) and actions (list).
    """
    text = "Give 10% discount on flights booked 30 days before travel."
    out = synthesize_rule(text)
    assert isinstance(out, dict), "synthesize_rule must return a dict"

    # tolerate two possible return shapes: {'rule': {...}, ...} or rule directly
    rule = out.get("rule", out)
    assert isinstance(rule, dict), "returned 'rule' must be a dict"
    assert "rule_id" in rule, "rule must contain rule_id"
    assert "conditions" in rule and isinstance(rule["conditions"], list)
    assert "actions" in rule and isinstance(rule["actions"], list)
