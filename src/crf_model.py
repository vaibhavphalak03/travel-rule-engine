# src/crf_model.py
import re

class EnhancedDummyCRF:
    """
    Deterministic CRF-like object implementing predict(list_of_tokens_lists).
    Kept under src so joblib/pickle can find the class as src.crf_model.EnhancedDummyCRF
    """
    def __init__(self):
        self.pct_re = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")
        self.days_re = re.compile(r"(\d{1,4})\s*(?:days|day|d|days?)\b", re.I)
        self.minstay_re = re.compile(r"shorter than\s+(\d+)\s*(?:nights|night)", re.I)
        self.product_re = re.compile(r"\b(flight|flights|hotel|hotels|car|cars|package|packages|insurance|visa)\b", re.I)
        self.fare_re = re.compile(r"\b(economy|premium|business)\b", re.I)
        self.price_re = re.compile(r"\b(\d{3,7})\b")
        self.promo_re = re.compile(r"\b([A-Z0-9]{3,12})\b")

    def _tag_tokens(self, tokens):
        tags = ["O"] * len(tokens)
        text = " ".join(tokens)

        m = self.pct_re.search(text)
        if m:
            num = m.group(1)
            for i, tk in enumerate(tokens):
                if num in tk or "%" in tk:
                    tags[i] = "B-DISCOUNT_PCT"
                    if i+1 < len(tokens) and "%" in tokens[i+1]:
                        tags[i+1] = "I-DISCOUNT_PCT"
                    break

        m = self.days_re.search(text)
        if m:
            val = m.group(1)
            for i, tk in enumerate(tokens):
                if val in tk:
                    tags[i] = "B-DATE"
                    if i+1 < len(tokens):
                        tags[i+1] = "I-DATE"
                    break

        m = self.minstay_re.search(text)
        if m:
            val = m.group(1)
            for i, tk in enumerate(tokens):
                if val in tk:
                    tags[i] = "B-MINSTAY"
                    if i+1 < len(tokens):
                        tags[i+1] = "I-MINSTAY"
                    break

        m = self.fare_re.search(text)
        if m:
            v = m.group(1).lower()
            for i, tk in enumerate(tokens):
                if v in tk.lower():
                    tags[i] = "B-FARE"
                    break

        m = self.product_re.search(text)
        if m:
            v = m.group(1).lower().rstrip("s")
            for i, tk in enumerate(tokens):
                if v in tk.lower():
                    tags[i] = "B-PRODUCT"
                    break

        for i, tk in enumerate(tokens):
            if len(tk) >= 3 and tk.isupper() and any(ch.isalpha() for ch in tk):
                tags[i] = "B-PROMO"

        m = self.price_re.search(text)
        if m:
            val = m.group(1)
            for i, tk in enumerate(tokens):
                if val in tk:
                    tags[i] = "B-PRICE"
                    break

        return tags

    def predict(self, list_of_tokens_lists):
        return [self._tag_tokens(tokens) for tokens in list_of_tokens_lists]
