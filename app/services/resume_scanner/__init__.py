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
    extract_declared_experience_years,
    calculate_total_experience_years,
    evaluate_education_requirement,
    split_full_name,
)
from .cart_model import (
    load_or_train_model,
    get_cart_model as _cart_model_get_cart_model,
    predict_fit,
    compute_weighted_fit,
    predict_fit_from_match_scores,
    check_ats_format,
    dataset_fit_probability,
)

import logging

logger = logging.getLogger("job-interview-platform.resume_scanner")


def get_cart_model():
    """
    Thin logging wrapper around cart_model.get_cart_model().

    NOTE: an earlier version of this function redefined its own
    module-level `_CART_MODEL` cache and shadowed the `get_cart_model`
    imported from cart_model.py above — meaning cart_model.get_cart_model()
    and resume_scanner.get_cart_model() were maintaining two SEPARATE
    cached model objects (both trained from the same source, so this
    wasn't causing incorrect predictions, but it meant two copies of the
    model sat in memory and "the cache" wasn't actually a single cache).
    This now delegates to cart_model.py's cache directly, so there is
    exactly one cached model object for the whole process — this wrapper
    only adds logging on top.
    """
    try:
        model = _cart_model_get_cart_model()
        logger.info("✅ Resume-scanner CART model ready.")
        return model
    except Exception as e:
        logger.error(f"❌ Failed to load/train resume-scanner CART model: {e}")
        raise


__all__ = [
    "extract_text",
    "extract_all_info",
    "extract_keywords_from_job_desc",
    "extract_declared_experience_years",
    "calculate_total_experience_years",
    "evaluate_education_requirement",
    "split_full_name",
    "predict_fit",
    "predict_fit_from_match_scores",
    "compute_weighted_fit",
    "check_ats_format",
    "get_cart_model",
    "dataset_fit_probability",
]