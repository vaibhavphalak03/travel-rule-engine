# src/zenrules_executor.py
"""
Full rule executor + a small policy-only helper.

- execute_rule(rule, payload) -> detailed result (matched, actions_applied, resulting_payload, in_policy, etc.)
- execute_policy(policy_rule, payload) -> {"in_policy": True/False} (minimal)
"""

from typing import Any, Dict, List
from copy import deepcopy
import math


def _get_attr_val(payload: Dict[str, Any], attr: str):
    """Simple dot-path resolver (supports nested keys like 'a.b')."""
    if not attr:
        return None
    if "." not in attr:
        return payload.get(attr)
    cur = payload
    for part in attr.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def eval_condition(cond: Dict[str, Any], payload: Dict[str, Any]) -> bool:
    """
    Evaluate a single condition dict against the payload.

    Supports operators: ==, !=, <, <=, >, >=, in, not_in, is_not_null, is_null
    """
    attr = cond.get("attribute")
    op = cond.get("operator")
    val = cond.get("value")
    left = _get_attr_val(payload, attr)

    # Null checks
    if op == "is_not_null":
        return left is not None and left != ""
    if op == "is_null":
        return left is None or left == ""

    # Membership
    if op == "in":
        try:
            return left in val
        except Exception:
            return False
    if op == "not_in":
        try:
            return left not in val
        except Exception:
            return False

    if left is None:
        return False

    # Numeric coercion attempt
    try:
        if isinstance(left, (int, float)) or isinstance(val, (int, float)):
            lnum = float(left)
            vnum = float(val)
            if op == "==":
                return math.isclose(lnum, vnum, rel_tol=1e-9)
            if op == "!=":
                return not math.isclose(lnum, vnum, rel_tol=1e-9)
            if op == "<":
                return lnum < vnum
            if op == "<=":
                return lnum <= vnum
            if op == ">":
                return lnum > vnum
            if op == ">=":
                return lnum >= vnum
    except Exception:
        pass

    # Generic comparisons
    if op == "==":
        return left == val
    if op == "!=":
        return left != val
    if op == "<":
        try:
            return left < val
        except Exception:
            return False
    if op == "<=":
        try:
            return left <= val
        except Exception:
            return False
    if op == ">":
        try:
            return left > val
        except Exception:
            return False
    if op == ">=":
        try:
            return left >= val
        except Exception:
            return False

    # Unsupported operator: fail-safe
    return False


def apply_action(action: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply a single action to the payload and return a summary dict.
    Supported actions:
      - apply_discount: params {"value": 10, "type": "percent"|"fixed"}
      - mark_out_of_policy: no params
      - set_field: params {"field": "x.y", "value": something}
    """
    name = action.get("action")
    params = action.get("params", {})
    applied = {"action": name, "params": params}

    if name == "apply_discount":
        value = params.get("value")
        dtype = params.get("type", "percent")
        price = payload.get("price")
        if price is None:
            applied["error"] = "no_price_field"
            return applied
        try:
            price = float(price)
            if dtype == "percent":
                new_price = price * (1 - float(value) / 100.0)
            else:
                new_price = price - float(value)
                if new_price < 0:
                    new_price = 0.0
            new_price = round(new_price, 2)
            payload["price_after_discount"] = new_price
            applied["resulting_price"] = new_price
        except Exception as e:
            applied["error"] = f"discount_error:{e}"
        return applied

    if name == "mark_out_of_policy":
        payload.setdefault("policy_flags", {})
        payload["policy_flags"]["out_of_policy_rule"] = True
        return applied

    if name == "set_field":
        field = params.get("field")
        value = params.get("value")
        if field:
            parts = field.split(".")
            cur = payload
            for p in parts[:-1]:
                if p not in cur or not isinstance(cur[p], dict):
                    cur[p] = {}
                cur = cur[p]
            cur[parts[-1]] = value
            applied["set_field"] = field
            applied["set_value"] = value
        else:
            applied["error"] = "no_field"
        return applied

    applied["warning"] = "unknown_action"
    return applied


def execute_rule(rule: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a rule (JSON DSL) against a payload.
    Returns a result dict used by the UI.
    """
    rule_copy = deepcopy(rule) if isinstance(rule, dict) else rule
    payload_copy = deepcopy(payload) if isinstance(payload, dict) else {}

    res: Dict[str, Any] = {
        "matched": False,
        "reason": "",
        "failed_condition": None,
        "actions_applied": [],
        "resulting_payload": deepcopy(payload_copy),
        "explanation": "",
    }

    if not rule_copy or not isinstance(rule_copy, dict):
        res["reason"] = "invalid_rule"
        return res

    conditions = rule_copy.get("conditions", [])
    actions = rule_copy.get("actions", [])

    # Evaluate conditions (AND)
    failed = None
    all_ok = True
    for cond in conditions:
        ok = eval_condition(cond, payload_copy)
        if not ok:
            all_ok = False
            failed = cond
            break

    res["matched"] = bool(all_ok)
    if not all_ok:
        res["reason"] = "conditions_not_met"
        res["failed_condition"] = failed
        res["explanation"] = "One or more rule conditions were not satisfied."
        res["resulting_payload"] = payload_copy
    else:
        # Apply actions
        res["reason"] = "actions_executed"
        applied_list: List[Dict[str, Any]] = []
        for act in actions:
            applied = apply_action(act, payload_copy)
            applied_list.append(applied)
        res["actions_applied"] = applied_list
        res["resulting_payload"] = payload_copy
        act_names = [a.get("action", "") for a in applied_list]
        if act_names:
            res["explanation"] = f"Conditions matched. Actions applied: {', '.join(act_names)}."
        else:
            res["explanation"] = "Conditions matched. No actions applied."

    # ---------------------------
    # STRICT Policy flag augmentation
    # ---------------------------
    applied_actions = res.get("actions_applied", []) or []
    out_of_policy = any(isinstance(a, dict) and a.get("action") == "mark_out_of_policy" for a in applied_actions)

    res["in_policy"] = not out_of_policy
    res["policy_status"] = "in_policy" if res["in_policy"] else "out_of_policy"

    return res


# Minimal wrapper for policy-only usage (returns only in_policy True/False)
def execute_policy(policy_rule: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, bool]:
    """
    Minimal policy executor: returns only {"in_policy": True/False}
    If all conditions match -> policy triggered -> OUT OF POLICY (in_policy=False)
    If any condition fails -> IN POLICY (in_policy=True)
    """
    if not isinstance(policy_rule, dict):
        return {"in_policy": True}
    conditions = policy_rule.get("conditions", [])
    if not conditions:
        return {"in_policy": True}
    for cond in conditions:
        if not eval_condition(cond, payload):
            return {"in_policy": True}
    return {"in_policy": False}
