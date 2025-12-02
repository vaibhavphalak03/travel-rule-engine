🚀 Travel Rule Engine — NL → JSON DSL (with Policy Check)

A complete end-to-end system that converts natural-language travel rules into machine-executable JSON (ZenRules-style DSL), validates them, executes them on booking payloads, and supports an attribute-based rule builder UI.

📌 Features Overview
✅ 1. Natural Language → JSON Rule Conversion

Example input: “Give 10% discount on flights booked 30 days before travel.”

- Produces structured DSL rule:

- conditions

- actions

- priority

- metadata

- Automatically adds product filters (flight/hotel/car/etc.).

- Slot extraction + intent prediction included.

✅ 2. Attribute-Based Rule Builder UI

- 35 travel parameters (flight, hotel, car, insurance, visa, package).

- Dropdowns + number/date inputs.

- Auto-generates JSON rules.

- Execute rules instantly on payload.

✅ 3. Travel Policy Validation System

- Supports policies like:

- not_cheapest_direct

- no_luxury_hotel_for_juniors

- UI displays:

- IN POLICY / OUT OF POLICY

✅ 4. ZenRules-Style Execution Engine

- Evaluates rule conditions.

- Applies actions (discount, override price).

- Shows failure reasons.

- Gives human-friendly explanation.

- Outputs final payload.

✅ 5. Machine Learning Components

- CRF BIO tagger for slot extraction

- Logistic Regression for intent classification

- Synthetic dataset powered by LLMs

- Evaluation notebook includes:

- Precision

- Recall

- F1 Score

- Confusion Matrix

✅ 6. Streamlit UIs (2 Apps)

- NL → JSON Generator — streamlit_app.py

- Attribute Rule Builder — attribute_generator.py

✅ 7. Pytest Testing Suite

- test_synthesizer.py

- test_executor.py

travel-rule-project/
│
├── src/
│   ├── synthesizer.py
│   ├── slot_tagger.py
│   ├── intent_train.py
│   ├── crf_predict.py
│   └── zenrules_executor.py
│
├── ui/
│   ├── streamlit_app.py
│   └── attribute_generator.py
│
├── data/
│   ├── parameter_dictionary.json
│   ├── sample_payload.json
│   ├── generated_rules.jsonl
│   └── bio_training_data.jsonl
│
├── notebooks/
│   └── model_evaluation.ipynb
│
├── tests/
│   ├── test_synthesizer.py
│   └── test_executor.py
│
├── Reflection.md
├── AI_Usage_Log.md
├── README.md
└── requirements.txt


🧪 How to Run the Project
1️⃣ Create & activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate

2️⃣ Install dependencies
pip install -r requirements.txt

3️⃣ Run NL → JSON UI
streamlit run ui/streamlit_app.py

4️⃣ Run Attribute-Based Rule Builder UI
streamlit run ui/attribute_generator.py

5️⃣ Run Tests
pytest -q

🎯 How the System Works
Step 1 — Slot Extraction (CRF)

Extracts:

- discount_percent

- date expressions

- booking window duration

- product category

- conditions

Step 2 — Intent Prediction

- Uses Logistic Regression to classify:

- booking_window_discount

loyalty_discount

- blackout_conflict

- price_match_policy

- seasonal_markup
and 15+ more.

Step 3 — JSON Rule Creation

Automatically builds:

- conditions

- action list

- priority

- metadata

- rule_id

Step 4 — Rule Execution

- Engine outputs:

- matched / not matched

- failed condition

- applied actions

- updated payload

- explanation text

Step 5 — Policy Check

UI displays:

IN POLICY ✔
or
OUT OF POLICY ✖

📊 ML Evaluation Summary

From model_evaluation.ipynb:

- CRF performs strongly for structured BIO slot tagging.

- Intent model reached ~55% accuracy on 20-class synthetic dataset.

- More data can increase accuracy further.

- All evaluation metrics included.

🔥 Future Improvements

- Price-match with screenshot/proof validation

- Transformer-based NER

- Rule conflict detection

- Multi-rule chain execution

- Version control for rule changes

- Visual payload diff view

👨‍💻 Developer

Vaibhav Phalak
B.Tech Artificial Intelligence
G.H. Raisoni College of Engineering & Management
📧 vaibhavphalak03@gmail.com
