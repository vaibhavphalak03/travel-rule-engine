# src/crf_train.py
"""
Train a CRF slot tagger on data/bio_training_data.jsonl
Saves model to models/crf_model.pkl
"""
import json
from pathlib import Path
import random
import joblib
from sklearn.metrics import classification_report
import sklearn_crfsuite
from sklearn_crfsuite import metrics

ROOT = Path(__file__).resolve().parents[1]
BIO_FILE = ROOT / "data" / "bio_training_data.jsonl"
MODEL_OUT = ROOT / "models" / "crf_model.pkl"

def word2features(sent, i):
    word = sent[i]
    features = {
        "bias": 1.0,
        "word.lower()": word.lower(),
        "word.isupper()": word.isupper(),
        "word.istitle()": word.istitle(),
        "word.isdigit()": word.isdigit(),
        "word.isalpha()": word.isalpha(),
        "suffix(3)": word[-3:],
        "prefix(3)": word[:3],
    }
    if i > 0:
        prev = sent[i-1]
        features.update({
            "-1:word.lower()": prev.lower(),
            "-1:word.isdigit()": prev.isdigit()
        })
    else:
        features["BOS"] = True
    if i < len(sent)-1:
        nxt = sent[i+1]
        features.update({
            "+1:word.lower()": nxt.lower(),
            "+1:word.isdigit()": nxt.isdigit()
        })
    else:
        features["EOS"] = True
    return features

def sent2features(sent):
    return [word2features(sent, i) for i in range(len(sent))]

def sent2labels(tags):
    return tags

def load_data():
    examples = [json.loads(l) for l in open(BIO_FILE, "r", encoding="utf8").read().splitlines()]
    X = [sent2features(e["tokens"]) for e in examples]
    y = [sent2labels(e["tags"]) for e in examples]
    return X, y

def train_and_eval():
    X, y = load_data()
    # simple train/test split
    data = list(zip(X, y))
    random.seed(42)
    random.shuffle(data)
    split = int(0.8 * len(data))
    train = data[:split]
    test = data[split:]
    X_train, y_train = zip(*train)
    X_test, y_test = zip(*test)

    crf = sklearn_crfsuite.CRF(
        algorithm='lbfgs',
        c1=0.1,
        c2=0.1,
        max_iterations=100,
        all_possible_transitions=True
    )
    print("Training CRF... (this may take a minute)")
    crf.fit(list(X_train), list(y_train))

    # Save model
    joblib.dump(crf, MODEL_OUT)
    print("Saved CRF model to", MODEL_OUT)

    # Evaluate
    y_pred = crf.predict(list(X_test))
    labels = list(crf.classes_)
    # remove 'O' for metrics
    labels = [l for l in labels if l != 'O']
    print("\nClassification report (by label):")
    print(metrics.flat_classification_report(y_test, y_pred, labels=labels, digits=3))

if __name__ == "__main__":
    train_and_eval()
