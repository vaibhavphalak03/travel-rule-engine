# ui/attribute_generator.py
import streamlit as st
import json
from pathlib import Path
import sys
from textwrap import shorten

# Make project root importable
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import executor (synthesize_rule optional)
try:
    from src.zenrules_executor import execute_rule
    SRC_AVAILABLE = True
except Exception as e:
    execute_rule = None
    SRC_AVAILABLE = False
    _import_err = e

st.set_page_config(page_title="Attribute-based Rule Generator", layout="wide")
st.title("Attribute-based Rule Generator")

st.markdown(
    "Use this UI to build a rule by selecting attributes. "
    "It generates a machine-readable JSON rule and can execute it on sample payload."
)

# Load sample payload
def load_sample_payload():
    p = Path("data") / "sample_payload.json"
    if not p.exists():
        return {}
    with p.open("r", encoding="utf8") as fh:
        return json.load(fh)

sample_payload = load_sample_payload()

# Layout
col1, col2 = st.columns([2, 3])

# ---------------------- LEFT SIDE (FORM) ----------------------
with col1:
    st.subheader("Rule metadata")
    rule_name = st.text_input("Rule name (internal)", value="generated_rule")
    priority = st.number_input("Priority", min_value=0, max_value=100, value=1)

    st.subheader("Product attributes")
    product_type = st.selectbox("product_type", ["flight", "hotel", "car", "package", "insurance", "visa"])
    price = st.number_input("price", value=25000.0)
    competitor_price = st.number_input("competitor_price", value=24000.0)
    currency = st.text_input("currency", value="INR")

    st.subheader("Booking / timing")
    booking_window_days = st.number_input("booking_window_days", value=30)
    advance_purchase_hours = st.number_input("advance_purchase_hours", value=720)
    booking_date = st.date_input("booking_date")
    travel_date = st.date_input("travel_date")

    st.subheader("Stay / trip")
    trip_length_days = st.number_input("trip_length_days", value=5)
    min_stay_days = st.number_input("min_stay_days", value=2)
    max_stay_days = st.number_input("max_stay_days", value=10)
    fare_class = st.selectbox("fare_class", ["economy", "premium", "business"])

    st.subheader("Customer & payment")
    loyalty_tier = st.selectbox("loyalty_tier", ["none", "silver", "gold", "platinum"], index=2)
    customer_country = st.text_input("customer_country", value="IN")
    payment_method = st.selectbox("payment_method", ["credit_card", "net_banking", "upi", "wallet"])
    channel = st.selectbox("channel", ["web", "mobile", "agent"])
    customer_segment = st.selectbox("customer_segment", ["retail", "corporate", "student"])

    st.subheader("Supplier & pricing")
    supplier = st.text_input("supplier", value="AirIndia")
    supplier_margin_pct = st.number_input("supplier_margin_pct", value=12.5)
    is_refundable = st.checkbox("is_refundable", value=True)
    min_booking_amount = st.number_input("min_booking_amount", value=5000.0)
    max_discount_pct = st.number_input("max_discount_pct", value=50.0)

    st.subheader("Promotions & blackout")
    promo_code = st.text_input("promo_code", value="WINTER10")
    promo_start_date = st.date_input("promo_start_date")
    promo_end_date = st.date_input("promo_end_date")
    blackout_dates = st.text_input("blackout_dates (comma-separated)", value="2025-12-24,2025-12-25")

    st.subheader("Logistics & extras")
    fare_basis = st.text_input("fare_basis", value="Y123")
    stopovers = st.number_input("stopovers", value=1)
    meal_plan = st.selectbox("meal_plan", ["room_only", "breakfast", "half_board", "full_board"])
    room_type = st.text_input("room_type", value="Deluxe")
    pickup_location = st.text_input("pickup_location", value="Mumbai Airport T2")
    dropoff_location = st.text_input("dropoff_location", value="Pune City Center")
    group_size = st.number_input("group_size", value=3)
    match_price_proof = st.text_input("match_price_proof", value="https://example.com/proof")

    st.subheader("Action")
    action_type = st.selectbox("Action", ["apply_discount", "override_price", "no_action"])
    discount_pct = st.number_input("discount_pct", value=10.0)
    override_price_val = st.number_input("override_price value", value=0.0)

    st.markdown("---")
    gen_rule_btn = st.button("Generate Rule JSON")
    gen_and_exec_btn = st.button("Generate & Execute Rule")

# ---------------------- RIGHT SIDE (OUTPUT) ----------------------
with col2:
    st.subheader("Generated Rule JSON")
    rule_display = st.empty()
    summary_display = st.empty()
    download_display = st.empty()

    exec_expander = st.expander("Execution Result", expanded=False)

# ---------------------- Rule Construction ----------------------
def build_conditions():
    conds = []
    conds.append({"attribute": "product_type", "operator": "==", "value": product_type})
    conds.append({"attribute": "booking_window_days", "operator": ">=", "value": int(booking_window_days)})
    conds.append({"attribute": "min_stay_days", "operator": ">=", "value": int(min_stay_days)})
    conds.append({"attribute": "supplier", "operator": "==", "value": supplier})
    return conds

def build_actions():
    if action_type == "apply_discount":
        return [{"action": "apply_discount", "params": {"value": float(discount_pct), "type": "percent"}}]
    if action_type == "override_price":
        return [{"action": "override_price", "params": {"value": float(override_price_val)}}]
    return []

def build_rule():
    return {
        "rule_id": f"rule_{int(Path().stat().st_mtime)}",
        "name": rule_name,
        "conditions": build_conditions(),
        "actions": build_actions(),
        "priority": int(priority),
        "meta": {"source": "attribute_ui"}
    }

# ---------------------- Button functionality ----------------------
if gen_rule_btn or gen_and_exec_btn:
    rule_json = build_rule()
    rule_text = json.dumps(rule_json, indent=2)

    rule_display.code(rule_text, language="json")

    summary_display.markdown(
        f"**Rule Summary:** product_type={product_type}, booking_window_days={booking_window_days}, discount={discount_pct}"
    )

    download_display.download_button(
        f"Download {rule_json['rule_id']}.json",
        data=rule_text,
        file_name=f"{rule_json['rule_id']}.json",
        mime="application/json"
    )

    if gen_and_exec_btn:
        with exec_expander:
            st.subheader("Execution on Sample Payload")

            if not SRC_AVAILABLE:
                st.error("Executor not available.")
            else:
                try:
                    res = execute_rule(rule_json, sample_payload)
                except Exception as e:
                    st.exception(e)
                    res = None

                st.write(res if res else "Execution failed.")
