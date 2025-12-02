# src/generator_with_nl.py
import json
import random
from datetime import datetime, timezone
from src.rule_templates import TEMPLATES

OUT_FILE = "data/generated_rules.jsonl"

VALUE_POOLS = {
    "product_type": ["flight", "hotel", "car", "package", "insurance", "visa"],
    "fare_class": ["economy", "premium", "business", "first"],
    "room_type": ["standard", "deluxe", "suite"],
    "loyalty_tier": ["none", "silver", "gold", "platinum"],
    "bundle_flag": [True, False],
    "channel": ["online", "app", "agent", "retail"],
    "price_match_proof": ["none", "url", "screenshot", "invoice"],
    "promo_eligibility_flags": [["first_booking"], ["student"], ["military"], []]
}

# small synonyms and phrasings for paraphrase
PHRASES = {
    "give": ["give", "offer", "apply"],
    "discount_pct": ["{v}% off", "{v}% discount", "a {v}% discount"],
    "booked_before": ["booked at least {v} days before", "booked {v} or more days in advance", "if booking is done {v}+ days before travel"],
    "price_match": ["if competitor price is lower", "when a competitor offers a lower price"],
    "bundle": ["when flight and hotel booked together", "for flight+hotel combo", "when booked as a package"]
}

def make_condition(attr):
    if attr in VALUE_POOLS:
        v = random.choice(VALUE_POOLS[attr])
        op = "contains" if isinstance(v, list) else "=="
        return {"attribute": attr, "operator": op, "value": v}

    if attr == "booking_window_days":
        return {"attribute": attr, "operator": ">=", "value": random.choice([0, 3, 7, 14, 30, 60])}

    if attr == "length_of_stay_days":
        return {"attribute": attr, "operator": ">=", "value": random.choice([1, 2, 3, 4, 7, 14])}

    if attr == "time_since_booking_hours":
        return {"attribute": attr, "operator": "<=", "value": random.choice([12, 24, 48])}

    if attr == "pax_count":
        return {"attribute": attr, "operator": ">=", "value": random.choice([1, 2, 4, 6, 10])}

    if attr == "supplier_markup_pct":
        return {"attribute": attr, "operator": "<", "value": random.choice([3, 5, 8, 12])}

    if attr == "competitor_price":
        return {"attribute": attr, "operator": "<", "value": "our_price"}

    if attr == "blackout_dates":
        return {"attribute": attr, "operator": "in", "value": ["2025-12-24", "2025-12-31"]}

    if attr == "travel_date":
        return {"attribute": attr, "operator": "in", "value": ["2025-12-24", "2025-12-31"]}

    if attr == "refundable_flag":
        return {"attribute": attr, "operator": "==", "value": random.choice(["refundable", "non-refundable"])}

    return {"attribute": attr, "operator": "present", "value": True}

def render_nl(template, rule):
    """
    Very small template-to-NL renderer. It inspects the template name and rule conditions
    and returns a human-friendly sentence. Not perfect but consistent.
    """
    name = template["name"]
    conds = {c["attribute"]: c for c in rule["conditions"]}

    # helper to pick phrase
    def p(key, **kw):
        return random.choice(PHRASES.get(key, ["{v}"])).format(**kw)

    # Example renderers for common templates
    if "booking_window" in name:
        bw = conds.get("booking_window_days", {}).get("value", 0)
        return f"{p('give',)} {p('discount_pct', v=rule['actions'][0]['params'].get('value','10'))} on {rule['product_type']} booked {p('booked_before', v=bw)}."
    if "loyalty" in name or "loyal" in name:
        tier = conds.get("loyalty_tier", {}).get("value", "gold")
        return f"{p('give')} a {rule['actions'][0]['params'].get('value',10)}% discount for {tier} members on {rule['product_type']}."
    if "bundle" in name or "combo" in name:
        return f"{p('give')} {p('discount_pct', v=rule['actions'][0]['params'].get('value',10))} {p('bundle')}."
    if "price_match" in name:
        return f"{p('price_match').capitalize()}: we will {p('give')} to match competitor price if proof is provided within {conds.get('time_since_booking_hours',{}).get('value',24)} hours."
    if "blackout" in name:
        dates = conds.get("travel_date",{}).get("value", ["dates"])
        return f"No discounts available for stays that include {', '.join(dates)}."
    if "min_stay" in name or "stay" in name:
        days = conds.get("length_of_stay_days",{}).get("value",1)
        return f"If stay is {days} nights or more, include free breakfast with the hotel booking."
    if "cancellation" in name:
        ref = conds.get("refundable_flag",{}).get("value","non-refundable")
        penalty = rule['actions'][0]['params'].get('value',100)
        return f"If booking is {ref}, cancellation penalty is {penalty}%."
    # fallback generic
    return f"{p('give')} {p('discount_pct', v=rule['actions'][0]['params'].get('value',10))} on {rule['product_type']} when conditions match."

def synth_rule_with_nl(template, idx):
    conds = [make_condition(a) for a in template["conds"]]
    action_type = template["action"]
    if action_type == "apply_discount":
        params = {"type": "percent", "value": random.choice([5, 8, 10, 12, 15])}
    elif action_type == "match_price":
        params = {"source": "competitor_price"}
    elif action_type == "add_service":
        params = {"service": "breakfast", "charge": 0}
    elif action_type == "set_cancellation_penalty":
        params = {"type": "percent", "value": random.choice([25, 50, 100])}
    elif action_type == "set_commission":
        params = {"type": "percent", "value": random.choice([5, 7, 10])}
    elif action_type == "allow_manual_override":
        params = {"max_override_percent": random.choice([3, 5, 7])}
    elif action_type == "require_insurance":
        params = {"level": "standard"}
    elif action_type == "require_doc":
        params = {"doc": "visa_application", "service": "visa"}
    elif action_type == "apply_markup":
        params = {"type": "percent", "value": random.choice([5, 8, 10])}
    elif action_type == "block_promo":
        params = {"reason": "blackout"}
    else:
        params = {}

    rule = {
        "rule_id": f"R{idx:05d}",
        "name": template["name"],
        "product_type": random.choice(VALUE_POOLS["product_type"]),
        "conditions": conds,
        "actions": [{"action": action_type, "params": params}],
        "priority": random.randint(1, 50),
        "meta": {"source": "synth", "created_by": "vaibhav", "created_at": datetime.now(timezone.utc).isoformat()}
    }
    # produce NL
    nl = render_nl(template, rule)
    return {"nl": nl, **rule}

def generate(n=1000):
    out = []
    for i in range(n):
        t = random.choice(TEMPLATES)
        r = synth_rule_with_nl(t, i + 1)
        out.append(r)
    with open(OUT_FILE, "w", encoding="utf8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Generated {len(out)} NL+JSON rules -> {OUT_FILE}")

if __name__ == "__main__":
    generate(1000)
