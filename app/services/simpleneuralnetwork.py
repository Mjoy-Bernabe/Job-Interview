# services/simpleneuralnetwork.py
"""
Small feed-forward Artificial Neural Network (ANN) that fuses the
semantic-similarity and keyword features into the final qualification score.

Why this file exists
---------------------
The methodology write-up describes a "Hybrid ANN + text similarity" model,
but the codebase only ever combined cosine similarity and keyword overlap
with a hard-coded formula (final = 0.7*cosine + 0.3*keyword). There was no
neural network anywhere - this file was previously empty. This module makes
the ANN real:

    [cosine_score, keyword_score, answer_length_score]
                    |
            hidden layer (ReLU, 4 units)
                    |
            output layer (linear, 1 unit) -> clipped to [0, 1]

Backward compatibility
-----------------------
The network ships with hand-set weights that are mathematically IDENTICAL to
the original formula (answer_length_score starts at weight 0), so scores
will not change unless you retrain. Once you have HR-confirmed labels
(Qualified / Not Qualified per answer), call `train_on_feedback()` and the
network will start learning a better combination than the fixed 70/30 split
- e.g. it can learn that keyword overlap matters less for "tell me about
yourself" style questions than for technical ones.

No external ML dependency is required beyond numpy (already installed as a
dependency of sentence-transformers/keybert).
"""

import json
import os
import numpy as np

WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "ann_weights.json")

FEATURE_NAMES = ["cosine_score", "keyword_score", "answer_length_score"]


class SimpleANN:
    def __init__(self, n_inputs: int = 3, n_hidden: int = 4):
        self.n_inputs = n_inputs
        self.n_hidden = n_hidden
        self._init_identity_weights()
        self._load_saved_weights()

    def _init_identity_weights(self):
        """
        Set up weights so the network reproduces the original
        final = 0.7*cosine + 0.3*keyword formula out of the box.

        Hidden neuron 0 passes cosine_score through untouched.
        Hidden neuron 1 passes keyword_score through untouched.
        Hidden neurons 2-3 are spare capacity for training later (start at 0
        contribution so they don't affect the current output).
        """
        self.W1 = np.zeros((self.n_inputs, self.n_hidden))
        self.b1 = np.zeros(self.n_hidden)
        self.W1[0, 0] = 1.0  # cosine_score -> hidden[0]
        self.W1[1, 1] = 1.0  # keyword_score -> hidden[1]
        self.W1[2, 2] = 1.0  # answer_length_score -> hidden[2] (unused until trained)

        self.W2 = np.zeros((self.n_hidden, 1))
        self.b2 = np.zeros(1)
        self.W2[0, 0] = 0.7  # weight on cosine
        self.W2[1, 0] = 0.3  # weight on keyword
        self.W2[2, 0] = 0.0  # length feature starts at 0 influence

    def _load_saved_weights(self):
        if os.path.exists(WEIGHTS_PATH):
            try:
                with open(WEIGHTS_PATH, "r") as f:
                    data = json.load(f)
                self.W1 = np.array(data["W1"])
                self.b1 = np.array(data["b1"])
                self.W2 = np.array(data["W2"])
                self.b2 = np.array(data["b2"])
            except Exception:
                # fall back silently to the identity/default weights
                pass

    def save(self):
        with open(WEIGHTS_PATH, "w") as f:
            json.dump(
                {
                    "W1": self.W1.tolist(),
                    "b1": self.b1.tolist(),
                    "W2": self.W2.tolist(),
                    "b2": self.b2.tolist(),
                },
                f,
            )

    def _relu(self, x):
        return np.maximum(0, x)

    def forward(self, x: np.ndarray) -> float:
        h = self._relu(x @ self.W1 + self.b1)
        out = h @ self.W2 + self.b2
        return float(np.clip(out[0], 0.0, 1.0))

    def predict(self, cosine_score: float, keyword_score: float,
                answer_length_score: float = 0.0) -> float:
        x = np.array([cosine_score, keyword_score, answer_length_score])
        return round(self.forward(x), 4)

    def train_on_feedback(self, samples, epochs: int = 300, lr: float = 0.05):
        """
        samples: list of dicts like
            {"cosine_score": .., "keyword_score": .., "answer_length_score": ..,
             "label": 1.0 or 0.0}   # 1.0 = HR confirmed Qualified
        Simple gradient descent (MSE loss) over the small network. Intended
        to be run offline / in a maintenance script once enough HR-confirmed
        labels exist, not on every request.
        """
        if not samples:
            return
        X = np.array([[s["cosine_score"], s["keyword_score"],
                        s.get("answer_length_score", 0.0)] for s in samples])
        y = np.array([[s["label"]] for s in samples])

        for _ in range(epochs):
            h_lin = X @ self.W1 + self.b1
            h = self._relu(h_lin)
            out = h @ self.W2 + self.b2

            error = out - y
            dW2 = h.T @ error / len(X)
            db2 = error.mean(axis=0)

            dh = (error @ self.W2.T) * (h_lin > 0)
            dW1 = X.T @ dh / len(X)
            db1 = dh.mean(axis=0)

            self.W2 -= lr * dW2
            self.b2 -= lr * db2
            self.W1 -= lr * dW1
            self.b1 -= lr * db1

        self.save()


_ann = SimpleANN()


def score(cosine_score: float, keyword_score: float,
          answer_length_score: float = 0.0) -> float:
    """Public entry point used by services/scoring.py"""
    return _ann.predict(cosine_score, keyword_score, answer_length_score)


def train_on_feedback(samples, epochs: int = 300, lr: float = 0.05):
    _ann.train_on_feedback(samples, epochs=epochs, lr=lr)
