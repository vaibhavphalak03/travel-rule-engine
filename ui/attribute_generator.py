# ui/attribute_generator.py
import streamlit as st
import json
from pathlib import Path
import sys
from textwrap import shorten
from datetime import date

# Make project root importable when running from ui/
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Optional imports (executor available if src is importable)
try:
    from src.zenrules_executor import execute_rule
    SRC_EXECUTOR_AVAILABLE = True
except Exception as _e:
    execute_rule = None
    SRC_EXECUTOR_AVAILABLE = False
    _import_err = _e

st.set_page_config(page_title="Attribute-based Rule Generator", layout="wide")
st.title("Attribute-based Rule Generator")
st.markdown("Use this form to build a machine-readable rule (JSON) by selecting attributes. "
            "You can also execute the generated rule on a sample payload.")

# --- helpers ---
def load_sample_payload_file():
    p = Path("data") / "sample_payload.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf8"))
        except Exception:
            pass
    return {}

def coerce_date(d: date):
    try:
        return str(d)
    except Exception:
        return None

# --- Form (left) / Output (right) layout ---
col1, col2 = st.columns([2, 3])

with col1:
    st.subheader("Rule metadata")
    rule_name = st.text_input("Rule name (internal)", value="generated_rule")
    priority = st.number_input("Priority (lower executes first)", value=1, min_value=0, step=1)

    st.subheader("Product attributes")
    product_type = st.selectbox("Product type", options=["flight", "hotel", "car", "package", "insurance", "visa"], index=0)
    price = st.number_input("Price", value=25000.0, step=1.0, format="%.2f")
    competitor_price = st.number_input("Competitor price", value=24000.0, step=1.0, format="%.2f")
    currency = st.text_input("Currency", value="INR")

    st.subheader("Booking / timing")
    booking_window_days = st.number_input("booking_window_days (days lead time)", value=30, min_value=0, step=1)
    advance_purchase_hours = st.number_input("advance_purchase_hours", value=720, min_value=0, step=1)
    booking_date = st.date_input("booking_date", value=date.today())
    travel_date = st.date_input("travel_date", value=date.today())

    st.subheader("Stay / trip")
    trip_length_days = st.number_input("trip_length_days", value=5, min_value=0, step=1)
    min_stay_days = st.number_input("min_stay_days", value=2, min_value=0, step=1)
    max_stay_days = st.number_input("max_stay_days", value=10, min_value=0, step=1)
    fare_class = st.selectbox("fare_class", options=["economy","premium","business"], index=0)

    st.subheader("Customer & payment")
    loyalty_tier = st.selectbox("loyalty_tier", options=["none","silver","gold","platinum"], index=2)
    customer_country = st.text_input("customer_country (ISO)", value="IN")
    payment_method = st.selectbox("payment_method", options=["credit_card","net_banking","upi","wallet"], index=0)
    channel = st.selectbox("channel", options=["web","mobile","agent"], index=0)
    customer_segment = st.selectbox("customer_segment", options=["retail","corporate","student"], index=0)

    st.subheader("Supplier & pricing")
    supplier = st.text_input("supplier", value="AirIndia")
    supplier_margin_pct = st.number_input("supplier_margin_pct", value=12.5, step=0.1, format="%.2f")
    is_refundable = st.checkbox("is_refundable", value=True)
    min_booking_amount = st.number_input("min_booking_amount", value=5000.0, step=1.0, format="%.2f")
    max_discount_pct = st.number_input("max_discount_pct", value=50.0, step=0.1, format="%.2f")

    st.subheader("Promotions & blackout")
    promo_code = st.text_input("promo_code", value="WINTER10")
    promo_start_date = st.date_input("promo_start_date", value=date.today())
    promo_end_date = st.date_input("promo_end_date", value=date.today())
    blackout_dates_text = st.text_input("blackout_dates (comma-separated YYYY-MM-DD)", value="2025-12-24,2025-12-25")

    st.subheader("Logistics & extras")
    fare_basis = st.text_input("fare_basis", value="Y123")
    stopovers = st.number_input("stopovers", value=1, min_value=0, step=1)
    meal_plan = st.selectbox("meal_plan", options=["room_only","breakfast","half_board","full_board"], index=1)
    room_type = st.text_input("room_type", value="Deluxe")
    pickup_location = st.text_input("pickup_location", value="Mumbai Airport T2")
    dropoff_location = st.text_input("dropoff_location", value="Pune City Center")
    group_size = st.number_input("group_size", value=3, min_value=1, step=1)
    match_price_proof = st.text_input("match_price_proof (URL or empty)", value="https://example.com/proof")

    st.markdown("---")
    st.subheader("Action configuration")
    action_type = st.selectbox("Action", options=["apply_discount","override_price","no_action","mark_out_of_policy","price_match_check"], index=0)
    discount_pct = st.number_input("discount_pct (if apply_discount)", value=10.0, min_value=0.0, max_value=100.0, step=0.1)
    override_price_val = st.number_input("override_price (if override_price)", value=0.0, step=1.0, format="%.2f")

    st.markdown("---")
    gen_rule_btn = st.button("Generate Rule from attributes")
    gen_and_exec_btn = st.button("Generate & Execute on sample payload")

# --- right column placeholders ---
with col2:
    st.subheader("Generated Rule (JSON)")
    rule_out_placeholder = st.empty()
    one_line_placeholder = st.empty()
    download_placeholder = st.empty()
    exec_expander = st.expander("Execution / Sample Payload", expanded=False)

# --- helper: build conditions systematically ---
def build_conditions_from_inputs():
    conds = []
    # Basic equality
    conds.append({"attribute": "product_type", "operator": "==", "value": product_type})
    # Booking / timing thresholds
    if booking_window_days:
        conds.append({"attribute": "booking_window_days", "operator": ">=", "value": int(booking_window_days)})
    if advance_purchase_hours:
        conds.append({"attribute": "advance_purchase_hours", "operator": ">=", "value": int(advance_purchase_hours)})
    # Stay/trip
    if trip_length_days:
        conds.append({"attribute": "trip_length_days", "operator": ">=", "value": int(trip_length_days)})
    if min_stay_days:
        conds.append({"attribute": "min_stay_days", "operator": ">=", "value": int(min_stay_days)})
    if max_stay_days:
        conds.append({"attribute": "max_stay_days", "operator": "<=", "value": int(max_stay_days)})
    # Fare class / supplier / promo
    if fare_class:
        conds.append({"attribute": "fare_class", "operator": "==", "value": fare_class})
    if supplier:
        conds.append({"attribute": "supplier", "operator": "==", "value": supplier})
    if promo_code:
        conds.append({"attribute": "promo_code", "operator": "==", "value": promo_code})
    # Loyalty / customer / payment
    if loyalty_tier and loyalty_tier != "none":
        conds.append({"attribute": "loyalty_tier", "operator": "==", "value": loyalty_tier})
    if customer_country:
        conds.append({"attribute": "customer_country", "operator": "==", "value": customer_country})
    if payment_method:
        conds.append({"attribute": "payment_method", "operator": "==", "value": payment_method})
    if channel:
        conds.append({"attribute": "channel", "operator": "==", "value": channel})
    if customer_segment:
        conds.append({"attribute": "customer_segment", "operator": "==", "value": customer_segment})
    # Numeric thresholds
    if supplier_margin_pct is not None:
        conds.append({"attribute": "supplier_margin_pct", "operator": ">=", "value": float(supplier_margin_pct)})
    if min_booking_amount:
        conds.append({"attribute": "min_booking_amount", "operator": "<=", "value": float(min_booking_amount)})
    if max_discount_pct:
        conds.append({"attribute": "max_discount_pct", "operator": ">=", "value": float(max_discount_pct)})
    if group_size:
        conds.append({"attribute": "group_size", "operator": ">=", "value": int(group_size)})
    # Boolean / logistics / misc
    conds.append({"attribute": "is_refundable", "operator": "==", "value": bool(is_refundable)})
    if fare_basis:
        conds.append({"attribute": "fare_basis", "operator": "==", "value": fare_basis})
    if stopovers is not None:
        conds.append({"attribute": "stopovers", "operator": "==", "value": int(stopovers)})
    if meal_plan:
        conds.append({"attribute": "meal_plan", "operator": "==", "value": meal_plan})
    if room_type:
        conds.append({"attribute": "room_type", "operator": "==", "value": room_type})
    if pickup_location:
        conds.append({"attribute": "pickup_location", "operator": "==", "value": pickup_location})
    if dropoff_location:
        conds.append({"attribute": "dropoff_location", "operator": "==", "value": dropoff_location})
    if match_price_proof:
        # require non-empty proof for price match flows
        conds.append({"attribute": "match_price_proof", "operator": "!=", "value": ""})
    # Promo date range conditions (stringified)
    try:
        if promo_start_date:
            conds.append({"attribute": "promo_start_date", "operator": "<=", "value": str(promo_start_date)})
        if promo_end_date:
            conds.append({"attribute": "promo_end_date", "operator": ">=", "value": str(promo_end_date)})
    except Exception:
        pass

    # NOTE: price & competitor_price are usually used for comparisons / actions,
    # not included as default conditions to avoid unintended semantics.
    # If you want price/competitor_price as conditions, uncomment below:
    # conds.append({"attribute":"price","operator":"<=","value":float(price)})
    # conds.append({"attribute":"competitor_price","operator":"<=","value":float(competitor_price)})

    return conds

# --- helper: build actions ---
def build_actions_from_inputs():
    actions = []
    if action_type == "apply_discount":
        actions.append({"action": "apply_discount", "params": {"value": float(discount_pct), "type": "percent"}})
    elif action_type == "override_price":
        actions.append({"action": "override_price", "params": {"value": float(override_price_val)}})
    elif action_type == "mark_out_of_policy":
        actions.append({"action": "mark_out_of_policy", "params": {}})
    elif action_type == "price_match_check":
        actions.append({"action": "price_match_check", "params": {}})
    else:
        actions.append({"action": "no_action", "params": {}})
    return actions

# --- build rule & sample payload ---
def build_rule_and_payload():
    # conditions based on inputs
    conditions = build_conditions_from_inputs()
    actions = build_actions_from_inputs()

    rule = {
        "rule_id": f"rule_{int(Path().resolve().stat().st_ctime)}",
        "name": rule_name or "generated_rule",
        "conditions": conditions,
        "actions": actions,
        "priority": int(priority),
        "meta": {"source": "attribute_ui"}
    }

    # build sample payload containing all fields selected above
    payload = {
        "product_type": product_type,
        "price": float(price),
        "competitor_price": float(competitor_price),
        "currency": currency,
        "booking_window_days": int(booking_window_days),
        "advance_purchase_hours": int(advance_purchase_hours),
        "booking_date": coerce_date(booking_date),
        "travel_date": coerce_date(travel_date),
        "trip_length_days": int(trip_length_days),
        "min_stay_days": int(min_stay_days),
        "max_stay_days": int(max_stay_days),
        "fare_class": fare_class,
        "loyalty_tier": loyalty_tier,
        "customer_country": customer_country,
        "payment_method": payment_method,
        "channel": channel,
        "customer_segment": customer_segment,
        "supplier": supplier,
        "supplier_margin_pct": float(supplier_margin_pct),
        "is_refundable": bool(is_refundable),
        "min_booking_amount": float(min_booking_amount),
        "max_discount_pct": float(max_discount_pct),
        "promo_code": promo_code,
        "promo_start_date": coerce_date(promo_start_date),
        "promo_end_date": coerce_date(promo_end_date),
        "blackout_dates": [d.strip() for d in blackout_dates_text.split(",") if d.strip()],
        "fare_basis": fare_basis,
        "stopovers": int(stopovers),
        "meal_plan": meal_plan,
        "room_type": room_type,
        "pickup_location": pickup_location,
        "dropoff_location": dropoff_location,
        "group_size": int(group_size),
        "match_price_proof": match_price_proof
    }

    return rule, payload

# --- handle button logic ---
if gen_rule_btn or gen_and_exec_btn:
    rule_json, sample_payload = build_rule_and_payload()
    rule_text = json.dumps(rule_json, indent=2, ensure_ascii=False)
    rule_out_placeholder.code(rule_text, language="json")

    # show a short one-line summary
    slots_preview = {
        "product_type": product_type,
        "booking_window_days": booking_window_days,
        "discount_pct": discount_pct
    }
    one_line = f"Rule {rule_json['name']} — {', '.join(f'{k}={v}' for k,v in slots_preview.items())}"
    one_line_placeholder.markdown("**Summary:** " + shorten(one_line, width=200, placeholder="..."))

    # download button
    download_placeholder.download_button(f"Download {rule_json['rule_id']}.json", data=rule_text, file_name=f"{rule_json['rule_id']}.json", mime="application/json")

    # persist generated JSON to data/ for later testing (optional)
    try:
        out_dir = Path("data")
        out_dir.mkdir(exist_ok=True)
        (out_dir / f"{rule_json['rule_id']}.json").write_text(rule_text, encoding="utf8")
    except Exception:
        pass

    # Execute if requested
    if gen_and_exec_btn:
        with exec_expander:
            st.subheader("Execution Result")
            exec_payload = sample_payload or {}
            # if src executor is available, run it
            if not SRC_EXECUTOR_AVAILABLE:
                st.warning("Executor not available in this environment. See import error.")
                st.info("You can still copy the generated JSON and run locally if you install dependencies.")
                st.code(json.dumps(exec_payload, indent=2), language="json")
            else:
                try:
                    res = execute_rule(rule_json, exec_payload)
                except Exception as e:
                    st.exception(f"Error while executing: {e}")
                    res = None

                if res is None:
                    st.write("Execution failed or returned nothing.")
                else:
                    matched = res.get("matched", False)
                    failed = res.get("failed_condition")
                    actions_applied = res.get("actions_applied", [])
                    st.metric("Matched", "Yes" if matched else "No")
                    if not matched and failed:
                        st.write("Failed condition:")
                        st.code(json.dumps(failed, indent=2), language="json")
                    st.write("Actions Applied")
                    st.code(json.dumps(actions_applied, indent=2), language="json")
                    st.write("Resulting payload after actions")
                    st.code(json.dumps(res.get("resulting_payload", exec_payload), indent=2), language="json")

# show sample payload (collapsed)
with exec_expander:
    st.subheader("Sample Payload (constructed from form)")
    try:
        # load from last generation (if available), else build a fresh payload
        _, sample_payload_show = build_rule_and_payload()
        st.code(json.dumps(sample_payload_show, indent=2), language="json")
    except Exception:
        st.write("No sample payload available yet.")
