# blueprints/interview.py
from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    flash,
)
import uuid

from app.extensions import mysql, logger, limiter
from app.services.questions import get_questions_for
from app.services.scoring import (
    score_answer_single,
    score_answer_combined,
    score_many,
    generate_detailed_advice,
)

interview_bp = Blueprint("interview", __name__)


@interview_bp.route("/chatapp")
def chat_app():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT email, username, contact_num FROM users WHERE user_id = %s",
        (user_id,),
    )
    user = cur.fetchone()
    if not user:
        cur.close()
        flash("User not found.", "error")
        return redirect(url_for("auth.login"))
    email, username, contact = user

    application_id = request.args.get("application_id", type=int)
    if not application_id:
        cur.close()
        flash("Choose an application before viewing its interview.", "error")
        return redirect(url_for("applicants.dashboard"))

    cur.execute(
        """
        SELECT c.user_name, c.position, c.experience, c.qualification_status,
               c.confidence, c.average_score, c.created_at
        FROM chatbot c
        JOIN applications a ON a.application_id = c.application_id
        JOIN applicants ap ON ap.applicant_id = a.applicant_id
        WHERE c.application_id = %s AND ap.user_id = %s
        """,
        (application_id, user_id),
    )
    result = cur.fetchone()
    cur.close()

    if result:
        name, position, experience, qualified, confidence, average_score, created_at = result
        chatbot_needed = False
    else:
        name = session.get("name")
        position = session.get("position")
        experience = session.get("experience")
        qualified = confidence = average_score = created_at = None
        chatbot_needed = True

    return render_template(
        "chat-app.html",
        name=name,
        email=email,
        contact=contact,
        username=username,
        position=position,
        experience=experience,
        qualified=qualified,
        confidence=confidence,
        average_score=average_score,
        created_at=created_at,
        chatbot_needed=chatbot_needed,
    )


@interview_bp.route("/chat")
def chatbot_page():
    if "user_id" not in session:
        flash("Please submit your application first.", "error")
        return redirect(url_for("applicants.dashboard"))

    user_id = session["user_id"]
    application_id = request.args.get("application_id", type=int)
    if not application_id:
        flash("Choose an eligible application before starting an interview.", "error")
        return redirect(url_for("applicants.dashboard"))

    # The application, not the user, is the interview boundary.
    cur = mysql.connection.cursor()
    cur.execute(
        """
        SELECT u.username, j.job_name,
               COALESCE(a.resume_experience_years,
                   (SELECT SUM(TIMESTAMPDIFF(YEAR, we.start_date,
                   COALESCE(we.end_date, CURDATE()))) FROM work_experience we
                   WHERE we.applicant_id = ap.applicant_id), 0)
        FROM applications a
        JOIN applicants ap ON ap.applicant_id = a.applicant_id
        JOIN users u ON u.user_id = ap.user_id
        JOIN jobs j ON j.job_id = a.job_id
        WHERE a.application_id = %s AND ap.user_id = %s
          AND a.pre_screen_status IN ('Passed Screening', 'Approved', 'Eligible', 'Shortlisted')
        """,
        (application_id, user_id),
    )
    application = cur.fetchone()
    if not application:
        cur.close()
        flash("Section 2 is only available for your eligible application.", "error")
        return redirect(url_for("applicants.dashboard"))

    cur.execute("SELECT id FROM chatbot WHERE application_id = %s", (application_id,))
    existing = cur.fetchone()
    cur.close()

    if existing:
        # Already finished interview – send them to summary or overview instead
        flash("You have already completed the chat interview.", "info")
        return redirect(url_for("summary.summary_report", application_id=application_id))

    name, position, experience = application
    session["active_application_id"] = application_id
    session["name"] = name
    session["position"] = position
    session["experience"] = float(experience or 0)

    return render_template(
        "chatbot.html",
        name=name,
        experience=experience,
        position=position,
        user_id=user_id,
        application_id=application_id,
    )


@interview_bp.route("/get_questions")
def get_questions_route():
    position = request.args.get("position") or session.get(
        "position", "Business Analyst")
    exp = int(request.args.get("experience") or session.get("experience", 0))
    questions = get_questions_for(position, exp)
    if not questions:
        return jsonify({"error": "No questions available"}), 404
    return jsonify({"questions": questions})


@interview_bp.route("/start-interview", methods=["POST"])
def start_interview():
    data = request.get_json()
    position = data.get("position") or session.get(
        "position", "Business Analyst")
    years = int(data.get("years_of_experience")
                or session.get("experience", 0))

    questions = get_questions_for(position, years)
    session_id = str(uuid.uuid4())
    session["session_id"] = session_id
    session["questions"] = questions
    session["question_index"] = 0
    session["answers_history"] = []

    first_question = questions[0] if questions else "No questions found for this role."
    return jsonify({"session_id": session_id, "question": first_question})


@interview_bp.route("/next_question", methods=["POST"])
def next_question():
    data = request.get_json()
    answer = data.get("answer", "")
    current_question = data.get("question", "")

    position = session.get("position", "Business Analyst")
    years = int(session.get("experience", 0))
    questions = get_questions_for(position, years)

    idx = session.get("question_index", 0)

    # save answer
    if answer and current_question:
        results = score_answer_combined(current_question, answer)
        history = session.get("answers_history", [])
        history.append(
            {"question": current_question, "answer": answer, **results}
        )
        session["answers_history"] = history
        idx += 1
        session["question_index"] = idx

    if idx >= len(questions):
        answers_history = session.get("answers_history", [])
        summary = score_many(
            [
                {"question": h["question"], "answer": h["answer"]}
                for h in answers_history
            ]
        )
        advice = generate_detailed_advice(
            summary["answers"], summary["average_score"])
        session["qualification_status"] = summary["qualification_status"]
        return jsonify(
            {
                "finished": True,
                "summary": summary,
                "advice": advice,
                "answers_history": answers_history,
            }
        )

    next_q = questions[idx]
    return jsonify(
        {
            "finished": False,
            "next_question": next_q,
            "feedback": "Thank you for your answer!",
            "qualification_status": "In Progress",
        }
    )


@interview_bp.route("/score_answer", methods=["POST"])
@limiter.limit("10/minute")
def score_answer_route():
    data = request.get_json(force=True)
    question = data.get("question", "").strip()
    answer = data.get("answer", "").strip()

    if not question or not answer:
        return jsonify({"error": "Missing question or answer."}), 400

    # The live chatbot must use the documented hybrid ANN scorer, not the
    # legacy cosine-only helper. This returns semantic, KeyBERT, and final
    # 70/30 ANN score data for the browser and final interview average.
    result = score_answer_combined(question, answer)
    return jsonify(result)


@interview_bp.route("/score", methods=["POST"])
def score_many_route():
    data = request.get_json()
    questions = data.get("questions", [])
    answers = data.get("answers", [])

    if len(questions) != len(answers):
        return jsonify({"error": "Mismatched questions and answers."}), 400

    qa_pairs = [
        {"question": q, "answer": a} for q, a in zip(questions, answers)
    ]
    summary = score_many(qa_pairs)
    return jsonify(summary)


@interview_bp.route("/submit_interview", methods=["POST"])
def submit_interview():
    data = request.get_json()
    answers = data.get("answers", [])  # [{question, answer}, ...]
    summary = score_many(answers)
    advice = generate_detailed_advice(
        summary["answers"], summary["average_score"])
    return jsonify(
        {
            "status": "success",
            "average_score": summary["average_score"],
            "feedback": advice,
            "summary": summary,
        }
    )


@interview_bp.route("/get_interview_summary", methods=["GET"])
def get_interview_summary():
    answers_history = session.get("answers_history", [])
    if not answers_history:
        return jsonify({"error": "No answers submitted yet"}), 400

    qa_pairs = [
        {"question": h["question"], "answer": h["answer"]}
        for h in answers_history
    ]
    summary = score_many(qa_pairs)
    advice = generate_detailed_advice(
        summary["answers"], summary["average_score"])
    return jsonify({"summary": summary, "advice": advice, "answers": answers_history})


@interview_bp.route("/hr/meet/<int:app_id>")
def live_meet(app_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    user_type = session.get("user_type", "Applicant")

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT 
            a.application_id,
            u.username AS applicant_name,
            u.email AS applicant_email,
            j.job_name,
            a.final_interview_status,
            a.final_interview_date,
            a.final_interviewer
        FROM applications a
        JOIN applicants ap ON ap.applicant_id = a.applicant_id
        JOIN users u ON u.user_id = ap.user_id
        JOIN jobs j ON j.job_id = a.job_id
        WHERE a.application_id = %s
    """, (app_id,))
    row = cur.fetchone()
    cur.close()

    if not row:
        flash("Meeting session not found.", "error")
        return redirect(url_for("applicants.dashboard") if user_type == "Applicant" else url_for("hr.hr_dashboard"))

    app_id, applicant_name, applicant_email, job_name, status, f_date, f_interviewer = row

    # Determine if user is HR/Staff or Applicant
    role = "HR" if user_type in ("HR", "Staff", "Admin") else "Applicant"

    return render_template(
        "video_meet.html",
        app_id=app_id,
        role=role,
        applicant_name=applicant_name,
        applicant_email=applicant_email,
        job_name=job_name,
        final_interviewer=f_interviewer or "HR Interviewer",
        status=status
    )
