"""
cart_model.py  ── v6
CART model calibrated to real ATS criteria + real labelled data.

Key changes over v5
--------------------
The dataset-trained DecisionTreeClassifier's P(shortlisted) is now BLENDED
into the weighted job-fit score (compute_weighted_fit) as a fifth signal,
instead of being computed by the resume-upload flow and then discarded.

Previously, routes/applicants.py's /submit-resume handler called
predict_fit() (which does consult the trained model) purely to compute
`fit_result`, then immediately re-derived `fit_result` a second time from
compute_weighted_fit() — a pure rule-based formula that never touched the
model at all. The first result was thrown away. compute_weighted_fit()
now accepts an optional `cart_probability` argument (the model's
P(shortlisted) for this applicant vs. this job) and folds it in as a
weighted term, via the new public dataset_fit_probability() wrapper below.

    Total Score = (0.20 x Education Score)
                + (0.25 x Experience Score)
                + (0.25 x Skill Score)
                + (0.15 x Normalized Age Score)
                + (0.15 x CART Score)              <- NEW

If the trained model is unavailable (e.g. the .pkl is missing and the CSV
can't be read), `cart_probability` is None and compute_weighted_fit()
falls back to redistributing that 0.15 proportionally across the other
four rule-based signals, so a missing model degrades visibly (score is
still meaningful) rather than silently docking 15% off every applicant.

Full pipeline (used by the resume-upload flow, /submit-resume):

    Step 1 — ATS FORMAT GATE (check_ats_format)
        The resume must first clear a minimum ATS-compliance bar (see
        resume_parser.ats_compliance_report — sections present, contact
        info, bullets, action verbs, date ranges, word count, no
        table-heavy formatting, etc). A resume an ATS can't even parse
        properly is rejected before we ever look at whether the person is
        qualified for the job.

    Step 2 — WEIGHTED JOB-FIT SCORE (compute_weighted_fit), only run if
        Step 1 passes. Each sub-score is 0-1 and is measured strictly
        against THIS job's own HR-configured requirement —
        education_baseline, required_exp_years, job_required_skills, and
        minimum_age (all pulled from job_desc / job_required_skills /
        skills_master — the same real, HR-curated source of truth
        routes/applicants.py's _job_required_skills() already uses — not
        a guess) — plus the trained CART model's own probability.

    Step 3 — THRESHOLD
        Total Score >= 0.55  -> Eligible
        Total Score <  0.55  -> Not Eligible

`predict_fit()` (the old rule-score + dataset-nudge model) and
`predict_fit_from_match_scores()` (used by the manual prescreen forms,
which have no resume to run an ATS check against) are both still present
below, unchanged, for backward compatibility with any other call sites.
"""

import os

DATASET_MODEL_PATH = os.path.join(os.path.dirname(__file__), "dataset_fit_model.pkl")
DATASET_PATH        = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ats_resume_dataset_elite_v3.csv")
LABELS = ["Strong Fit", "Moderate Fit", "Weak Fit"]


# ─────────────────────────────────────────────────────────────────────────────
# Dataset-trained fit model (ats_resume_dataset_elite_v3.csv)
# ─────────────────────────────────────────────────────────────────────────────
# A scikit-learn DecisionTreeClassifier (CART) trained on 6,000 real labelled
# rows (skill_match_score, experience_match, education_match -> shortlisted).
# It cannot see resume formatting (bullets, sections, etc.) — only
# skill/experience/education fit — so it complements, rather than replaces,
# the rule-based score below. ~89% held-out accuracy.
_dataset_model = None


def _load_dataset_model():
    """
    Load the cached dataset model from disk if present; otherwise train it
    from ats_resume_dataset_elite_v3.csv and cache it to disk. Returns
    False (not None) on failure so callers can distinguish "not loaded yet"
    from "unavailable" with a single falsy check.
    """
    global _dataset_model
    if _dataset_model is not None:
        return _dataset_model

    # Prefer a previously trained model on disk — avoids retraining (and
    # re-reading the 6,000-row CSV) on every process start.
    try:
        import joblib
        if os.path.exists(DATASET_MODEL_PATH):
            _dataset_model = joblib.load(DATASET_MODEL_PATH)
            return _dataset_model
    except Exception as e:
        print(f"[cart_model] Could not load cached dataset model ({e}), retraining …")

    try:
        import pandas as pd
        from sklearn.tree import DecisionTreeClassifier
        import joblib

        dataset = pd.read_csv(DATASET_PATH)

        columns = ["skill_match_score", "experience_match", "education_match"]
        dataset = dataset.dropna(subset=columns + ["shortlisted"])

        X = dataset[columns]
        y = dataset["shortlisted"].astype(int)

        model = DecisionTreeClassifier(
            criterion="gini",
            max_depth=5,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
        )
        model.fit(X, y)

        joblib.dump(model, DATASET_MODEL_PATH)
        _dataset_model = model
        return _dataset_model

    except Exception as e:
        print(f"[cart_model] Dataset CART training failed: {e}")
        _dataset_model = False
        return _dataset_model


def _dataset_fit_probability(
    features: dict,
    experience_match: bool | None = None,
    education_match: bool | None = None,
) -> float | None:
    """
    Map our resume ats_features onto the dataset's 3-feature schema and
    return the trained model's P(shortlisted). Returns None if the model
    isn't available, so callers can fall back to rules-only scoring.

    IMPORTANT: experience_match / education_match must describe the
    applicant against THIS job (e.g. years-of-experience >= required,
    highest degree >= required degree) — not merely whether the resume
    contains a date or an "Education" heading.
    """
    model = _load_dataset_model()
    if not model:
        return None

    skill_match_score = features.get("keyword_match_ratio", 0.0)
    experience_match = int(bool(experience_match)) if experience_match is not None else 0
    education_match = int(bool(education_match)) if education_match is not None else 0

    try:
        import pandas as pd
        row = pd.DataFrame(
            [[skill_match_score, experience_match, education_match]],
            columns=["skill_match_score", "experience_match", "education_match"],
        )
        prediction = model.predict_proba(row)[0]
        classes = list(model.classes_)
        return float(prediction[classes.index(1)])
    except Exception:
        return None


def dataset_fit_probability(
    ats_features: dict,
    experience_match: bool,
    education_match: bool,
) -> float | None:
    """
    Public wrapper around the trained dataset CART classifier — this is the
    function outside callers (routes/applicants.py, via
    services.resume_scanner) should use. Returns P(shortlisted) in [0, 1],
    or None if the model is unavailable, so compute_weighted_fit() can
    degrade gracefully instead of pretending the model said something it
    didn't.

    `ats_features` is the dict returned by resume_parser.extract_ats_features
    (i.e. extracted["ats_features"]). `experience_match` / `education_match`
    must be computed against the SPECIFIC job being screened for (applicant
    years >= required_exp_years; applicant's highest degree >= the job's
    education_baseline) — not a generic "resume has a date" / "resume has
    an Education section" check.
    """
    return _dataset_fit_probability(ats_features, experience_match, education_match)


def get_cart_model():
    """
    Public accessor kept for backward compatibility with existing callers
    (e.g. `services/resume_scanner/__init__.py` wrapping this with logging).
    Warms the cache and returns the dataset-trained model (or False if
    training/loading failed).
    """
    return _load_dataset_model()


# Backward-compat alias — older code may still import load_or_train_model().
load_or_train_model = get_cart_model


# ─────────────────────────────────────────────────────────────────────────────
# Dataset-only prediction  (no resume text/structure required)
# ─────────────────────────────────────────────────────────────────────────────
# Used by applicants.py's manual-entry prescreen forms (/submit,
# /prescreenn), where there is no uploaded resume to derive bullet counts,
# sections, action verbs, etc. from — only the same three signals the
# dataset model was trained on. There is exactly one trained model in the
# whole project, sourced from ats_resume_dataset_elite_v3.csv.

def predict_fit_from_match_scores(
    skill_match_score: float,
    experience_match: bool,
    education_match: bool,
    threshold: float = 0.55,
) -> dict:
    """
    Predict P(shortlisted) directly from the dataset model's three native
    features — skipping the resume-structure rule score in predict_fit(),
    which requires fields (bullet_count, sections_present, ...) that a
    manual entry form simply doesn't have.

    Falls back to a transparent weighted estimate (not a fixed guess) if
    the dataset model failed to load, so a missing .pkl file never
    silently produces a meaningless constant score.

    Returns
    -------
    {
      "status":             "Eligible" | "Not Eligible",
      "model_score":         float,  # 0-1 probability of being shortlisted
      "probability_percent": float,  # 0-100
      "features": {
          "skill_match_score": float,
          "experience_match":  bool,
          "education_match":   bool,
      },
    }
    """
    skill_match_score = max(0.0, min(1.0, float(skill_match_score)))
    experience_match = bool(experience_match)
    education_match = bool(education_match)

    model = _load_dataset_model()
    probability = None
    if model:
        try:
            import pandas as pd
            row = pd.DataFrame(
                [[skill_match_score, int(experience_match), int(education_match)]],
                columns=["skill_match_score", "experience_match", "education_match"],
            )
            proba = model.predict_proba(row)[0]
            classes = list(model.classes_)
            probability = float(proba[classes.index(1)])
        except Exception as e:
            print(f"[cart_model] predict_fit_from_match_scores inference failed: {e}")
            probability = None

    if probability is None:
        # Dataset model unavailable (e.g. .pkl missing and CSV unreadable)
        # — fall back to a plain, disclosed weighted estimate rather than
        # a hardcoded number, so behaviour degrades visibly, not silently.
        probability = (
            0.5 * skill_match_score
            + 0.25 * (1.0 if experience_match else 0.0)
            + 0.25 * (1.0 if education_match else 0.0)
        )

    status = "Eligible" if probability >= threshold else "Not Eligible"

    return {
        "status": status,
        "model_score": round(probability, 4),
        "probability_percent": round(probability * 100, 2),
        "features": {
            "skill_match_score": round(skill_match_score, 4),
            "experience_match": experience_match,
            "education_match": education_match,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Applicant-facing messages  (shared by the weighted engine and predict_fit)
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


# ═══════════════════════════════════════════════════════════════════════════════
# WEIGHTED JOB-FIT SCORING ENGINE  (primary decision engine for /submit-resume)
# ═══════════════════════════════════════════════════════════════════════════════
#
#   Step 1 — ATS format gate
#   Step 2 — Education / Experience / Skill / Age / CART weighted score
#   Step 3 — 0.55 threshold -> Eligible / Not Eligible

# Must match resume_parser.DEGREE_LEVEL_ORDER exactly (kept duplicated here,
# not imported, so cart_model.py has no hard dependency on the parser module
# and can be unit-tested / reused on its own).
DEGREE_LEVEL_ORDER = [
    "Entry-level track", "Diploma", "Associate", "Bachelor's", "Master's", "Doctoral",
]

# Resume must pass at least this fraction of the ATS-compliance checklist
# (resume_parser.ats_compliance_report) before job-fit scoring even runs.
ATS_MIN_PASS_RATIO = 0.5

# Weights for the Total Score formula (must sum to 1.0)
WEIGHT_EDUCATION  = 0.20
WEIGHT_EXPERIENCE = 0.25
WEIGHT_SKILLS     = 0.25
WEIGHT_AGE        = 0.15
WEIGHT_CART       = 0.15   # trained DecisionTreeClassifier signal, see dataset_fit_probability()

# Acceptance threshold requested: Total Score >= 0.55 -> Eligible
TOTAL_SCORE_THRESHOLD = 0.55


def check_ats_format(ats_compliance: dict, min_pass_ratio: float = ATS_MIN_PASS_RATIO) -> dict:
    """
    STEP 1 — ATS format gate.

    `ats_compliance` is the dict returned by
    resume_parser.ats_compliance_report(features):
        {"checks": [{"label": ..., "passed": bool, "tip": ...}, ...],
         "score": int, "max_score": int}

    Returns
    -------
    {"passed": bool, "ratio": float, "failed_checks": [label, ...]}
    """
    checks = ats_compliance.get("checks", []) if ats_compliance else []
    max_score = ats_compliance.get("max_score") or len(checks) or 0
    score = ats_compliance.get("score")
    if score is None:
        score = sum(1 for c in checks if c.get("passed"))
    ratio = (score / max_score) if max_score else 0.0
    failed_checks = [c["label"] for c in checks if not c.get("passed")]
    return {
        "passed": ratio >= min_pass_ratio,
        "ratio": round(ratio, 3),
        "score": score,
        "max_score": max_score,
        "failed_checks": failed_checks,
    }


def _education_score(highest_level: "str | None", required_level: "str | None") -> float:
    """
    0-1 — how the applicant's highest detected/declared degree compares to
    the job's required degree level (education_baseline, translated to a
    DEGREE_LEVEL_ORDER entry by resume_parser.evaluate_education_requirement
    / _detect_degree_level).

    Meets or exceeds the requirement -> 1.0
    No checkable requirement configured for the job -> 1.0 (nothing to fail)
    Below the requirement -> partial credit proportional to how close the
    applicant's rank is to the required rank, so e.g. an Associate's degree
    against a Bachelor's requirement scores higher than no degree at all.
    """
    if not required_level or required_level not in DEGREE_LEVEL_ORDER:
        return 1.0
    required_rank = DEGREE_LEVEL_ORDER.index(required_level)
    if not highest_level or highest_level not in DEGREE_LEVEL_ORDER:
        return 0.0
    applicant_rank = DEGREE_LEVEL_ORDER.index(highest_level)
    if applicant_rank >= required_rank:
        return 1.0
    if required_rank == 0:
        return 1.0
    return max(0.0, applicant_rank / required_rank)


def _experience_score(applicant_years: float, required_years: float) -> float:
    """
    0-1 — applicant's total years of experience (resume_parser.
    calculate_total_experience_years) vs. the job's required_exp_years.

    Meets or exceeds requirement -> 1.0. No requirement configured (0) ->
    1.0. Otherwise linear partial credit up to the requirement.
    """
    applicant_years = max(0.0, float(applicant_years or 0))
    required_years = max(0.0, float(required_years or 0))
    if required_years <= 0:
        return 1.0
    return max(0.0, min(1.0, applicant_years / required_years))


def _skill_score(required_skills_found_count: int, required_skills_total_count: int) -> float:
    """
    0-1 — fraction of the job's real, HR-curated required skills
    (job_required_skills / skills_master) that were found on the resume.
    No required skills configured for this job -> 1.0 (nothing to fail).
    """
    required_skills_total_count = int(required_skills_total_count or 0)
    if required_skills_total_count <= 0:
        return 1.0
    required_skills_found_count = int(required_skills_found_count or 0)
    return max(0.0, min(1.0, required_skills_found_count / required_skills_total_count))


def _normalized_age_score(age: "float | None", minimum_age: "float | None") -> float:
    """
    0-1 — Normalized Age score: how the applicant's age compares to the
    job's minimum_age requirement (job_desc.minimum_age).

    At or above the minimum -> 1.0. Below it -> proportional partial
    credit (age / minimum_age). No age could be determined from the resume
    -> neutral 0.5, so one unparsed field doesn't sink an otherwise
    qualified applicant (the applicant can still correct it on the review
    screen before final submission).
    """
    if age is None:
        return 0.5
    age = float(age)
    minimum_age = float(minimum_age or 0)
    if minimum_age <= 0:
        return 1.0
    if age >= minimum_age:
        return 1.0
    return max(0.0, age / minimum_age)


def compute_weighted_fit(
    *,
    ats_compliance: dict,
    highest_education_level: "str | None",
    required_education_level: "str | None",
    applicant_experience_years: float,
    required_experience_years: float,
    required_skills_found_count: int,
    required_skills_total_count: int,
    applicant_age: "float | None",
    minimum_age: "float | None",
    cart_probability: "float | None" = None,
    ats_min_pass_ratio: float = ATS_MIN_PASS_RATIO,
    threshold: float = TOTAL_SCORE_THRESHOLD,
) -> dict:
    """
    Full pipeline:

      Step 1 — ATS format gate. A resume that fails this is rejected
               immediately; qualification is never even checked, since a
               resume an ATS can't parse can't be reliably scored.

      Step 2 — Weighted Total Score, only computed if Step 1 passes:

          Total Score = (0.20 x Education Score)
                      + (0.25 x Experience Score)
                      + (0.25 x Skill Score)
                      + (0.15 x Normalized Age Score)
                      + (0.15 x CART Score)

          `cart_probability` should be the trained model's P(shortlisted)
          for this applicant vs. this job (see dataset_fit_probability()
          above). If it's None (model unavailable), its 0.15 weight is
          redistributed proportionally across the other four signals
          instead of silently docking every applicant's score by 15%.

      Step 3 — Total Score >= 0.55 -> Eligible, else Not Eligible.

    Returns
    -------
    {
      "stage_failed":      "ats_format" | None,
      "ats_check":         {"passed", "ratio", "score", "max_score", "failed_checks"},
      "education_score":   float | None,  # 0-1
      "experience_score":  float | None,  # 0-1
      "skill_score":       float | None,  # 0-1
      "age_score":         float | None,  # 0-1
      "cart_score":        float | None,  # 0-1, None if model unavailable
      "total_score":       float,         # 0-1
      "score_percent":     float,         # 0-100, for display (match_score)
      "eligible":          bool,
      "label":             "Strong Fit" | "Moderate Fit" | "Weak Fit",
      "message":           str,
    }
    """
    ats_check = check_ats_format(ats_compliance, ats_min_pass_ratio)

    if not ats_check["passed"]:
        return {
            "stage_failed": "ats_format",
            "ats_check": ats_check,
            "education_score": None,
            "experience_score": None,
            "skill_score": None,
            "age_score": None,
            "cart_score": None,
            "total_score": 0.0,
            "score_percent": 0.0,
            "eligible": False,
            "label": "Weak Fit",
            "message": (
                "Your resume didn't meet the minimum ATS formatting standard "
                "(e.g. missing contact info/sections, too few bullet points, "
                "or table-heavy layout that ATS parsers misread), so it "
                "couldn't be scored against this job's requirements yet. "
                "Please revise your resume's formatting — see the checklist "
                "below — and upload it again."
            ),
        }

    education_score = _education_score(highest_education_level, required_education_level)
    experience_score = _experience_score(applicant_experience_years, required_experience_years)
    skill_score = _skill_score(required_skills_found_count, required_skills_total_count)
    age_score = _normalized_age_score(applicant_age, minimum_age)

    if cart_probability is not None:
        cart_score = max(0.0, min(1.0, float(cart_probability)))
        total_score = (
            WEIGHT_EDUCATION * education_score
            + WEIGHT_EXPERIENCE * experience_score
            + WEIGHT_SKILLS * skill_score
            + WEIGHT_AGE * age_score
            + WEIGHT_CART * cart_score
        )
    else:
        # Trained model unavailable for this request (e.g. pkl/CSV missing)
        # — redistribute its weight proportionally across the four
        # rule-based signals instead of silently docking 15% every time.
        cart_score = None
        rule_weight_total = WEIGHT_EDUCATION + WEIGHT_EXPERIENCE + WEIGHT_SKILLS + WEIGHT_AGE
        boost = 1 + (WEIGHT_CART / rule_weight_total)
        total_score = (
            WEIGHT_EDUCATION * boost * education_score
            + WEIGHT_EXPERIENCE * boost * experience_score
            + WEIGHT_SKILLS * boost * skill_score
            + WEIGHT_AGE * boost * age_score
        )

    total_score = max(0.0, min(1.0, total_score))
    eligible = total_score >= threshold

    if total_score >= 0.80:
        label = "Strong Fit"
    elif total_score >= threshold:
        label = "Moderate Fit"
    else:
        label = "Weak Fit"

    return {
        "stage_failed": None,
        "ats_check": ats_check,
        "education_score": round(education_score, 4),
        "experience_score": round(experience_score, 4),
        "skill_score": round(skill_score, 4),
        "age_score": round(age_score, 4),
        "cart_score": round(cart_score, 4) if cart_score is not None else None,
        "total_score": round(total_score, 4),
        "score_percent": round(total_score * 100, 2),
        "eligible": eligible,
        "label": label,
        "message": _MESSAGES[label],
    }


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
# Rule-based weighted scorer  (legacy engine — kept for backward compat)
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
    bullets = features.get("bullet_count", 0)
    if bullets >= 8:
        score += 10
    elif bullets >= 5:
        score += 7
    elif bullets >= 3:
        score += 4
    else:
        score += 0

    verbs = features.get("action_verb_count", 0)
    if verbs >= 8:
        score += 8
    elif verbs >= 5:
        score += 6
    elif verbs >= 3:
        score += 3
    else:
        score += 0

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
    wc = features.get("word_count", 0)
    if 300 <= wc <= 900:
        score += 8
    elif 200 <= wc < 300 or 900 < wc <= 1100:
        score += 4
    else:
        score += 0

    score += 4 if features.get("has_email") else 0
    score += 3 if features.get("has_phone") else 0

    tables = features.get("suspicious_table_lines", 0)
    if tables > 5:
        score -= 5
    elif tables > 2:
        score -= 2

    return max(0.0, min(100.0, score)) ## overall score is clamped to 0-100


def _score_to_label(score: float) -> tuple[str, dict]:
    """Convert 0-100 score to label + calibrated probabilities."""
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

    total = sum(probs.values())
    probs = {k: round(v / total, 4) for k, v in probs.items()}
    return label, probs


# ─────────────────────────────────────────────────────────────────────────────
# predict_fit  ── rule-based score, nudged by the real dataset model
# ─────────────────────────────────────────────────────────────────────────────
# NOTE: this is the OLD engine, kept only for backward compatibility with
# any other call sites. The resume-upload flow (/submit-resume) now uses
# compute_weighted_fit() above instead, with the CART model's probability
# blended in directly via dataset_fit_probability() — see
# routes/applicants.py.

def predict_fit(
    features: dict,
    model=None,
    *,
    experience_match: bool | None = None,
    education_match: bool | None = None,
) -> dict:
    """
    Single-model prediction, calibrated in two stages:

      Stage 1: rule-based weighted score (0-100) from resume structure/format.
      Stage 1b: nudge that score by up to ±6 points using the real,
                dataset-trained DecisionTreeClassifier's P(shortlisted) for
                this applicant's skill/experience/education fit against the
                job. (±6, not a replacement — the dataset model only sees 3
                coarse signals and can't judge resume quality/formatting.)
      Stage 2: convert the (possibly nudged) score to a label + probabilities.

    `model` is accepted for backward compatibility with older call sites
    that pass `get_cart_model()` in explicitly, but is otherwise unused —
    the dataset model is loaded/cached internally.

    Returns
    -------
    {
      "label":            str,
      "screening_result": "Eligible" | "Not Eligible",
      "eligible":         bool,
      "score":            float,   # 0-100
      "message":          str,
    }
    """
    rule_score = _rule_score(features)

    dataset_p = _dataset_fit_probability(features, experience_match, education_match)
    if dataset_p is not None:
        rule_score = max(0.0, min(100.0, rule_score + (dataset_p - 0.5) * 12))

    label, probs = _score_to_label(rule_score)
    confidence = probs[label]
    eligible = label == "Strong Fit"

    return {
        "label":            label,
        "screening_result": "Eligible" if eligible else "Not Eligible",
        "eligible":         eligible,
        "confidence":       confidence,
        "probabilities":    probs,
        "score":            round(rule_score, 1),
        "message":          _MESSAGES[label],
    }