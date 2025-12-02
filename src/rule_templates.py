# src/rule_templates.py
# Simple template definitions used by the generator.
# Each template has: id, name, conds (list of attribute keys), and action (action key)

TEMPLATES = [
    {"id": "t1", "name": "product_class_discount", "conds": ["product_type", "fare_class"], "action": "apply_discount"},
    {"id": "t2", "name": "booking_window_discount", "conds": ["product_type", "booking_window_days"], "action": "apply_discount"},
    {"id": "t3", "name": "loyalty_discount", "conds": ["product_type", "loyalty_tier"], "action": "apply_discount"},
    {"id": "t4", "name": "bundle_combo_discount", "conds": ["itinerary_components", "bundle_flag"], "action": "apply_discount"},
    {"id": "t5", "name": "price_match_policy", "conds": ["price_match_proof", "time_since_booking_hours", "competitor_price"], "action": "match_price"},
    {"id": "t6", "name": "blackout_exclusion", "conds": ["travel_date"], "action": "block_promo"},
    {"id": "t7", "name": "min_stay_perk", "conds": ["length_of_stay_days"], "action": "add_service"},
    {"id": "t8", "name": "cancellation_policy", "conds": ["refundable_flag", "booking_window_days"], "action": "set_cancellation_penalty"},
    {"id": "t9", "name": "supplier_commission_override", "conds": ["supplier", "supplier_markup_pct"], "action": "set_commission"},
    {"id": "t10", "name": "promo_code_eligibility", "conds": ["promo_code", "promo_eligibility_flags"], "action": "apply_discount"},
    {"id": "t11", "name": "manual_override", "conds": ["channel", "manual_override_allowed"], "action": "allow_manual_override"},
    {"id": "t12", "name": "insurance_requirement", "conds": ["length_of_stay_days", "destination_country"], "action": "require_insurance"},
    {"id": "t13", "name": "payment_method_incentive", "conds": ["payment_method"], "action": "apply_discount"},
    {"id": "t14", "name": "group_booking_discount", "conds": ["group_booking_flag", "pax_count"], "action": "apply_discount"},
    {"id": "t15", "name": "child_infant_pricing", "conds": ["customer_age_group"], "action": "apply_discount"},
    {"id": "t16", "name": "seasonal_markup", "conds": ["travel_season"], "action": "apply_markup"},
    {"id": "t17", "name": "tax_override", "conds": ["product_type", "channel"], "action": "set_tax_pct"},
    {"id": "t18", "name": "promo_cap_precedence", "conds": ["promo_eligibility_flags", "max_discount_allowed"], "action": "apply_discount"},
    {"id": "t19", "name": "blackout_min_stay_conflict", "conds": ["blackout_dates", "length_of_stay_days"], "action": "block_promo"},
    {"id": "t20", "name": "require_docs_by_destination", "conds": ["destination_country", "customer_country"], "action": "require_doc"}
]
