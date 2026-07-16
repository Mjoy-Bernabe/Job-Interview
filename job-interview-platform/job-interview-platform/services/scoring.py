# services/scoring.py
import numpy as np
from typing import List, Dict, Any
from extensions import sentence_model, kw_model, logger
from sklearn.metrics.pairwise import cosine_similarity
import os

# 1. Import TensorFlow to load your new model
from tensorflow.keras.models import load_model 

# 2. Load the trained model once when the Flask server starts
model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'interview_scoring_ann.keras')
try:
    ann_model = load_model(model_path)
    logger.info("✅ ANN Scoring Model loaded successfully!")
except Exception as e:
    logger.error(f"❌ Failed to load ANN model: {e}")
    ann_model = None

def _encode(text: str):
    if not sentence_model:
        raise RuntimeError("SentenceTransformer model not loaded.")
    return sentence_model.encode([text])[0]

def explain_score(score: float) -> str:
    if score >= 0.60:
        return "Excellent and highly relevant answer."
    if score >= 0.40:
        return "Good answer with relevant content, but missing some key details."
    return "Answer lacks relevance or detail. Try to address the question more directly."

def score_answer_combined(question: str, ideal_answer: str, candidate_answer: str) -> Dict[str, Any]:
    """Advanced ANN Scoring: S-BERT + Keyword Overlap -> ANN Prediction"""
    if not question.strip() or not candidate_answer.strip() or not ideal_answer.strip():
        return _empty_result()

    try:
        # 1. Feature 1: S-BERT Semantic Similarity (Compare candidate to the IDEAL answer)
        ideal_emb = _encode(ideal_answer)
        cand_emb = _encode(candidate_answer)
        cosine_score = float(cosine_similarity([ideal_emb], [cand_emb])[0][0])

        # 2. Feature 2: KeyBERT Keyword Overlap
        if kw_model:
            kw_pairs = kw_model.extract_keywords(ideal_answer, top_n=5)
            keywords = [k[0].lower() for k in kw_pairs]
        else:
            keywords = []

        answer_words = set(candidate_answer.lower().split())
        matched = [kw for kw in keywords if kw in answer_words]
        keyword_score = len(matched) / len(keywords) if keywords else 0.0

        # 3. Feature 3: Answer Length
        word_count = len(answer_words)

        # 4. 🧠 ANN INFERENCE (The magic happens here)
        fallback_score = (cosine_score * 0.7) + (keyword_score * 0.3)

        if ann_model:
            features = np.array([[cosine_score, keyword_score, word_count]])
            ann_prediction = float(ann_model.predict(features, verbose=0)[0][0])
            
            # SAFETY NET: Blend ANN (60%) with fallback (40%) so semantically
            # correct answers are never zeroed out by an overly strict ANN.
            final_score = (ann_prediction * 0.6) + (fallback_score * 0.4)

            # 🔍 DEBUG: Log all raw scoring components
            logger.info(
                f"🔍 [SCORE DEBUG] Q='{question[:50]}...' | "
                f"cosine={cosine_score:.4f}  keyword={keyword_score:.4f}  words={word_count}  "
                f"ANN_raw={ann_prediction:.4f}  fallback={fallback_score:.4f}  "
                f"BLENDED(pre-round)={final_score:.4f}"
            )
        else:
            # Fallback if the .keras file is missing
            final_score = fallback_score
            logger.info(
                f"🔍 [SCORE DEBUG - NO ANN] Q='{question[:50]}...' | "
                f"cosine={cosine_score:.4f}  keyword={keyword_score:.4f}  words={word_count}  "
                f"fallback={fallback_score:.4f}"
            )

        final_score = round(final_score, 2)

        # 5. Determine Final Status (relaxed thresholds: 0.60 = Qualified, 0.40 = Partial)
        status = (
            "Qualified" if final_score >= 0.60
            else "Partially Qualified" if final_score >= 0.40
            else "Not Qualified"
        )
        feedback = explain_score(final_score)
        logger.info(f"🔍 [SCORE RESULT] final_score={final_score}  status={status}")

        return {
            "score": final_score,
            "qualification_status": status,
            "feedback": feedback,
            "matched_keywords": matched,
            "total_keywords": keywords,
            "cosine_score": round(cosine_score, 2),
            "keyword_score": round(keyword_score, 2),
        }
    except Exception as e:
        logger.error(f"❌ Error in score_answer_combined: {e}")
        return _empty_result()

def _empty_result() -> Dict[str, Any]:
    return {
        "score": 0.0,
        "qualification_status": "Error",
        "feedback": "An error occurred while scoring.",
        "matched_keywords": [],
        "total_keywords": [],
        "cosine_score": 0.0,
        "keyword_score": 0.0,
    }

def score_many(qa_pairs: List[Dict[str, str]]) -> Dict[str, Any]:
    total = 0.0
    results = []

    for pair in qa_pairs:
        q = pair.get("question", "")
        ideal = pair.get("ideal_answer", "")  # Make sure your frontend/db passes the ideal_answer!
        a = pair.get("answer", "")
        
        # If your previous system didn't use ideal_answers, you might need to adjust this part in your routes!
        res = score_answer_combined(q, ideal, a)
        results.append(res)
        total += res["score"]

    avg = round(total / len(results), 2) if results else 0.0
    status = (
        "Qualified" if avg >= 0.60 else
        "Partially Qualified" if avg >= 0.40 else
        "Not Qualified"
    )
    logger.info(f"🔍 [SCORE_MANY] avg_score={avg}  status={status}  total_questions={len(results)}")

    return {
        "average_score": avg,
        "qualification_status": status,
        "answers": results,
    }

def compute_answer_score(question: str, answer: str) -> float:
    """Simple cosine similarity between question and answer."""
    if not question.strip() or not answer.strip():
        return 0.0
    try:
        q_emb = _encode(question)
        a_emb = _encode(answer)
        score = cosine_similarity([q_emb], [a_emb])[0][0]
        return round(float(score), 2)
    except Exception as e:
        logger.error(f"❌ Error in compute_answer_score: {e}")
        return 0.0


def score_answer_single(question: str, answer: str) -> Dict[str, Any]:
    """Original basic scoring fallback (used by /score_answer endpoint)."""
    score = compute_answer_score(question, answer)
    feedback = explain_score(score)
    status = (
        "Qualified" if score >= 0.60
        else "Partially Qualified" if score >= 0.40
        else "Not Qualified"
    )
    logger.info(f"🔍 [SINGLE SCORE] Q='{question[:50]}...' score={score}  status={status}")
    return {
        "score": score,
        "qualification_status": status,
        "feedback": feedback,
    }

def generate_detailed_advice(qa_results: List[Dict[str, Any]], avg_score: float) -> str:
    if not qa_results:
        return "No advice available."

    if avg_score >= 0.60:
        base = "You performed very well overall. Your answers were relevant and detailed."
    elif avg_score >= 0.40:
        base = "Your interview performance is decent, but there is room to improve some answers."
    else:
        base = "Your answers suggest you should prepare more before the next interview."

    # find lowest score question for targeted advice
    lowest = min(qa_results, key=lambda r: r.get("score", 0))
    suggestion = (
        "Try to give more concrete examples and connect them clearly to the question."
    )

    return f"{base} Focus especially on questions where your score was low. {suggestion}"