"""
Re-train and re-save the interview scoring ANN model.

This script creates a simple 3-input → 1-output neural network that scores
interview answers based on:
  - cosine_score  (S-BERT semantic similarity, 0–1)
  - keyword_score (KeyBERT keyword overlap, 0–1)
  - word_count    (number of words in the answer)

It generates synthetic training data that encodes sensible scoring rules,
trains the model, and saves it as models/interview_scoring_ann.keras
compatible with your current TensorFlow/Keras version.

Usage:
    python retrain_ann.py
"""

import numpy as np
import os

# ── Suppress TF verbose logs ──
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import keras
from keras import layers

print(f"Keras version: {keras.__version__}")

# ─────────────────────────────────────────────
# 1. Generate synthetic training data
# ─────────────────────────────────────────────
np.random.seed(42)
N = 5000  # number of training samples

# Random features
cosine_scores  = np.random.uniform(0.0, 1.0, N)
keyword_scores = np.random.uniform(0.0, 1.0, N)
word_counts    = np.random.randint(1, 150, N).astype(float)

# Normalize word_count to a 0–1 range for the label formula
# (we'll feed the raw word_count as a feature, but the label uses a scaled version)
word_count_norm = np.clip(word_counts / 50.0, 0.0, 1.0)  # 50+ words ≈ max credit

# Build a sensible label:
#   - cosine_score is most important (semantic match):  weight 0.55
#   - keyword_score matters moderately:                 weight 0.25
#   - answer length gives a small bonus:                weight 0.20
labels = (
    0.55 * cosine_scores +
    0.25 * keyword_scores +
    0.20 * word_count_norm
)

# Clip to [0, 1] and add a tiny bit of noise for realism
labels = np.clip(labels + np.random.normal(0, 0.03, N), 0.0, 1.0)

# Stack features: shape (N, 3)
X_train = np.column_stack([cosine_scores, keyword_scores, word_counts])
y_train = labels.astype(np.float32)

print(f"Training data shape: X={X_train.shape}, y={y_train.shape}")
print(f"Label stats — min: {y_train.min():.3f}, max: {y_train.max():.3f}, mean: {y_train.mean():.3f}")

# ─────────────────────────────────────────────
# 2. Build the ANN (same 3-input architecture)
# ─────────────────────────────────────────────
model = keras.Sequential([
    layers.Input(shape=(3,)),
    layers.Dense(64, activation="relu"),
    layers.Dense(32, activation="relu"),
    layers.Dense(16, activation="relu"),
    layers.Dense(1, activation="sigmoid"),   # output in [0, 1]
])

model.compile(
    optimizer="adam",
    loss="mse",
    metrics=["mae"],
)

model.summary()

# ─────────────────────────────────────────────
# 3. Train
# ─────────────────────────────────────────────
history = model.fit(
    X_train, y_train,
    epochs=50,
    batch_size=64,
    validation_split=0.2,
    verbose=1,
)

# ─────────────────────────────────────────────
# 4. Quick sanity check
# ─────────────────────────────────────────────
test_cases = np.array([
    [0.95, 0.80, 45],   # Great answer: high cosine, good keywords, decent length
    [0.70, 0.60, 30],   # Good answer
    [0.40, 0.20, 10],   # Weak answer
    [0.10, 0.00,  2],   # Terrible answer
    [0.85, 1.00, 60],   # Excellent with all keywords
])

predictions = model.predict(test_cases, verbose=0)
print("\n── Sanity Check ──")
for i, (tc, pred) in enumerate(zip(test_cases, predictions)):
    cos, kw, wc = tc
    print(f"  Case {i+1}: cosine={cos:.2f}  keyword={kw:.2f}  words={int(wc)}  → score={pred[0]:.4f}")

# ─────────────────────────────────────────────
# 5. Save the model
# ─────────────────────────────────────────────
save_path = os.path.join(os.path.dirname(__file__), "models", "interview_scoring_ann.keras")
os.makedirs(os.path.dirname(save_path), exist_ok=True)
model.save(save_path)
print(f"\n✅ Model saved to: {save_path}")

# Verify it loads back
loaded = keras.models.load_model(save_path)
print("✅ Model re-loaded successfully — no version errors!")
