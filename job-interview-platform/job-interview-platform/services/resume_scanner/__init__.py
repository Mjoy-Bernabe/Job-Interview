# services/resume_scanner/__init__.py
"""
Resume Scanner engine, adapted from the standalone `scanner_updated` project
into JIPS as an internal service module.

This package intentionally has NO Flask / MySQL code of its own — it only
does:
    file -> text -> ATS features -> CART "Strong/Moderate/Weak Fit" label

All DB writes (users/applicants/applications/work_experience/educations/
skills_master/applicant_skills — same auth_db columns JIPS already uses)
are done in blueprints/applicants.py using the app's existing `mysql`
connection, so the resume-scanning applicant goes through the exact same
`applications.screening_status` pipeline as a manually-filled application,
and can proceed to the interview-simulation phase (blueprints/interview.py)
the same way.
"""
from .parser import (
    extract_text,
    extract_all_info,
    extract_keywords_from_job_desc,
    calculate_total_experience_years,
    evaluate_education_requirement,
)
from .cart_model import load_or_train_model, predict_fit

import logging

logger = logging.getLogger("job-interview-platform.resume_scanner")

_CART_MODEL = None


def get_cart_model():
    """
    Lazily loads (or trains, on first run) the CART fit-classifier once per
    process and reuses it afterwards — mirrors how extensions.py loads the
    SentenceTransformer/KeyBERT singletons at startup.
    """
    global _CART_MODEL
    if _CART_MODEL is None:
        try:
            _CART_MODEL = load_or_train_model()
            logger.info("✅ Resume-scanner CART model ready.")
        except Exception as e:
            logger.error(f"❌ Failed to load/train resume-scanner CART model: {e}")
            raise
    return _CART_MODEL


__all__ = [
    "extract_text",
    "extract_all_info",
    "extract_keywords_from_job_desc",
    "calculate_total_experience_years",
    "evaluate_education_requirement",
    "predict_fit",
    "get_cart_model",
]
