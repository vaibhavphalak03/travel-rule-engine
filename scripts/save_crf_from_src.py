# scripts/save_crf_from_src.py
from pathlib import Path
import joblib
from src.crf_model import EnhancedDummyCRF

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "models" / "crf_model.joblib"
OUT.parent.mkdir(exist_ok=True)
obj = EnhancedDummyCRF()
joblib.dump(obj, OUT)
print("Saved CRF object to", OUT)
