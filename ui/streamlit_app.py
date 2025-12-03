# ui/streamlit_app.py
"""
Streamlit app:
 - Tab 1: NL -> JSON rule generation + execution
 - Tab 2: Minimal Policy Check (IN / OUT only)

This version:
 - Fixes import path issues by adding project root to sys.path
 - Initializes session_state keys before widget creation (avoids Streamlit errors)
 - Provides safe stubs if src modules fail to import (so UI remains usable)
"""

from pathlib import Path
import sys
import json
from textwrap import shorten

# ------------------------------
# Ensure project root is importable
# ------------------------------
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# ------------------------------
# Try importing actual modules from src/
# ------------------------------
SRC_AVAILABLE = False
_import_err = None

try:
    from src.synthesizer import synthesize_rule
    from src.zenrules_executor import execute_rule, execute_policy
    SRC_AVAILABLE = True
except Exception as e:
    _import_err = e
    SRC_AVAILABLE = False
    # We'll define safe fallback stubs below

# ------------------------------
# Helpers & sample payload
# ------------------------------
def load_sample_payload():
    p = Path("data") / "sample_payload.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf8"))
        except Exception:
            pass
    # Minimal sample payload with common fields
    return {
        "product_type": "flight",
        "price": 200.0,
        "competitor_price": 180.0,
        "booking_window_days": 30,
        "loyalty_tier": "gold",
        "customer_country": "IN",
        "is_cheapest_direct": True,
        "hotel_class": 3
    }

sample_payload = load_sample_payload()

# ------------------------------
# Safe fallback implementations (used only when SRC_AVAILABLE == False)
# ------------------------------
if not SRC_AVAILABLE:
    def synthesize_rule(text):
        # minimal fake response so UI remains demo-capable
        return {
            "intent": "booking_window_discount",
            "slots": {"discount_pct": 10, "booking_window_days": 30},
            "rule": {
                "rule_id": "rule_demo",
                "name": "booking_window_discount",
                "conditions": [
                    {"attribute": "product_type", "operator": "==", "value": "flight"},
                    {"attribute": "booking_window_days", "operator": ">=", "value": 30}
                ],
                "actions": [{"action": "apply_discount", "params": {"value": 10, "type": "percent"}}],
                "priority": 1,
                "meta": {"source": "stub"}
            }
        }

    def execute_rule(rule, payload):
        # Minimal executor: test simple operators and simulate discount application
        conds = rule.get("conditions", [])
        matched = True
        failed_condition = None

        for c in conds:
            attr = c.get("attribute")
            op = c.get("operator")
            val = c.get("value")
            pv = payload.get(attr)
            ok = False
            try:
                if op == "==":
                    ok = (pv == val)
                elif op == ">=":
                    ok = float(pv) >= float(val)
                elif op == "<=":
                    ok = float(pv) <= float(val)
                else:
                    ok = False
            except Exception:
                ok = False

            if not ok:
                matched = False
                failed_condition = c
                break

        actions_applied = []
        resulting = dict(payload)
        if matched:
            for a in rule.get("actions", []):
                if a.get("action") == "apply_discount":
                    v = a.get("params", {}).get("value", 0)
                    if a.get("params", {}).get("type") == "percent":
                        try:
                            resulting_price = float(resulting.get("price", 0)) * (1 - float(v)/100.0)
                        except Exception:
                            resulting_price = resulting.get("price", 0)
                        resulting["price_after_discount"] = round(resulting_price, 2)
                    else:
                        resulting["price_after_discount"] = v
                    actions_applied.append(a)

        # simple policy inference: if action mark_out_of_policy present -> out_of_policy
        in_policy = not any(a.get("action") == "mark_out_of_policy" for a in rule.get("actions", []))

        return {
            "matched": matched,
            "reason": "actions_executed" if matched else "conditions_not_met",
            "failed_condition": failed_condition,
            "actions_applied": actions_applied,
            "resulting_payload": resulting,
            "in_policy": in_policy,
            "policy_status": "in_policy" if in_policy else "out_of_policy",
            "explanation": ("The rule matched; actions applied." if matched else "One or more rule conditions were not satisfied.")
        }

    def execute_policy(policy_rule, payload):
        # policy_rule is assumed in same JSON shape: {"conditions": [...]}
        # reuse execute_rule-like logic but no actions; only returns in_policy boolean
        conds = policy_rule.get("conditions", [])
        for c in conds:
            attr = c.get("attribute")
            op = c.get("operator")
            val = c.get("value")
            pv = payload.get(attr)
            try:
                if op == "==":
                    if not (pv == val):
                        return {"in_policy": True}  # condition not met -> policy not triggered -> IN POLICY
                elif op == ">":
                    if not (float(pv) > float(val)):
                        return {"in_policy": True}
                elif op == "<":
                    if not (float(pv) < float(val)):
                        return {"in_policy": True}
                elif op == ">=":
                    if not (float(pv) >= float(val)):
                        return {"in_policy": True}
                elif op == "<=":
                    if not (float(pv) <= float(val)):
                        return {"in_policy": True}
                else:
                    # unknown operator -> treat as IN POLICY (safe default)
                    return {"in_policy": True}
            except Exception:
                return {"in_policy": True}
        # If all conditions matched -> policy triggered -> OUT OF POLICY
        return {"in_policy": False}

# ------------------------------
# Built-in policies
# ------------------------------
BUILTIN_POLICIES = {
    "not_cheapest_direct": {
        "rule_id": "policy_001",
        "name": "not_cheapest_direct",
        "conditions": [
            {"attribute": "is_cheapest_direct", "operator": "==", "value": False}
        ],
        "actions": [{"action": "mark_out_of_policy"}]
    },
    "no_luxury_hotel_for_juniors": {
        "rule_id": "policy_002",
        "name": "no_luxury_hotel_for_juniors",
        "conditions": [
            {"attribute": "loyalty_tier", "operator": "==", "value": "basic"},
            {"attribute": "hotel_class", "operator": ">", "value": 4}
        ],
        "actions": [{"action": "mark_out_of_policy"}]
    }
}

# ------------------------------
# Streamlit UI
# ------------------------------
import streamlit as st

st.set_page_config(page_title="NL → JSON & Policy Demo", layout="wide")
st.title("NL → JSON Rule Synthesizer  —  Policy Checker")

# Initialize session_state defaults BEFORE widgets are created
if "last_generated_rule" not in st.session_state:
    st.session_state["last_generated_rule"] = None
if "policy_payload_text" not in st.session_state:
    st.session_state["policy_payload_text"] = json.dumps(sample_payload, indent=2)
if "builtin_policy_selected" not in st.session_state:
    st.session_state["builtin_policy_selected"] = next(iter(BUILTIN_POLICIES.keys()))

# Tabs
tab1, tab2 = st.tabs(["NL → JSON", "Policy Check"])

# ----------------------------
# Tab 1: NL -> JSON generation
# ----------------------------
with tab1:
    st.header("Natural Language → JSON rule")
    if not SRC_AVAILABLE:
        st.error("Project imports failed. Synthesizer or executor not fully available.")
        st.write("Import error (short):", str(_import_err))
        st.info("Fix: run Streamlit from project root with venv activated and PYTHONPATH set, or install requirements.")
        st.code("cd path/to/project && .\\.venv\\Scripts\\Activate.ps1 && $env:PYTHONPATH = Get-Location && streamlit run ui/streamlit_app.py", language="powershell")

    st.write("Type a rule in plain English and click **Generate Rule**.")

    col1, col2 = st.columns([2, 3])
    with col1:
        nl_input = st.text_area("Enter rule (English)",
                                value="Give 10% discount on flights booked at least 20 days before travel.",
                                height=140)
        generate_btn = st.button("Generate Rule")
        show_generated_json = st.checkbox("Show generated rule JSON", value=False)
    with col2:
        json_placeholder = st.empty()
        summary_placeholder = st.empty()
        exec_expander = st.expander("Execution Details (expand)", expanded=False)

    if generate_btn:
        if not SRC_AVAILABLE:
            st.warning("Synthesizer not available. Using demo stub output.")
            out = synthesize_rule(nl_input)
        else:
            try:
                out = synthesize_rule(nl_input)
            except Exception as e:
                st.exception(f"Synthesis error: {e}")
                out = None

        if out is None:
            json_placeholder.code("Error: synthesizer failed or not available.", language="text")
            summary_placeholder.info("Synthesizer not available.")
        else:
            rule = out.get("rule", out) if isinstance(out, dict) else out
            st.session_state["last_generated_rule"] = rule
            intent = out.get("intent", "")
            slots = out.get("slots", {})

            rule_json_text = json.dumps(rule, indent=2, ensure_ascii=False)
            if show_generated_json:
                json_placeholder.code(rule_json_text, language="json")
            else:
                json_placeholder.info(f"Rule ID: **{rule.get('rule_id','-')}** | Name: **{rule.get('name','-')}**")

            one_line = f"This rule ({rule.get('name')}) will apply when conditions match. Slots: {', '.join(f'{k}={v}' for k,v in list(slots.items())[:4])}"
            summary_placeholder.success(shorten(one_line, width=220, placeholder="..."))

            with exec_expander:
                st.subheader("Predicted Intent & Slots")
                st.code(json.dumps({"intent": intent, "slots": slots}, indent=2), language="json")
                st.subheader("Sample Payload")
                st.code(json.dumps(sample_payload, indent=2), language="json")

                custom_payload_text = st.text_area("Custom payload (optional)", value=json.dumps(sample_payload, indent=2), height=200, key="exec_custom_payload")

                try:
                    exec_payload = json.loads(custom_payload_text)
                except Exception as e:
                    st.error(f"Invalid JSON payload: {e}")
                    exec_payload = sample_payload

                if st.button("Execute rule on payload"):
                    if not SRC_AVAILABLE:
                        st.warning("Executor not available; using demo executor.")
                        res = execute_rule(rule, exec_payload)
                    else:
                        try:
                            res = execute_rule(rule, exec_payload)
                        except Exception as e:
                            st.exception(f"Execution error: {e}")
                            res = None

                    if res is None:
                        st.write("Execution failed.")
                    else:
                        matched = res.get("matched", False)
                        in_policy = res.get("in_policy", None)
                        failed = res.get("failed_condition")

                        st.metric("Matched", "Yes" if matched else "No")
                        if in_policy is not None:
                            if in_policy:
                                st.success("Policy: ✅ IN POLICY")
                            else:
                                st.error("Policy: ❌ OUT OF POLICY")

                        if not matched and failed:
                            attr = failed.get("attribute")
                            op = failed.get("operator")
                            val = failed.get("value")
                            st.write(f"Failed condition: `{attr} {op} {val}`")
                        elif matched:
                            st.write("Conditions matched; actions applied.")

                        with st.expander("Show full execution JSON (debug)", expanded=False):
                            st.code(json.dumps(res, indent=2, ensure_ascii=False), language="json")

# -----------------------------------------
# Tab 2: Minimal Policy Check (clean)
# -----------------------------------------
with tab2:
    st.header("Minimal Policy Check (IN / OUT only)")
    st.write("Choose a built-in policy or use the last generated rule as the policy. The payload is editable; click Check Policy to evaluate.")

    source = st.radio("Policy source:", options=["Built-in policy", "Use last generated rule"], index=0)

    selected_policy = None
    if source == "Built-in policy":
        builtin_keys = list(BUILTIN_POLICIES.keys())
        sel = st.selectbox("Choose built-in policy", builtin_keys, index=builtin_keys.index(st.session_state.get("builtin_policy_selected", builtin_keys[0])))
        st.session_state["builtin_policy_selected"] = sel
        selected_policy = BUILTIN_POLICIES.get(sel)
    else:
        last = st.session_state.get("last_generated_rule")
        if last:
            selected_policy = last
            st.info("Using last generated rule as the policy.")
            if st.checkbox("Show selected policy JSON (optional)"):
                st.code(json.dumps(selected_policy, indent=2, ensure_ascii=False), language="json")
        else:
            st.warning("No generated rule found. Generate one in NL → JSON tab first.")

    # Controlled payload textarea using session_state
    policy_payload_text = st.text_area("Payload JSON (edit if needed)", value=st.session_state["policy_payload_text"], height=240, key="policy_payload_text")

    if st.button("Check Policy"):
        if not SRC_AVAILABLE:
            st.warning("Executor import error (using demo policy checker).")
            try:
                payload = json.loads(st.session_state["policy_payload_text"])
            except Exception:
                st.error("Invalid JSON payload. Using sample payload.")
                payload = sample_payload
            res = execute_policy(selected_policy, payload)
        else:
            try:
                payload = json.loads(st.session_state["policy_payload_text"])
            except Exception:
                st.error("Invalid JSON payload. Using sample payload.")
                payload = sample_payload
            try:
                res = execute_policy(selected_policy, payload)
            except Exception as e:
                st.exception(f"Policy execution error: {e}")
                res = {"in_policy": True}

        in_policy = res.get("in_policy", True)
        if in_policy:
            st.success("✅ IN POLICY")
        else:
            st.error("❌ OUT OF POLICY")

    st.caption("This tab intentionally only shows IN / OUT for a clean demo.")
