# blueprints/summary.py
from datetime import datetime
import pdfkit
import os
import json
from flask import (
    Blueprint,
    current_app,
    render_template,
    session,
    request,
    jsonify,
    redirect,
    url_for,
    send_file,
)
from app.extensions import mysql, logger, limiter
from app.services.scoring import score_many
from app.services.pdf_utils import generate_pdf_summary
from app.services.overall_status import sync_overall_status

summary_bp = Blueprint("summary", __name__)


@summary_bp.route("/summary")
def summary_page():
    try:
        return render_template("summary.html")
    except Exception as e:
        logger.error(f"Error rendering summary.html: {e}")
        return f"<h1>Error rendering summary:</h1><pre>{e}</pre>", 500


@summary_bp.route("/summary_report")
def summary_report():
    user_id = session.get("user_id")
    if not user_id:
        return "User session not found.", 400

    application_id = request.args.get("application_id", type=int)
    if not application_id:
        return "Application not specified.", 400

    cur = mysql.connection.cursor()
    cur.execute(
        """
        SELECT c.* FROM chatbot c
        JOIN applications a ON a.application_id = c.application_id
        JOIN applicants ap ON ap.applicant_id = a.applicant_id
        WHERE c.application_id = %s AND ap.user_id = %s
        """,
        (application_id, user_id),
    )
    row = cur.fetchone()
    if not row:
        return "No summary found for this user.", 404

    keys = [desc[0] for desc in cur.description]
    data = dict(zip(keys, row))

    cur.execute(
        "SELECT overall_status FROM application_overall_status WHERE application_id = %s",
        (application_id,),
    )
    overall_row = cur.fetchone()
    overall_status = overall_row[0] if overall_row else "Pending"
    cur.close()

    assessment_data = json.loads(data.get("assessment_data") or "[]")
    advice_list = json.loads(data.get("advice") or "[]")

    return render_template(
        "summary.html",
        name=data.get("user_name"),
        position=data.get("position"),
        skills=data.get("skills"),
        qualification_status=data.get("qualification_status"),
        overall_status=overall_status,
        confidence=data.get("confidence"),
        average_score=data.get("average_score") or 0,  # <-- add this
        assessment_data=assessment_data,
        advice_list=advice_list,
    )


@summary_bp.route("/save_summary_report", methods=["POST"])
@limiter.limit("10/minute")
def save_summary_report():
    try:
        data = request.get_json(force=True)
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "User not logged in or session expired."}), 403

        try:
            application_id = int(data.get("application_id"))
        except (TypeError, ValueError):
            return jsonify({"error": "A valid application_id is required."}), 400

        user_name = data.get("user_name")
        position = data.get("position")
        experience = data.get("experience", "")
        skills = data.get("skills", [])
        qualification_status = data.get("qualification_status", "")
        advice = data.get("advice", [])
        assessment_data = data.get("assessment_data", [])

        # Scores and the final qualification must come from the server-side
        # ANN + SentenceTransformer + KeyBERT implementation. The browser may
        # display provisional per-answer feedback, but it must not be able to
        # submit a fabricated average or status.
        qa_pairs = [
            {"question": item.get("question", ""), "answer": item.get("answer", "")}
            for item in assessment_data
            if isinstance(item, dict) and item.get("question") and item.get("answer")
        ]
        if not qa_pairs:
            return jsonify({"error": "At least one scored interview answer is required."}), 400

        scored_summary = score_many(qa_pairs)
        scored_answers = [
            {**pair, **result}
            for pair, result in zip(qa_pairs, scored_summary["answers"])
        ]
        qualification_status = scored_summary["qualification_status"]
        average_score = scored_summary["average_score"]
        qualified_count = sum(
            1 for result in scored_summary["answers"]
            if result.get("qualification_status") == "Qualified"
        )
        confidence = round((qualified_count / len(scored_answers)) * 100, 2)
        assessment_data = scored_answers

        if not user_name or not position:
            return jsonify({"error": "Missing user_name or position"}), 400

        cur = mysql.connection.cursor()
        cur.execute(
            """
            SELECT a.application_id FROM applications a
            JOIN applicants ap ON ap.applicant_id = a.applicant_id
            WHERE a.application_id = %s AND ap.user_id = %s
              AND a.pre_screen_status IN ('Passed Screening', 'Approved', 'Eligible', 'Shortlisted')
            """,
            (application_id, user_id),
        )
        if not cur.fetchone():
            cur.close()
            return jsonify({"error": "Interview is not available for this application."}), 403
        cur.execute(
            """
            INSERT INTO chatbot
            (user_id, application_id, user_name, position, experience, skills,
             qualification_status, advice, assessment_data,
             confidence, average_score, created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
            """,
            (
                user_id,
                application_id,
                user_name,
                position,
                experience,
                json.dumps(skills),
                qualification_status,
                json.dumps(advice),
                json.dumps(assessment_data),
                confidence,
                average_score,
            ),
        )

        # Section 2 result just landed — recompute the combined verdict so
        # the summary report can show "Passed Screening" / "Rejected"
        # alongside the raw chatbot qualification_status.
        overall_status = sync_overall_status(cur, application_id)

        mysql.connection.commit()
        cur.close()

        # 👉 here is a good place to trigger your "step 2" email if you want
        # from app.services.email_service import send_step2_email
        # send_step2_email(user_id, qualification_status, confidence)

        return jsonify(
            {
                "message": "Summary report saved.",
                "redirect": url_for("summary.summary_page"),
                "overall_status": overall_status,
            }
        ), 201
    except Exception as e:
        logger.error(f"Error in save_summary_report: {e}")
        return jsonify({"error": "Failed to save summary.", "details": str(e)}), 500


@summary_bp.route("/download_summary")
def download_summary():
    user_name = session.get("name", "Candidate")
    position = session.get("position", "Unknown")
    skills = session.get("skills", [])
    status = session.get("qualification_status", "Not Qualified")

    if isinstance(skills, list):
        skills_str = ", ".join(skills)
    else:
        skills_str = str(skills)

    path = generate_pdf_summary(user_name, position, skills_str, status)
    return send_file(path, as_attachment=True)


@summary_bp.route("/generate_pdf", methods=["POST"])
def generate_pdf():
    data = request.get_json()

    user_name = data.get("user_name", "Candidate")
    role = data.get("role", "Unknown")
    skills = data.get("skills", "")
    qualification_status = data.get("qualification_status", "Not Qualified")
    advice_list = data.get("advice_list", [])
    assessment_data = data.get("assessment_data", [])

    rendered = render_template(
        "summary.html",
        user_name=user_name,
        role=role,
        skills_str=skills,
        qualification_status=qualification_status,
        advice_list=advice_list,
        assessment_data=assessment_data,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"summary_reports/{user_name}_summary_{timestamp}.pdf"
    os.makedirs("summary_reports", exist_ok=True)

    config = pdfkit.configuration(wkhtmltopdf="/usr/local/bin/wkhtmltopdf")
    pdfkit.from_string(rendered, filename, configuration=config)

    with open(filename, "rb") as f:
        pdf_data = f.read()

    resp = current_app.response_class(pdf_data, mimetype="application/pdf")
    resp.headers[
        "Content-Disposition"] = f"attachment; filename={os.path.basename(filename)}"
    return resp