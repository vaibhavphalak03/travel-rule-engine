# src/entity_patterns.py
# spaCy EntityRuler patterns for travel rule extraction.
# Each pattern tags text spans with an entity label.


PATTERNS = [
    # product types
    {"label": "PRODUCT_TYPE", "pattern": [{"LOWER": "flight"}]},
    {"label": "PRODUCT_TYPE", "pattern": [{"LOWER": "hotel"}]},
    {"label": "PRODUCT_TYPE", "pattern": [{"LOWER": "car"}]},
    {"label": "PRODUCT_TYPE", "pattern": [{"LOWER": "package"}]},
    {"label": "PRODUCT_TYPE", "pattern": [{"LOWER": "insurance"}]},
    {"label": "PRODUCT_TYPE", "pattern": [{"LOWER": "visa"}]},

    # fare class
    {"label": "FARE_CLASS", "pattern": [{"LOWER": "economy"}]},
    {"label": "FARE_CLASS", "pattern": [{"LOWER": "business"}]},
    {"label": "FARE_CLASS", "pattern": [{"LOWER": "first"}]},
    {"label": "FARE_CLASS", "pattern": [{"LOWER": "premium"}]},

    # room type
    {"label": "ROOM_TYPE", "pattern": [{"LOWER": "standard"}]},
    {"label": "ROOM_TYPE", "pattern": [{"LOWER": "deluxe"}]},
    {"label": "ROOM_TYPE", "pattern": [{"LOWER": "suite"}]},

    # loyalty tier
    {"label": "LOYALTY_TIER", "pattern": [{"LOWER": "gold"}]},
    {"label": "LOYALTY_TIER", "pattern": [{"LOWER": "silver"}]},
    {"label": "LOYALTY_TIER", "pattern": [{"LOWER": "platinum"}]},
    {"label": "LOYALTY_TIER", "pattern": [{"LOWER": "none"}]},

    # promo code (alphanumeric tokens)
    {"label": "PROMO_CODE", "pattern": [{"IS_ALPHA": True, "LENGTH": {">=": 2}}, {"IS_DIGIT": False, "OP": "?"}]},

    # price match proof
    {"label": "PRICE_MATCH_PROOF", "pattern": [{"LOWER": "screenshot"}]},
    {"label": "PRICE_MATCH_PROOF", "pattern": [{"LOWER": "invoice"}]},
    {"label": "PRICE_MATCH_PROOF", "pattern": [{"LOWER": "url"}]},
    {"label": "PRICE_MATCH_PROOF", "pattern": [{"LOWER": "link"}]},

    # refundable
    {"label": "REFUNDABLE_FLAG", "pattern": [{"LOWER": "refundable"}]},
    {"label": "REFUNDABLE_FLAG", "pattern": [{"LOWER": "non-refundable"}]},
    {"label": "REFUNDABLE_FLAG", "pattern": [{"LOWER": "non"}, {"LOWER": "refundable"}]},

    # bundle/combo/package
    {"label": "BUNDLE_FLAG", "pattern": [{"LOWER": "combo"}]},
    {"label": "BUNDLE_FLAG", "pattern": [{"LOWER": "bundle"}]},
    {"label": "BUNDLE_FLAG", "pattern": [{"LOWER": "package"}]},

    # booking window days: "30 days before", "at least 30 days"
    {"label": "BOOKING_WINDOW_DAYS", "pattern": [{"LIKE_NUM": True}, {"LOWER": "days"}, {"LOWER": "before"}]},
    {"label": "BOOKING_WINDOW_DAYS", "pattern": [{"LOWER": "at"}, {"LOWER": "least"}, {"LIKE_NUM": True}, {"LOWER": "days"}]},
    {"label": "BOOKING_WINDOW_DAYS", "pattern": [{"LIKE_NUM": True}, {"LOWER": "or"}, {"LOWER": "more"}, {"LOWER": "days"}]},

    # length of stay: "3 nights", "stay 7 nights"
    {"label": "LENGTH_OF_STAY", "pattern": [{"LIKE_NUM": True}, {"LOWER": {"IN": ["night","nights"]}}]},
    {"label": "LENGTH_OF_STAY", "pattern": [{"LOWER": "stay"}, {"LIKE_NUM": True}, {"LOWER": {"IN": ["night","nights"]}}]},

    # pax / group count
    {"label": "PAX_COUNT", "pattern": [{"LIKE_NUM": True}, {"LOWER": {"IN": ["passenger","passengers","pax","people","persons"]}}]},
    {"label": "GROUP", "pattern": [{"LOWER": "group"}]},

    # payment methods
    {"label": "PAYMENT_METHOD", "pattern": [{"LOWER": "upi"}]},
    {"label": "PAYMENT_METHOD", "pattern": [{"LOWER": "card"}]},
    {"label": "PAYMENT_METHOD", "pattern": [{"LOWER": "netbanking"}]},

    # promo eligibility flags
    {"label": "PROMO_ELIGIBILITY", "pattern": [{"LOWER": "student"}]},
    {"label": "PROMO_ELIGIBILITY", "pattern": [{"LOWER": "first_booking"}]},
    {"label": "PROMO_ELIGIBILITY", "pattern": [{"LOWER": "military"}]},

    # supplier (common examples)
    {"label": "SUPPLIER", "pattern": [{"LOWER": "airindia"}]},
    {"label": "SUPPLIER", "pattern": [{"LOWER": "oyo"}]},
    {"label": "SUPPLIER", "pattern": [{"LOWER": "hertz"}]},

    # season
    {"label": "TRAVEL_SEASON", "pattern": [{"LOWER": "peak"}]},
    {"label": "TRAVEL_SEASON", "pattern": [{"LOWER": "off-peak"}]},
    {"label": "TRAVEL_SEASON", "pattern": [{"LOWER": "holiday"}]},

    # age group
    {"label": "AGE_GROUP", "pattern": [{"LOWER": "child"}]},
    {"label": "AGE_GROUP", "pattern": [{"LOWER": "infant"}]},
    {"label": "AGE_GROUP", "pattern": [{"LOWER": "adult"}]},
    {"label": "AGE_GROUP", "pattern": [{"LOWER": "senior"}]},

    # time window hours (e.g., within 24 hours)
    {"label": "TIME_WINDOW_HOURS", "pattern": [{"LOWER": "within"}, {"LIKE_NUM": True}, {"LOWER": {"IN": ["hour","hours"]}}]},
    {"label": "TIME_WINDOW_HOURS", "pattern": [{"LIKE_NUM": True}, {"LOWER": {"IN": ["hour","hours"]}}, {"LOWER": "after"}]},

    # discount value (percent)
    {"label": "DISCOUNT_PCT", "pattern": [{"LIKE_NUM": True}, {"TEXT": "%"}]},
    {"label": "DISCOUNT_PCT", "pattern": [{"LIKE_NUM": True}, {"LOWER": "percent"}]},

    # competitor / competitor price mentions
    {"label": "COMPETITOR_PRICE", "pattern": [{"LOWER": "competitor"}, {"LOWER": "price"}]},
    {"label": "COMPETITOR_PRICE", "pattern": [{"LOWER": "competitor's"}, {"LOWER": "price"}]},

    # blackout date simple match (YYYY-MM-DD format)
    {"label": "BLACKOUT_DATE", "pattern": [{"SHAPE": "dddd-dd-dd"}]},
]
