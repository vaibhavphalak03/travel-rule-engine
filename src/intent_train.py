# src/intent_train.py
import json
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

ROOT = Path(__file__).resolve().parents[1]
GEN_FILE = ROOT / "data" / "generated_rules.jsonl"
MODEL_OUT = ROOT / "models" / "intent_clf.pkl"

def load_data():
    texts = []
    labels = []
    for line in open(GEN_FILE, encoding="utf8"):
        obj = json.loads(line)
        nl = obj.get("nl","")
        name = obj.get("name","unknown")
        texts.append(nl)
        labels.append(name)
    return texts, labels

def train():
    X, y = load_data()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    pipe = make_pipeline(TfidfVectorizer(ngram_range=(1,2), min_df=2), LogisticRegression(max_iter=1000))
    pipe.fit(X_train, y_train)
    preds = pipe.predict(X_test)
    print(classification_report(y_test, preds, zero_division=0))
    joblib.dump(pipe, MODEL_OUT)
    print("Saved intent model to", MODEL_OUT)

if __name__ == "__main__":
    train()
