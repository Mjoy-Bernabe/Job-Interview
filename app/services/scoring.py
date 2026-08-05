# services/scoring.py
import re
from typing import List, Dict, Any

from app.extensions import get_keyword_model, get_sentence_model, logger
from sklearn.metrics.pairwise import cosine_similarity

from app.services import simpleneuralnetwork as ann

# An answer at/above this many words is treated as "fully developed" for the
# length feature (kept as a soft signal, weight 0 until the ANN is trained).
FULL_LENGTH_WORDS = 40


def _encode(text: str):
    model = get_sentence_model()
    return model.encode([text])[0]


def _normalize(text: str) -> str:
    """Lowercase and strip punctuation, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _keyword_hit(keyword: str, answer_norm: str, answer_tokens: List[str]) -> bool:
    """
    True if `keyword` (which may be a multi-word KeyBERT phrase, e.g.
    'java database' or 'jdbc connection') is present in the answer.

    The old implementation only checked exact single-token membership in
    answer.lower().split(), which meant multi-word keyphrases (the norm for
    KeyBERT output) almost never matched, silently driving keyword_score
    toward 0 for good answers. This checks:
      1. exact phrase / substring match against the normalized answer, and
      2. a light stem match (first 5 chars) for single-word keywords, so
         'database' still matches 'databases' / 'databased'.
    """
    kw = _normalize(keyword)
    if not kw:
        return False
    if kw in answer_norm:
        return True
    if " " not in kw and len(kw) >= 4:
        root = kw[:5] if len(kw) > 5 else kw
        return any(tok.startswith(root) for tok in answer_tokens if len(tok) >= 3)
    return False


def explain_score(score: float) -> str:
    if score > 0.8:
        return "Excellent and highly relevant answer."
    if score > 0.6:
        return "Good answer with relevant content."
    if score > 0.4:
        return "Partially relevant. Add more detail and examples."
    return "Answer lacks relevance. Try to address the question more directly."


def compute_answer_score(question: str, answer: str) -> float:
    """Simple cosine similarity between question and answer."""
    if not question.strip() or not answer.strip():
        return 0.0
    try:
        q_emb = _encode(question)
        a_emb = _encode(answer)
        score = cosine_similarity([q_emb], [a_emb])[0][0]
        score = max(0.0, min(1.0, float(score)))  # cosine can be <0; clip to [0,1]
        return round(score, 2)
    except Exception as e:
        logger.error(f"❌ Error in compute_answer_score: {e}")
        return 0.0


def score_answer_single(question: str, answer: str) -> Dict[str, Any]:
    score = compute_answer_score(question, answer)
    feedback = explain_score(score)
    status = "Qualified" if score >= 0.6 else "Not Qualified"
    return {
        "score": score,
        "qualification_status": status,
        "feedback": feedback,
    }


def score_answer_combined(question: str, answer: str) -> Dict[str, Any]:
    """Cosine similarity + KeyBERT keyword overlap, fused through the ANN."""
    if not question.strip() or not answer.strip():
        return {
            "score": 0.0,
            "qualification_status": "Not Qualified",
            "feedback": "Please provide a complete answer to score it.",
            "matched_keywords": [],
            "missing_keywords": [],
            "total_keywords": [],
            "cosine_score": 0.0,
            "keyword_score": 0.0,
        }

    try:
        q_emb = _encode(question)
        a_emb = _encode(answer)
        cosine_score = cosine_similarity([q_emb], [a_emb])[0][0]
        cosine_score = max(0.0, min(1.0, float(cosine_score)))

        keyword_model = get_keyword_model()
        kw_pairs = keyword_model.extract_keywords(
            question, keyphrase_ngram_range=(1, 2), top_n=5
        )
        keywords = [item[0] for item in kw_pairs]

        answer_norm = _normalize(answer)
        answer_tokens = answer_norm.split()

        matched = [kw for kw in keywords if _keyword_hit(kw, answer_norm, answer_tokens)]
        missing = [kw for kw in keywords if kw not in matched]
        keyword_score = len(matched) / len(keywords) if keywords else 0.0

        length_score = min(len(answer_tokens) / FULL_LENGTH_WORDS, 1.0)

        final_score = ann.score(cosine_score, keyword_score, length_score)
        final_score = round(final_score, 2)

        status = (
            "Qualified"
            if final_score >= 0.7
            else "Partially Qualified"
            if final_score >= 0.5
            else "Not Qualified"
        )

        return {
            "score": final_score,
            "qualification_status": status,
            "feedback": explain_score(final_score),
            "matched_keywords": matched,
            "missing_keywords": missing,
            "total_keywords": keywords,
            "cosine_score": round(cosine_score, 2),
            "keyword_score": round(keyword_score, 2),
        }
    except Exception as e:
        logger.error(f"❌ Error in score_answer_combined: {e}")
        return {
            "score": 0.0,
            "qualification_status": "Error",
            "feedback": "The answer could not be scored. Please try again.",
            "matched_keywords": [],
            "missing_keywords": [],
            "total_keywords": [],
            "cosine_score": 0.0,
            "keyword_score": 0.0,
        }


def score_many(qa_pairs: List[Dict[str, str]]) -> Dict[str, Any]:
    total = 0.0
    results = []

    for pair in qa_pairs:
        q = pair.get("question", "")
        a = pair.get("answer", "")
        res = score_answer_combined(q, a)
        results.append(res)
        total += res["score"]

    avg = round(total / len(results), 2) if results else 0.0

    # Documented model: "Qualified if AverageScore > 0.60, otherwise Not
    # Qualified" - a binary decision. (Previously this used a 3-way
    # >=0.7/>=0.5 split here, which didn't match the write-up.)
    qualification_status = "Qualified" if avg > 0.60 else "Not Qualified"

    # Kept separately as a more granular tier for HR-facing views/analytics;
    # does not replace the documented binary decision above.
    score_tier = (
        "Qualified" if avg >= 0.7 else
        "Partially Qualified" if avg >= 0.5 else
        "Not Qualified"
    )

    return {
        "average_score": avg,
        "qualification_status": qualification_status,
        "score_tier": score_tier,
        "answers": results,
    }


def generate_detailed_advice(qa_results: List[Dict[str, Any]], avg_score: float) -> str:
    if not qa_results:
        return "No advice available."

    if avg_score > 0.60:
        base = "You performed well overall. Your answers were relevant and detailed."
    elif avg_score >= 0.5:
        base = "Your interview performance is decent, but there is room to improve some answers."
    else:
        base = "Your answers suggest you should prepare more before the next interview."

    # find lowest score question for targeted advice
    lowest = min(qa_results, key=lambda r: r.get("score", 0))
    missing = lowest.get("missing_keywords") or []

    if missing:
        kw_list = ", ".join(missing[:3])
        suggestion = (
            f"On your weakest answer, try covering topics like: {kw_list}. "
            "Ground your response with a concrete example tied to the question."
        )
    else:
        suggestion = (
            "Try to give more concrete examples and connect them clearly to the question."
        )

    return f"{base} Focus especially on questions where your score was low. {suggestion}"
