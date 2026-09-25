/* ────────────────────────────────────────
   Sample buggy ML codes for demo
   ──────────────────────────────────────── */

export interface SampleCode {
  id: string;
  title: string;
  description: string;
  severity: string;
  code: string;
}

export const SAMPLE_CODES: SampleCode[] = [
  {
    id: "data-leakage",
    title: "Data Leakage",
    description: "StandardScaler applied before train/test split — the classic silent killer",
    severity: "CRITICAL",
    code: `import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression

# Load data
df = pd.read_csv('data.csv')
X = df.drop('target', axis=1)
y = df['target']

# BUG: Scaler fitted on ALL data before split (DATA LEAKAGE)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)  # ← LEAKAGE HERE

# Split AFTER scaling (wrong order)
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42
)

model = LogisticRegression()
model.fit(X_train, y_train)

# This accuracy is LYING to you
accuracy = model.score(X_test, y_test)
print(f"Accuracy: {accuracy}")  # Looks great. Is meaningless.`,
  },
  {
    id: "overfitting-nightmare",
    title: "Overfitting Nightmare",
    description: "Deep neural network with no regularization, no validation, no dropout",
    severity: "HIGH",
    code: `import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
import pandas as pd
from sklearn.model_selection import train_test_split

# Load small dataset
df = pd.read_csv('data.csv')  # Only 500 rows
X = df.drop('label', axis=1)
y = df['label']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# BUG: Massive model on tiny dataset, no regularization, no dropout
model = Sequential([
    Dense(512, activation='relu', input_shape=(X_train.shape[1],)),
    Dense(512, activation='relu'),
    Dense(256, activation='relu'),
    Dense(256, activation='relu'),
    Dense(128, activation='relu'),
    Dense(1, activation='sigmoid')
])

model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

# BUG: No validation split, no early stopping — blind training
model.fit(X_train, y_train, epochs=200, batch_size=8)

# Training accuracy will be 99%+. Test accuracy will be garbage.
loss, acc = model.evaluate(X_test, y_test)
print(f"Test Accuracy: {acc}")`,
  },
  {
    id: "timeseries-leak",
    title: "Time Series Split Error",
    description: "Random shuffle on time-series data — future leaks into past",
    severity: "CRITICAL",
    code: `import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

# Load time-series financial data
df = pd.read_csv('stock_data.csv')
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date')

# Feature engineering
df['price_change'] = df['close'].pct_change()
df['ma_7'] = df['close'].rolling(7).mean()
df['ma_30'] = df['close'].rolling(30).mean()
df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
df = df.dropna()

X = df[['price_change', 'ma_7', 'ma_30', 'volume']]
y = df['target']

# BUG: Random split on time-series data — future data leaks into training!
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, shuffle=True, random_state=42
)

# BUG: LabelEncoder on full data (if categorical features existed)
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

accuracy = model.score(X_test, y_test)
print(f"Accuracy: {accuracy}")  # Looks amazing. Completely cheating.`,
  },
];
