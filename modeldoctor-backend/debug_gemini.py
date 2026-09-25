"""Quick debug script to see raw Gemini JSON output — uses actual ModelDoctor prompts."""
import google.generativeai as genai
from dotenv import load_dotenv
import os, json

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

from prompts.diagnosis_prompt import SYSTEM_PROMPT, build_user_prompt
from services.pattern_scanner import scan_code, format_flags_for_prompt

code = """import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report

df = pd.read_csv('customer_churn.csv')
le = LabelEncoder()
df['gender'] = le.fit_transform(df['gender'])
df['contract_type'] = le.fit_transform(df['contract_type'])
scaler = StandardScaler()
X = df.drop('churn', axis=1)
y = df['churn']
X_scaled = scaler.fit_transform(X)
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
model = GradientBoostingClassifier(n_estimators=200, learning_rate=0.1, max_depth=5)
model.fit(X_train, y_train)
y_pred = model.predict(X_test)
print(f'Accuracy: {accuracy_score(y_test, y_pred)}')
print(classification_report(y_test, y_pred))
"""

flags = scan_code(code)
flags_text = format_flags_for_prompt(flags)
user_prompt = build_user_prompt(code=code, flagged_patterns=flags_text)

model = genai.GenerativeModel(
    "gemini-2.5-flash",
    system_instruction=SYSTEM_PROMPT,
    generation_config=genai.GenerationConfig(
        temperature=0.1,
        response_mime_type="application/json",
    ),
)

resp = model.generate_content(user_prompt)
raw = resp.text
print("RAW LEN:", len(raw))
print("=" * 60)
print("REPR FIRST 500:")
print(repr(raw[:500]))
print("=" * 60)

try:
    d = json.loads(raw)
    print("DIRECT PARSE OK!")
    print("Score:", d.get("health_score"))
    print("Issues:", len(d.get("issues", [])))
except json.JSONDecodeError as e:
    print("DIRECT PARSE FAILED:", e)
    pos = e.pos
    print("AROUND ERROR POSITION:")
    print(repr(raw[max(0, pos - 100):pos + 100]))
