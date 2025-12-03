# scripts/create_enhanced_crf.py
"""
Create an enhanced, deterministic CRF-like object that implements .predict(list_of_tokens_lists)
and returns BIO-like tags. Saved as models/crf_model.joblib.
This is fast, deterministic, and avoids native compilation issues.
"""
import re
from pathlib import Path
import joblib

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "models"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "crf_model.joblib"

class EnhancedDummyCRF:
    def __init__(self):
        # regex patterns
        self.pct_re = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")
        self.days_re = re.compile(r"(\d{1,4})\s*(?:days|day|d|days?)\b", re.I)
        self.minstay_re = re.compile(r"shorter than\s+(\d+)\s*(?:nights|night)", re.I)
        self.product_re = re.compile(r"\b(flight|flights|hotel|hotels|car|cars|package|packages|insurance|visa)\b", re.I)
        self.fare_re = re.compile(r"\b(economy|premium|business)\b", re.I)
        self.promo_re = re.compile(r"\b([A-Z0-9]{3,12})\b")
        self.price_re = re.compile(r"\b(\d{3,7})\b")

    def _tag_tokens(self, tokens):
        tags = ["O"] * len(tokens)
        text = " ".join(tokens)

        # discount pct
        m = self.pct_re.search(text)
        if m:
            num = m.group(1)
            # find token containing num or '%'
            for i, tk in enumerate(tokens):
                if num in tk or "%" in tk:
                    tags[i] = "B-DISCOUNT_PCT"
                    if i+1 < len(tokens) and "%" in tokens[i+1]:
                        tags[i+1] = "I-DISCOUNT_PCT"
                    break

        # booking window / days
        m = self.days_re.search(text)
        if m:
            val = m.group(1)
            for i, tk in enumerate(tokens):
                if val in tk:
                    tags[i] = "B-DATE"
                    if i+1 < len(tokens):
                        tags[i+1] = "I-DATE"
                    break

        # min stay (nights)
        m = self.minstay_re.search(text)
        if m:
            val = m.group(1)
            for i, tk in enumerate(tokens):
                if val in tk:
                    tags[i] = "B-MINSTAY"
                    if i+1 < len(tokens):
                        tags[i+1] = "I-MINSTAY"
                    break

        # fare class
        m = self.fare_re.search(text)
        if m:
            v = m.group(1).lower()
            for i, tk in enumerate(tokens):
                if v in tk.lower():
                    tags[i] = "B-FARE"
                    break

        # product
        m = self.product_re.search(text)
        if m:
            v = m.group(1).lower().rstrip("s")
            for i, tk in enumerate(tokens):
                if v in tk.lower():
                    tags[i] = "B-PRODUCT"
                    break

        # promo codes / uppercase tokens (very naive)
        # mark tokens that look like promo codes (all caps letters+numbers)
        for i, tk in enumerate(tokens):
            if len(tk) >= 3 and tk.isupper() and any(ch.isalpha() for ch in tk):
                tags[i] = "B-PROMO"

        # numeric price hints
        m = self.price_re.search(text)
        if m:
            val = m.group(1)
            for i, tk in enumerate(tokens):
                if val in tk:
                    tags[i] = "B-PRICE"
                    break

        return tags

    def predict(self, list_of_tokens_lists):
        results = []
        for tokens in list_of_tokens_lists:
            results.append(self._tag_tokens(tokens))
        return results

# Save object
dummy = EnhancedDummyCRF()
joblib.dump(dummy, OUT_PATH)
print("Saved enhanced DummyCRF to", OUT_PATH)
