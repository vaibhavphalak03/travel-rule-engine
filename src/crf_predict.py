# src/crf_predict.py
import joblib
import spacy
from src.entity_patterns import PATTERNS

MODEL = "models/crf_model.pkl"

def load_nlp_with_ruler():
    try:
        nlp = spacy.load("en_core_web_sm")
    except:
        nlp = spacy.blank("en")
    # add entity ruler if missing
    from spacy.pipeline import EntityRuler
    if "entity_ruler" not in nlp.pipe_names:
        ruler = nlp.add_pipe("entity_ruler")
        ruler.add_patterns(PATTERNS)
    return nlp

def extract_tokens(text):
    nlp = load_nlp_with_ruler()
    doc = nlp(text)
    return [t.text for t in doc]

def to_features(tokens):
    # replicate feature extraction used in training
    def f(sent, i):
        w = sent[i]
        out = {
            "bias": 1.0,
            "word.lower()": w.lower(),
            "word.isupper()": w.isupper(),
            "word.istitle()": w.istitle(),
            "word.isdigit()": w.isdigit(),
            "word.isalpha()": w.isalpha(),
            "suffix(3)": w[-3:],
            "prefix(3)": w[:3]
        }
        if i>0:
            p = sent[i-1]
            out["-1:word.lower()"] = p.lower()
            out["-1:word.isdigit()"] = p.isdigit()
        else:
            out["BOS"] = True
        if i < len(sent)-1:
            n = sent[i+1]
            out["+1:word.lower()"] = n.lower()
            out["+1:word.isdigit()"] = n.isdigit()
        else:
            out["EOS"] = True
        return out
    return [f(tokens, i) for i in range(len(tokens))]

if __name__ == "__main__":
    crf = joblib.load(MODEL)
    s = "Offer 10% discount on flights booked at least 30 days before travel."
    toks = extract_tokens(s)
    feats = to_features(toks)
    pred = crf.predict([feats])[0]
    print("Tokens:", toks)
    print("Pred:", pred)
