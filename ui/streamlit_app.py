# ui/streamlit_app.py
"""
Streamlit app:
 - Tab 1: NL -> JSON rule generation + execution
 - Tab 2: Minimal Policy Check (IN / OUT only)

This version: quick-fill buttons removed (as requested). Everything else unchanged.
"""

import streamlit as st
import json
from pathlib import Path
from textwrap import shorten

# Try imports
try:
    from src.synthesizer import synthesize_rule
    from src.zenrules_executor import execute_rule, execute_policy
    SRC_AVAILABLE = True
except Exception as e:
    synthesize_rule = None
    execute_rule = None
    execute_policy = None
    SRC_AVAILABLE = False
    _import_err = e

st.set_page_config(page_title="NL → JSON & Policy Demo", layout="wide")
st.title("NL → JSON Rule Synthesizer  —  Policy Checker")

# -------------------------
# Helpers
# -------------------------
def load_sample_payload():
    p = Path("data") / "sample_payload.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf8"))
        except Exception:
            pass
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

# Built-in policies
BUILTIN_POLICIES = {
    "not_cheapest_direct": {
        "rule_id": "policy_001",
        "name": "not_cheapest_direct",
        "conditions": [
            {"attribute": "is_cheapest_direct", "operator": "==", "value": False}
        ]
    },
    "no_luxury_hotel_for_juniors": {
        "rule_id": "policy_002",
        "name": "no_luxury_hotel_for_juniors",
        "conditions": [
            {"attribute": "loyalty_tier", "operator": "==", "value": "basic"},
            {"attribute": "hotel_class", "operator": ">", "value": 4}
        ]
    }
}

# session_state defaults
if "last_generated_rule" not in st.session_state:
    st.session_state["last_generated_rule"] = None
if "policy_payload_text" not in st.session_state:
    st.session_state["policy_payload_text"] = json.dumps(load_sample_payload(), indent=2)
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
        st.error(f"Project imports failed: {_import_err}")
        st.info("Run Streamlit from project root with PYTHONPATH set or install the package in the venv.")
    st.write("Type a rule in plain English and click Generate Rule.")

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
            st.warning("Synthesizer not available.")
            out = None
        else:
            try:
                out = synthesize_rule(nl_input)
            except Exception as e:
                st.exception(f"Synthesis error: {e}")
                out = None

        if out is None:
            json_placeholder.code("Error: synthesizer failed or not available.", language="text")
        else:
            # store last generated rule
            rule = out.get("rule", out)
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
                st.code(json.dumps(load_sample_payload(), indent=2), language="json")

                # editable payload for execution (local, independent of policy tab)
                custom_payload_text = st.text_area("Custom payload (optional)", value=json.dumps(load_sample_payload(), indent=2), height=200, key="exec_custom_payload")

                try:
                    exec_payload = json.loads(custom_payload_text)
                except Exception as e:
                    st.error(f"Invalid JSON payload: {e}")
                    exec_payload = load_sample_payload()

                if st.button("Execute rule on payload"):
                    if not SRC_AVAILABLE:
                        st.warning("Executor not available.")
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

    # radio: source
    source = st.radio("Policy source:", options=["Built-in policy", "Use last generated rule"], index=0)

    selected_policy = None
    # Built-in selection always shown and uses session_state default
    if source == "Built-in policy":
        builtin_keys = list(BUILTIN_POLICIES.keys())
        if builtin_keys:
            idx = builtin_keys.index(st.session_state.get("builtin_policy_selected", builtin_keys[0])) if st.session_state.get("builtin_policy_selected") in builtin_keys else 0
            sel = st.selectbox("Choose built-in policy", builtin_keys, index=idx, key="builtin_choice_widget")
            st.session_state["builtin_policy_selected"] = sel
            selected_policy = BUILTIN_POLICIES.get(sel)
        else:
            st.error("No built-in policies defined.")
    else:
        last = st.session_state.get("last_generated_rule")
        if last:
            selected_policy = last
            st.info("Using last generated rule as the policy.")
            if st.checkbox("Show selected policy JSON (optional)"):
                st.code(json.dumps(selected_policy, indent=2, ensure_ascii=False), language="json")
        else:
            st.warning("No generated rule found. Generate one in NL → JSON tab first.")

    st.subheader("Payload for policy check")
    # Controlled payload textarea using session_state
    payload_text = st.text_area("Payload JSON (edit if needed)", value=st.session_state["policy_payload_text"], height=240, key="policy_payload_text")

    # Check policy
    if st.button("Check Policy"):
        if not SRC_AVAILABLE:
            st.error(f"Executor import error: {_import_err}")
        else:
            try:
                payload = json.loads(st.session_state["policy_payload_text"])
            except Exception:
                st.error("Invalid JSON payload. Using default sample payload.")
                payload = load_sample_payload()

            if selected_policy is None:
                st.error("No policy selected. Choose a built-in policy or generate one.")
            else:
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
