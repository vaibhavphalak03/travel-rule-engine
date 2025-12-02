# src/postprocess_slots.py
import re

def bio_to_spans(tokens, tags):
    spans = []
    cur_label = None
    cur_tokens = []
    start = None
    for i, (t, tag) in enumerate(zip(tokens, tags)):
        if tag == 'O':
            if cur_label:
                spans.append((cur_label, ' '.join(cur_tokens), start, i-1))
                cur_label = None
                cur_tokens = []
                start = None
            continue
        if tag.startswith('B-'):
            if cur_label:
                spans.append((cur_label, ' '.join(cur_tokens), start, i-1))
            cur_label = tag[2:]
            cur_tokens = [t]
            start = i
            continue
        if tag.startswith('I-') and cur_label:
            cur_tokens.append(t)
    if cur_label:
        spans.append((cur_label, ' '.join(cur_tokens), start, len(tokens)-1))
    return spans

def normalize_span_to_attr(span_label, span_text):
    """
    Map span_label & text to attribute name + normalized value.
    Return (attr_name, value)
    """
    # simple rules — extend as needed
    if span_label in ('DISCOUNT_PCT', 'PERCENT'):
        # find first number
        m = re.search(r'(\d+)', span_text)
        if m:
            return ('discount_pct', int(m.group(1)))
    if span_label in ('DATE','BOOKING_WINDOW_DAYS'):
        # find number of days
        m = re.search(r'(\d+)', span_text)
        if m:
            return ('booking_window_days', int(m.group(1)))
    if span_label == 'PRODUCT_TYPE':
        return ('product_type', span_text.lower())
    if span_label == 'PROMO_CODE':
        return ('promo_code', span_text)
    # fallback
    return (span_label.lower(), span_text)

# example usage
tokens = ['Offer','10','%','discount','on','flights','booked','at','least','30','days','before','travel','.']
tags = ['O','B-DISCOUNT_PCT','I-DISCOUNT_PCT','O','O','O','O','B-DATE','I-DATE','I-DATE','I-DATE','O','O','O']
spans = bio_to_spans(tokens, tags)
attrs = [normalize_span_to_attr(lbl, txt) for lbl, txt, _, _ in spans]
print(spans)   # e.g. [('DISCOUNT_PCT','10 %',1,2), ('DATE','at least 30 days',7,10)]
print(attrs)   # e.g. [('discount_pct',10), ('booking_window_days',30)]
