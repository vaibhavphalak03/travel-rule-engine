# scripts/train_intent_quick.py
"""
Quick intent trainer — trains a LogisticRegression classifier using small synthetic
and/or existing training data. Saves model to models/intent_clf.joblib
"""
from pathlib import Path
import json
import random
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "models"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_MODEL = OUT_DIR / "intent_clf.joblib"

# If you have an intent training file, use it. Format: one json per line {"text": "...", "intent": "..."}
INTENT_FILE = DATA_DIR / "intent_training.jsonl"

texts, labels = [], []

if INTENT_FILE.exists():
    print("Loading training data from", INTENT_FILE)
    with INTENT_FILE.open("r", encoding="utf8") as fh:
        for ln in fh:
            try:
                j = json.loads(ln)
                texts.append(j.get("text",""))
                labels.append(j.get("intent","generic_rule"))
            except Exception:
                pass

if len(texts) < 50:
    # Synthetic augmentation: create patterns for key intents
    print("Generating synthetic training data (augmenting)...")
    templates = [
        ("Give {pct}% discount on {product} booked at least {days} days before travel.", "booking_window_discount"),
        ("Apply {pct}% discount on {product} when booked {days} days ahead.", "booking_window_discount"),
        ("Match competitor price if proof provided.", "price_match_policy"),
        ("If customer sends proof of a lower price, match it.", "price_match_policy"),
        ("No discounts for stays shorter than {n} nights.", "blackout_min_stay_conflict"),
        ("Do not allow discounts for stays under {n} nights.", "blackout_min_stay_conflict"),
        ("Apply {pct}% surcharge on {fare} class bookings.", "fare_class_surcharge"),
        ("Apply surcharge of {pct}% for {fare} class.", "fare_class_surcharge"),
        ("Apply promo {code} only on bookings above {amt}.", "promo_code_eligibility"),
        ("Override supplier commission for supplier {supplier}.", "supplier_commission_override"),
        ("Manual override: allow discount {pct}% for this request.", "manual_override"),
    ]
    products = ["flights", "hotels", "cars", "package", "insurance", "visa"]
    fares = ["economy","premium","business"]
    suppliers = ["AirIndia","SupplierA","SupplierB"]
    promo_codes = ["WINTER10","SUMMER5","BLACKFRI"]
    for tpl, intent in templates:
        for n in range(120):
            text = tpl.format(
                pct=random.choice([5,10,15,20]),
                product=random.choice(products),
                days=random.choice([7,14,21,30,45]),
                n=random.choice([1,2,3]),
                fare=random.choice(fares),
                code=random.choice(promo_codes),
                amt=random.choice([1000,3000,5000,10000]),
                supplier=random.choice(suppliers)
            )
            texts.append(text)
            labels.append(intent)

# final sanity
if len(texts) < 10:
    raise SystemExit("Not enough data to train intent classifier.")

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(texts, labels, test_size=0.15, random_state=42, stratify=labels)

print("Training intent classifier (TF-IDF + LogisticRegression)...")
clf = make_pipeline(
    TfidfVectorizer(ngram_range=(1,2), max_features=5000),
    LogisticRegression(max_iter=400, solver="liblinear")
)
clf.fit(X_train, y_train)

print("Evaluation:")
y_pred = clf.predict(X_test)
print(classification_report(y_test, y_pred, zero_division=0))

joblib.dump(clf, OUT_MODEL)
print("Saved intent model to:", OUT_MODEL)
