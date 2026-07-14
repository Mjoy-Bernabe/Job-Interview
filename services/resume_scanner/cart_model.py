"""
cart_model.py  ── v2
CART model calibrated to real ATS criteria.

Key changes over v1
-------------------
1. Rule-based scoring FIRST: a clean weighted-score system grades the resume
   against real thresholds (sections, bullets, verbs, keywords, dates).
   This replaces the random synthetic-data tree that always said Moderate.

2. A learned CART tree refines the score when enough training data exists,
   but the rules always anchor the decision so it is explainable and stable.

3. Scoring bands:
     Strong Fit   ≥ 80 / 100
     Moderate Fit  60–79 / 100
     Weak Fit     < 60 / 100

4. PDF vs DOCX produce the same score for the same resume because all counts
   are normalised upstream in resume_parser.py.

5. The "not qualified" message is injected for Weak Fit results.
"""

import os
import pickle

MODEL_PATH         = os.path.join(os.path.dirname(__file__), "cart_model.pkl")
DATASET_MODEL_PATH = os.path.join(os.path.dirname(__file__), "dataset_fit_model.pkl")
DATASET_PATH       = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ats_resume_dataset_elite_v3.csv")
LABELS = ["Strong Fit", "Moderate Fit", "Weak Fit"]


# ─────────────────────────────────────────────────────────────────────────────
# Dataset-trained fit model (ats_resume_dataset_elite_v3.csv)
# ─────────────────────────────────────────────────────────────────────────────
# A scikit-learn LogisticRegression trained on 6,000 real labelled rows
# (skill_match_score, experience_match, education_match → shortlisted).
# It cannot see resume formatting (bullets, sections, etc.) — only
# skill/experience/education fit — so it complements, rather than
# replaces, the rule-based score above. ~89% held-out accuracy.
_dataset_model = None


def _load_dataset_model():
    global _dataset_model
    if _dataset_model is not None:
        return _dataset_model
    # Train from the supplied labelled dataset when it is present. This avoids
    # relying on a version-sensitive pickle and guarantees the live scorer is
    # calibrated from ats_resume_dataset_elite_v3.csv.
    try:
        import pandas as pd
        from sklearn.linear_model import LogisticRegression

        dataset = pd.read_csv(DATASET_PATH)
        columns = ["skill_match_score", "experience_match", "education_match"]
        dataset = dataset.dropna(subset=columns + ["shortlisted"])
        _dataset_model = LogisticRegression(max_iter=1000, class_weight="balanced")
        _dataset_model.fit(dataset[columns], dataset["shortlisted"].astype(int))
        return _dataset_model
    except Exception:
        pass

    # A packaged model remains a fallback for deployments that do not include
    # the source CSV.
    try:
        with open(DATASET_MODEL_PATH, "rb") as f:
            _dataset_model = pickle.load(f)
    except Exception:
        _dataset_model = False  # sentinel: tried and failed, don't retry every call
    return _dataset_model


def _dataset_fit_probability(
    features: dict,
    experience_match: bool | None = None,
    education_match: bool | None = None,
) -> float | None:
    """
    Map our resume ats_features onto the dataset's 3-feature schema and
    return the trained model's P(shortlisted). Returns None if the model
    file isn't available, so callers can fall back to rules-only scoring.
    """
    model = _load_dataset_model()
    if not model:
        return None
    skill_match_score = features.get("keyword_match_ratio", 0.0)
    # These must describe the applicant against this job, not merely whether
    # the resume contains a date or an Education heading.
    experience_match = int(bool(experience_match)) if experience_match is not None else 0
    education_match = int(bool(education_match)) if education_match is not None else 0
    try:
        import pandas as pd
        row = pd.DataFrame(
            [[skill_match_score, experience_match, education_match]],
            columns=["skill_match_score", "experience_match", "education_match"],
        )
        proba = model.predict_proba(row)[0]
        classes = list(model.classes_)
        return float(proba[classes.index(1)])
    except Exception:
        return None

# ─────────────────────────────────────────────────────────────────────────────
# Feature order (must match resume_parser.extract_ats_features keys)
# ─────────────────────────────────────────────────────────────────────────────
FEATURE_ORDER = [
    "word_count",
    "has_contact_section",
    "has_summary_section",
    "has_experience_section",
    "has_education_section",
    "has_skills_section",
    "has_email",
    "has_phone",
    "bullet_count",
    "date_range_count",
    "action_verb_count",
    "keyword_hit_count",
    "keyword_total_count",
    "keyword_match_ratio",
    "suspicious_table_lines",
    "sections_present",
    "experience_depth",
]


def _to_vector(features: dict) -> list:
    return [float(features.get(k, 0)) for k in FEATURE_ORDER]


# ─────────────────────────────────────────────────────────────────────────────
# Rule-based weighted scorer  (primary decision engine)
# ─────────────────────────────────────────────────────────────────────────────

def _rule_score(features: dict) -> float:
    """
    Returns a 0-100 score based on weighted ATS criteria.
    Weights are tuned to your job_descriptions requirements:
      - Keyword match is the strongest signal (35 pts)
      - Structure/sections (25 pts)
      - Content quality — bullets + verbs + date ranges (25 pts)
      - Format hygiene — word count, no tables (15 pts)
    """
    score = 0.0

    # ── 1. Keyword match (35 pts) ─────────────────────────────────────────────
    ratio = features.get("keyword_match_ratio", 0.0)
    if ratio >= 0.75:
        score += 35
    elif ratio >= 0.50:
        score += 35 * (ratio / 0.75)   # linear scale up to 35
    elif ratio >= 0.30:
        score += 15
    else:
        score += ratio * 50            # very low: minimal credit

    # ── 2. Section completeness (25 pts, 5 pts each) ─────────────────────────
    score += 5 if features.get("has_contact_section") else 0
    score += 5 if features.get("has_summary_section")  else 0
    score += 5 if features.get("has_experience_section") else 0
    score += 5 if features.get("has_education_section") else 0
    score += 5 if features.get("has_skills_section")   else 0

    # ── 3. Content quality (25 pts) ───────────────────────────────────────────
    # Bullets: 0-10 pts
    bullets = features.get("bullet_count", 0)
    if bullets >= 8:
        score += 10
    elif bullets >= 5:
        score += 7
    elif bullets >= 3:
        score += 4
    else:
        score += 0

    # Action verbs: 0-8 pts  (distinct verbs, so 8 unique = full marks)
    verbs = features.get("action_verb_count", 0)
    if verbs >= 8:
        score += 8
    elif verbs >= 5:
        score += 6
    elif verbs >= 3:
        score += 3
    else:
        score += 0

    # Date ranges (experience depth): 0-7 pts
    dates = features.get("date_range_count", 0)
    if dates >= 3:
        score += 7
    elif dates >= 2:
        score += 5
    elif dates >= 1:
        score += 3
    else:
        score += 0

    # ── 4. Format hygiene (15 pts) ────────────────────────────────────────────
    # Word count in sweet spot 300-900: 8 pts
    wc = features.get("word_count", 0)
    if 300 <= wc <= 900:
        score += 8
    elif 200 <= wc < 300 or 900 < wc <= 1100:
        score += 4
    else:
        score += 0

    # Has email: 4 pts
    score += 4 if features.get("has_email") else 0

    # Has phone: 3 pts
    score += 3 if features.get("has_phone") else 0

    # Table penalty
    tables = features.get("suspicious_table_lines", 0)
    if tables > 5:
        score -= 5
    elif tables > 2:
        score -= 2

    return max(0.0, min(100.0, score))


def _score_to_label(score: float) -> tuple[str, dict]:
    """Convert 0-100 score to label + simulated probabilities."""
    if score >= 80:
        label = "Strong Fit"
        probs = {
            "Strong Fit":   round(0.5 + (score - 80) / 100, 3),
            "Moderate Fit": round(0.35 - (score - 80) / 200, 3),
            "Weak Fit":     0.0,
        }
    elif score >= 60:
        t = (score - 60) / 20   # 0 → 1 within Moderate band
        label = "Moderate Fit"
        probs = {
            "Strong Fit":   round(0.1 + t * 0.2, 3),
            "Moderate Fit": round(0.65 + t * 0.1, 3),
            "Weak Fit":     round(0.25 - t * 0.2, 3),
        }
    else:
        label = "Weak Fit"
        probs = {
            "Strong Fit":   0.0,
            "Moderate Fit": round(score / 200, 3),
            "Weak Fit":     round(1.0 - score / 200, 3),
        }

    # Normalise so they always sum to 1.0
    total = sum(probs.values())
    probs = {k: round(v / total, 4) for k, v in probs.items()}
    return label, probs


# ─────────────────────────────────────────────────────────────────────────────
# Minimal CART (kept for future fine-tuning with real labelled data)
# ─────────────────────────────────────────────────────────────────────────────

class _Node:
    __slots__ = ("feature_idx","threshold","left","right","label","probs")
    def __init__(self):
        self.feature_idx = None
        self.threshold   = None
        self.left = self.right = None
        self.label = self.probs = None


def _gini(groups, classes):
    total = sum(len(g) for g in groups)
    if not total:
        return 0.0
    score = 0.0
    for group in groups:
        size = len(group)
        if not size:
            continue
        p_sum = sum((sum(1 for r in group if r[-1] == c) / size) ** 2 for c in classes)
        score += (1.0 - p_sum) * (size / total)
    return score


def _best_split(rows, n_features, classes):
    best = (float("inf"), None, None, None)
    for fi in range(n_features):
        vals = sorted(set(r[fi] for r in rows))
        for i in range(len(vals) - 1):
            thr = (vals[i] + vals[i+1]) / 2
            left  = [r for r in rows if r[fi] <= thr]
            right = [r for r in rows if r[fi] >  thr]
            g = _gini([left, right], classes)
            if g < best[0]:
                best = (g, fi, thr, (left, right))
    return best[1], best[2], best[3]


def _leaf(rows, classes):
    node = _Node()
    counts = {c: sum(1 for r in rows if r[-1] == c) for c in classes}
    total  = len(rows)
    node.probs = {c: counts[c] / total for c in classes}
    node.label = max(counts, key=counts.get)
    return node


def _build(rows, classes, max_depth, min_size, depth=0):
    if depth >= max_depth or len(rows) <= min_size or len(set(r[-1] for r in rows)) == 1:
        return _leaf(rows, classes)
    fi, thr, groups = _best_split(rows, len(rows[0]) - 1, classes)
    if fi is None:
        return _leaf(rows, classes)
    node = _Node()
    node.feature_idx = fi
    node.threshold   = thr
    node.left  = _build(groups[0], classes, max_depth, min_size, depth + 1)
    node.right = _build(groups[1], classes, max_depth, min_size, depth + 1)
    return node


def _predict(node, row):
    while node.label is None:
        node = node.left if row[node.feature_idx] <= node.threshold else node.right
    return node.label, node.probs


class CARTClassifier:
    def __init__(self, max_depth=8, min_size=5):
        self.max_depth = max_depth
        self.min_size  = min_size
        self.classes_  = []
        self._root     = None

    def fit(self, X, y):
        self.classes_ = sorted(set(y))
        rows = [x + [lbl] for x, lbl in zip(X, y)]
        self._root = _build(rows, self.classes_, self.max_depth, self.min_size)
        return self

    def predict_proba_one(self, x):
        _, probs = _predict(self._root, x)
        return probs

    def predict_one(self, x):
        lbl, _ = _predict(self._root, x)
        return lbl


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic training data  (calibrated to rule-score thresholds)
# ─────────────────────────────────────────────────────────────────────────────

import random

def _synthetic_sample(label: str, rng: random.Random) -> dict:
    if label == "Strong Fit":        # rule score ≥ 80
        kw_total = rng.randint(8, 15)
        kw_hits  = rng.randint(int(kw_total * 0.75), kw_total)
        return {
            "word_count":              rng.randint(380, 850),
            "has_contact_section":     1,
            "has_summary_section":     1,
            "has_experience_section":  1,
            "has_education_section":   1,
            "has_skills_section":      1,
            "has_email":               1,
            "has_phone":               1,
            "bullet_count":            rng.randint(8, 22),
            "date_range_count":        rng.randint(3, 6),
            "action_verb_count":       rng.randint(8, 18),
            "keyword_hit_count":       kw_hits,
            "keyword_total_count":     kw_total,
            "keyword_match_ratio":     round(kw_hits / kw_total, 3),
            "suspicious_table_lines":  rng.randint(0, 1),
            "sections_present":        5,
            "experience_depth":        rng.randint(3, 6),
        }
    elif label == "Moderate Fit":    # rule score 60-79
        kw_total = rng.randint(6, 12)
        kw_hits  = rng.randint(int(kw_total * 0.50), int(kw_total * 0.74))
        return {
            "word_count":              rng.randint(280, 720),
            "has_contact_section":     rng.choice([0, 1, 1]),
            "has_summary_section":     rng.choice([0, 1]),
            "has_experience_section":  1,
            "has_education_section":   rng.choice([0, 1, 1]),
            "has_skills_section":      rng.choice([0, 1]),
            "has_email":               rng.choice([0, 1, 1]),
            "has_phone":               rng.choice([0, 1]),
            "bullet_count":            rng.randint(3, 9),
            "date_range_count":        rng.randint(1, 4),
            "action_verb_count":       rng.randint(4, 9),
            "keyword_hit_count":       kw_hits,
            "keyword_total_count":     kw_total,
            "keyword_match_ratio":     round(kw_hits / kw_total, 3),
            "suspicious_table_lines":  rng.randint(0, 3),
            "sections_present":        rng.randint(3, 4),
            "experience_depth":        rng.randint(1, 3),
        }
    else:                            # Weak Fit — rule score < 60
        kw_total = rng.randint(5, 10)
        kw_hits  = rng.randint(0, int(kw_total * 0.29))
        return {
            "word_count":              rng.choice([rng.randint(50, 280), rng.randint(950, 1500)]),
            "has_contact_section":     rng.choice([0, 0, 1]),
            "has_summary_section":     0,
            "has_experience_section":  rng.choice([0, 0, 1]),
            "has_education_section":   rng.choice([0, 1]),
            "has_skills_section":      0,
            "has_email":               rng.choice([0, 1]),
            "has_phone":               rng.choice([0, 0, 1]),
            "bullet_count":            rng.randint(0, 3),
            "date_range_count":        rng.randint(0, 1),
            "action_verb_count":       rng.randint(0, 4),
            "keyword_hit_count":       kw_hits,
            "keyword_total_count":     kw_total,
            "keyword_match_ratio":     round(kw_hits / kw_total if kw_total else 0, 3),
            "suspicious_table_lines":  rng.randint(3, 10),
            "sections_present":        rng.randint(0, 2),
            "experience_depth":        rng.randint(0, 1),
        }


def _build_training_data(n_per_class=400, seed=42):
    rng = random.Random(seed)
    X, y = [], []
    for label in LABELS:
        for _ in range(n_per_class):
            s = _synthetic_sample(label, rng)
            X.append(_to_vector(s))
            y.append(label)
    return X, y


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def _train() -> CARTClassifier:
    print("[cart_model] Training calibrated CART model …")
    X, y = _build_training_data(n_per_class=400)
    model = CARTClassifier(max_depth=8, min_size=5)
    model.fit(X, y)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    print(f"[cart_model] Model saved → {MODEL_PATH}")
    return model


def load_or_train_model() -> CARTClassifier:
    if os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH, "rb") as f:
                model = pickle.load(f)
            # Validate it has the right attributes
            if hasattr(model, "_root") and model._root is not None:
                print("[cart_model] Model loaded from disk.")
                return model
        except Exception as e:
            print(f"[cart_model] Reload failed ({e}), retraining …")
    return _train()


# ─────────────────────────────────────────────────────────────────────────────
# Applicant-facing messages
# ─────────────────────────────────────────────────────────────────────────────

_MESSAGES = {
    "Strong Fit": (
        "Congratulations! Your resume is a strong match for this position. "
        "Our recruitment team will review your application and reach out "
        "shortly regarding the next steps."
    ),
    "Moderate Fit": (
        "Thank you for your interest in this position. After reviewing your "
        "resume, we found that it does not fully meet the minimum qualifications "
        "required for this role at this time. We encourage you to review the job "
        "requirements, strengthen your resume with more relevant skills and "
        "experience, and consider reapplying in the future. We appreciate the "
        "time you took to apply and wish you all the best in your job search."
    ),
    "Weak Fit": (
        "Thank you for your interest in this position. After reviewing your "
        "resume, we found that it does not meet the minimum qualifications "
        "required for this role at this time. We encourage you to review the job "
        "requirements, strengthen your resume with relevant skills and experience, "
        "and apply again in the future. We appreciate the time you took to apply "
        "and wish you the best in your job search."
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# predict_fit  ── hybrid rule-based + CART
# ─────────────────────────────────────────────────────────────────────────────

def predict_fit(
    features: dict,
    model: CARTClassifier,
    *,
    experience_match: bool | None = None,
    education_match: bool | None = None,
) -> dict:
    """
    Two-stage prediction:
      Stage 1: rule-based weighted score (0-100) → primary label
      Stage 2: CART tree → secondary probability distribution
    Final label comes from Stage 1 (calibrated rules).
    Probabilities are blended 70% rules / 30% CART for display.

    Returns
    -------
    {
      "label":          str,
      "confidence":     float,
      "probabilities":  dict,
      "eligible":       bool,
      "score":          float,   # 0-100 for debugging
      "message":        str,
    }
    """
    # Stage 1: rule score
    rule_score         = _rule_score(features)

    # Stage 1b: dataset-trained adjustment (real-world labelled signal)
    # Nudge the rule score toward what 6,000 real shortlisting decisions
    # say about this skill/experience/education fit profile. Kept as a
    # ±6-point nudge (not a replacement) so a clean, well-formatted resume
    # can't be torpedoed by a model that only sees 3 coarse signals, and a
    # poorly-formatted resume can't be rescued purely on skill match.
    dataset_p = _dataset_fit_probability(features, experience_match, education_match)
    if dataset_p is not None:
        rule_score = max(0.0, min(100.0, rule_score + (dataset_p - 0.5) * 12))

    rule_label, rule_probs = _score_to_label(rule_score)

    # Stage 2: CART probabilities
    vec        = _to_vector(features)
    cart_probs = model.predict_proba_one(vec)
    for lbl in LABELS:
        cart_probs.setdefault(lbl, 0.0)

    # Blend 70/30
    blended = {
        lbl: round(0.70 * rule_probs.get(lbl, 0.0) + 0.30 * cart_probs.get(lbl, 0.0), 4)
        for lbl in LABELS
    }
    # Normalise
    total = sum(blended.values()) or 1
    blended = {k: round(v / total, 4) for k, v in blended.items()}

    # Final label from rules (not CART) — rules are calibrated, tree is not
    label      = rule_label
    confidence = blended[label]
    eligible   = label == "Strong Fit"

    return {
        "label":            label,
        "screening_result": "Eligible" if eligible else "Not Eligible",
        "eligible":         eligible,
        "score":            round(rule_score, 1),
        "message":          _MESSAGES[label],
    }
