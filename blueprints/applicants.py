import os
import json
import uuid
from datetime import datetime
from urllib.parse import unquote

import numpy as np

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
    current_app,
)
from werkzeug.utils import secure_filename

from extensions import mysql, logger
from services.email_service import send_step1_completed_email  # ⬅️ NEW IMPORT

# CART (Decision Tree)
from sklearn.tree import DecisionTreeClassifier

# Resume-scanning engine (ported from scanner_updated) — text extraction,
# ATS feature scoring, and the "Strong/Moderate/Weak Fit" CART classifier.
from services import resume_scanner
from services.overall_status import sync_overall_status

applicants_bp = Blueprint("applicants", __name__)


# ---------- CART (Decision Tree) MODEL FOR PRESCREEN & APPLICATION ----------

# Education mapping
CART_EDU_MAP = {
    "high_school": 1,
    "vocational": 2,
    "associate": 3,
    "bachelor": 4,
    "master": 5,
    "phd": 6,
}


def cart_normalize_age(age):
    age = max(20, min(age, 65))  # clamp between 20–65
    return (age - 20) / (65 - 20)


def cart_experience_score(exp_years):
    return min(exp_years, 15) / 15.0


def cart_skill_score(skill_count):
    return min(skill_count, 10) / 10.0


# Sample training data
raw_applicants_cart = [
    ("bachelor",    25,  3,  4, 1),
    ("high_school", 21,  0,  1, 0),
    ("master",      32,  8,  7, 1),
    ("bachelor",    45, 15, 10, 1),
    ("vocational",  28,  2,  2, 0),
    ("associate",   23,  1,  3, 0),
    ("phd",         38, 10,  6, 1),
    ("bachelor",    50,  5,  5, 1),
    ("high_school", 60, 15,  2, 0),
    ("master",      27,  4,  8, 1),
]

X_cart = []
y_cart = []

for edu, age, exp, skills, label in raw_applicants_cart:
    edu_score = CART_EDU_MAP[edu]
    age_norm = cart_normalize_age(age)
    exp_s = cart_experience_score(exp)
    skill_s = cart_skill_score(skills)
    X_cart.append([edu_score, age_norm, exp_s, skill_s])
    y_cart.append(label)

X_cart = np.array(X_cart)
y_cart = np.array(y_cart)

# CART model trained once at app startup
cart_model = DecisionTreeClassifier(
    criterion="gini",
    max_depth=3,
    random_state=42,
)
cart_model.fit(X_cart, y_cart)


def cart_predict_from_form(age, education_level, experience, skills_raw: str):
    """
    Use the global cart_model (DecisionTreeClassifier) to compute
    score and predicted status from form data.
    """
    # education mapping normalized fallback
    edu_clean = education_level.lower().replace("'", "").replace(" ", "_") if education_level else "high_school"
    edu_score = CART_EDU_MAP.get(edu_clean, 1)

    # normalized & derived scores
    age_norm = cart_normalize_age(age)
    exp_s = cart_experience_score(experience)

    skills_list = [s.strip() for s in skills_raw.split(",") if s.strip()]
    skill_count = len(skills_list)
    skill_s = cart_skill_score(skill_count)

    features = np.array([[edu_score, age_norm, exp_s, skill_s]])

    proba = cart_model.predict_proba(features)[0][1]  # prob of class 1
    pred = cart_model.predict(features)[0]

    status = "Eligible" if pred == 1 else "Not Eligible"

    return {
        "status": status,
        "model_score": float(proba),  # 0–1
        "probability_percent": round(float(proba) * 100, 2),
        "features": {
            "edu_score": edu_score,
            "age_norm": float(age_norm),
            "exp_score": float(exp_s),
            "skill_score": float(skill_s),
            "skill_count": skill_count,
        },
    }


def allowed_resume_file(filename: str) -> bool:
    allowed = current_app.config.get("ALLOWED_RESUME_EXTENSIONS", {"pdf", "doc", "docx"})
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


# ---------- Pending resume-scan holding area ----------
#
# The scanner reads/parses the resume immediately on upload, but nothing is
# written to the database yet. Instead the parsed result is parked on disk
# as a small JSON file ("pending scan") keyed by a random token. The token
# is handed to the applicant's browser (hidden form field) and mirrored in
# their session, so the review page (resume_review.html) can show the
# scanned data, let the applicant correct anything the scanner misread,
# and only once they press "Confirm & Submit" does /confirm-resume-application
# write the (possibly-edited) data into the database.

def _pending_scan_dir() -> str:
    upload_dir = current_app.config.get("UPLOAD_FOLDER", "uploads")
    if not os.path.isabs(upload_dir):
        upload_dir = os.path.join(current_app.root_path, upload_dir)
    pending_dir = os.path.join(upload_dir, "pending_scans")
    os.makedirs(pending_dir, exist_ok=True)
    return pending_dir


def _save_pending_scan(data: dict) -> str:
    token = uuid.uuid4().hex
    path = os.path.join(_pending_scan_dir(), f"{token}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return token


def _load_pending_scan(token: str) -> dict | None:
    if not token:
        return None
    path = os.path.join(_pending_scan_dir(), f"{token}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _delete_pending_scan(token: str) -> None:
    if not token:
        return
    path = os.path.join(_pending_scan_dir(), f"{token}.json")
    try:
        os.remove(path)
    except OSError:
        pass


# ---------- Dashboard & Application Pipeline ----------


@applicants_bp.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("You need to log in first.", "error")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    cur = mysql.connection.cursor()

    # Get baseline profile credentials from 'users' (normalized column name: user_type)
    cur.execute(
        "SELECT email, username, contact_num, user_type FROM users WHERE user_id = %s",
        (user_id,),
    )
    user = cur.fetchone()
    if not user:
        cur.close()
        flash("User not found.", "error")
        return redirect(url_for("auth.login"))
    email, username, contact, user_type = user

    # Security check: only Applicant accounts may view this dashboard.
    # Without this, a logged-in HR/Admin session could load /dashboard
    # directly by URL and see the applicant portal.
    if (user_type or "").strip().lower() != "applicant":
        cur.close()
        session.clear()
        flash("Please log in through the correct portal.", "error")
        return redirect(url_for("auth.staff_login"))

    # Retrieve ALL of the candidate's applications (one row per job applied to).
    # NOTE: this used to be LIMIT 1 (latest application only), which meant the
    # "Application Info" panel showed the same (most recent) job's phase-1
    # data no matter which job card the applicant clicked on. We now fetch
    # every application and key the per-job data by job_id so each job's
    # detail view only ever shows that job's own information.
    cur.execute(
        """
        SELECT
            app.application_id,
            app.job_id,
            u.username,
            u.email,
            u.contact_num,
            j.job_name,
            app.pre_screen_status,
            COALESCE(
                app.resume_experience_years,
                (SELECT SUM(TIMESTAMPDIFF(YEAR, start_date, COALESCE(end_date, CURDATE())))
                 FROM work_experience
                 WHERE applicant_id = a.applicant_id),
                0
            ) AS years_experience,
            (SELECT degree_level FROM educations WHERE applicant_id = a.applicant_id ORDER BY graduation_year DESC LIMIT 1) AS education_level,
            (SELECT GROUP_CONCAT(sm.skill_name SEPARATOR ', ') 
             FROM applicant_skills ask 
             JOIN skills_master sm ON sm.skill_id = ask.skill_id 
             WHERE ask.applicant_id = a.applicant_id) AS skills,
            TIMESTAMPDIFF(YEAR, a.date_of_birth, CURDATE()) AS age,
            app.final_interview_status,
            app.final_interview_date,
            app.final_interviewer
        FROM applications app
        JOIN applicants a ON a.applicant_id = app.applicant_id
        JOIN users u ON u.user_id = a.user_id
        JOIN jobs j ON j.job_id = app.job_id
        WHERE u.user_id = %s
        ORDER BY app.application_id DESC
        """,
        (user_id,),
    )
    app_rows = cur.fetchall()

    applications_by_job = {}
    applicant = None
    for r in app_rows:
        job_entry = {
            "id": r[0],
            "job_id": r[1],
            "user_id": user_id,
            "name": r[2],
            "email": r[3],
            "contact": r[4],
            "position": r[5],
            "eligibility": "Eligible" if r[6] == "Passed Screening" else "Not Eligible",
            "yearexperience": float(r[7]) if r[7] is not None else 0,
            "level": "N/A",
            "status": r[6],  # screening_status string
            "confidence": 75,  # static fallback when not using live prediction state
            "address": None,
            "education_level": r[8] or "N/A",
            "skills": r[9] or "None listed",
            "age": int(r[10]) if r[10] is not None else None,
            "final_interview_status": r[11] or "Pending",
            "final_interview_date": str(r[12]) if r[12] else "",
            "final_interviewer": r[13] or ""
        }
        # Keep only the latest application per job_id (rows are already
        # ordered newest-first, so the first time we see a job_id wins).
        applications_by_job.setdefault(r[1], job_entry)

        if applicant is None:
            # Most recent application overall — used for the general
            # "Applicant Info" / Profile summary, not for the per-job cards.
            applicant = job_entry
            # Sync simple session data for backward compatibility
            session["position"] = r[5]
            session["experience"] = job_entry["yearexperience"]
            session["name"] = r[2]

    # Fetch available job list and real-time candidate limit statistics
    cur.execute(
        """
        SELECT j.job_id, j.job_name, j.max_applicants, COUNT(app.application_id) AS current_count
        FROM jobs j
        LEFT JOIN applications app ON app.job_id = j.job_id
        GROUP BY j.job_id, j.job_name, j.max_applicants
        ORDER BY j.job_name ASC
        """
    )
    positions = cur.fetchall()
    position_limits = [
        {
            "id": p[0],
            "position": p[1],
            "max_allowed": p[2],
            "current_count": p[3],
            "is_full": bool(p[2] and p[3] >= p[2]),
        }
        for p in positions
    ]

    # Pull dynamic jobs and detailed description requirements
    cur.execute(
        """
        SELECT
            j.job_id,
            j.job_name,
            j.application_status,
            j.application_deadline,
            j.max_applicants,
            jd.department,
            jd.employment_type,
            jd.education_baseline,
            jd.required_exp_years,
            jd.minimum_age,
            EXISTS (
                SELECT 1
                FROM applications app
                JOIN applicants a2 ON a2.applicant_id = app.applicant_id
                WHERE app.job_id = j.job_id AND a2.user_id = %s
            ) AS has_applied
        FROM jobs j
        LEFT JOIN job_desc jd ON jd.job_id = j.job_id
        ORDER BY jd.department ASC, j.job_name ASC
        """,
        (user_id,),
    )
    rows = cur.fetchall()

    available_jobs = []

    for p in rows:

        app = applications_by_job.get(p[0])   # p[0] = job_id

        phase1 = None
        phase2 = None

        if app:
            # Section 1
            phase1 = app["eligibility"]

            # Section 2
            if app.get("chatbot"):
                phase2 = app["chatbot"]["qualification_status"]

        available_jobs.append({
            "id": p[0],
            "position": p[1],
            "application_status": p[2],
            "deadline_date": p[3],
            "max_allowed": p[4],
            "category": p[5] or "General",
            "form_access": p[6],
            "employment_type": p[6],
            "education_level": p[7],
            "experience_years": p[8],
            "min_age": p[9],
            "has_applied": bool(p[10]),

            # NEW
            "phase1_status": phase1,
            "phase2_status": phase2,
        })

    # Fetch Section 2 results by application ID. A job title is not a safe
    # boundary for independent applications.
    cur.execute(
        """
        SELECT application_id, position, qualification_status, average_score
        FROM chatbot
        WHERE user_id = %s AND application_id IS NOT NULL
        """,
        (user_id,),
    )
    chatbot_by_application = {}
    for application_id, pos, qual_status, avg_score in cur.fetchall():
        chatbot_by_application[application_id] = {
            "position": pos,
            "qualification_status": qual_status,
            "average_score": float(avg_score) if avg_score is not None else 0,
        }

    chatbot_data = None
    name = session.get("name", username)
    result = session.get("result")
    reason = session.get("reason")
    confidence = session.get("confidence")
    position = session.get("position")
    qualification_status = session.get("qualification_status", "")
    applied_role = position or "Business Analyst"

    if position:
        chatbot_data = chatbot_by_application.get(session.get("active_application_id"))

    # Attach each job's own chatbot result (if any) to its application entry,
    # keyed by job_id, so the frontend can render Section 1 + Section 2 for
    # the exact job the applicant clicked on rather than whichever job was
    # applied to most recently.
    for job_id, entry in applications_by_job.items():
        entry["chatbot"] = chatbot_by_application.get(entry["id"])

    # JSON-safe dict (job_id as string keys) for embedding into the page.
    applications_by_job_json = {str(k): v for k, v in applications_by_job.items()}
    for job in available_jobs:
        app = applications_by_job.get(job["id"])

        job["card_class"] = ""

        if app:
            chatbot = app.get("chatbot")

            # Phase 2 has highest priority
            if chatbot:
                if chatbot.get("qualification_status") == "Qualified":
                    job["card_class"] = "qualified"

                elif chatbot.get("qualification_status") == "Not Qualified":
                    job["card_class"] = "not-qualified"

            # Otherwise use Phase 1
            elif app["eligibility"] == "Eligible":
                job["card_class"] = "eligible"

            else:
                job["card_class"] = "not-eligible"

        elif job["has_applied"]:
            job["card_class"] = "pending"
    
    for job in available_jobs:
        job["card_class"] = ""
        job["card_status"] = ""

        app = applications_by_job.get(job["id"])

        if app:
            chatbot = app.get("chatbot")

            # Section 2 (Highest Priority)
            if chatbot:
                status = (chatbot.get("qualification_status") or "").strip()

                if status == "Qualified":
                    job["card_class"] = "qualified"
                    job["card_status"] = "Qualified"

                elif status == "Not Qualified":
                    job["card_class"] = "not-qualified"
                    job["card_status"] = "Not Qualified"

            # Section 1
            if job["card_class"] == "":
                if app["eligibility"] == "Eligible":
                    job["card_class"] = "eligible"
                    job["card_status"] = "Eligible"
                else:
                    job["card_class"] = "not-eligible"
                    job["card_status"] = "Not Eligible"

        elif job["has_applied"]:
            job["card_class"] = "pending"
            job["card_status"] = "Application Submitted"
        cur.close()

    return render_template(
        "dashboard.html",
        name=name,
        email=email,
        contact=contact,
        username=username,
        result=result,
        reason=reason,
        confidence=confidence,
        position=position,
        applied_role=applied_role,
        qualification_status=qualification_status,
        application_data=applicant,
        has_applied=applicant is not None,
        position_limits=position_limits,
        available_jobs=available_jobs,
        chatbot_data=chatbot_data,
        applications_by_job=applications_by_job_json,
    )


@applicants_bp.route("/submit", methods=["POST"])
def submit_application():
    if "user_id" not in session:
        flash("You must be logged in to apply.", "error")
        return redirect(url_for("auth.login"))

    try:
        # --- 1. GET DATA ---
        form = request.form
        user_id = session["user_id"]

        name = form.get("name")
        email = form.get("email")
        contact = form.get("contact")
        age = int(form.get("age")) if form.get("age") else 0
        address = form.get("address")

        position = form.get("position")
        start_date_form = form.get("start_date")
        desired_pay = int(form.get("desired_pay")) if form.get("desired_pay") else 0
        employment_type = form.get("employment_type")

        school = form.get("school")
        school_location = form.get("school_location")
        years_attended = form.get("years_attended")
        education_level = form.get("education_level")
        degree = form.get("degree")
        major = form.get("major")

        job_title = form.get("job_title")
        company = form.get("company")
        experience = int(form.get("experience")) if form.get("experience") else 0
        responsibilities = form.get("responsibilities")
        skills = form.get("skills", "")

        cur = mysql.connection.cursor()

        name_parts = resume_scanner.split_full_name(name)
        first_name = name_parts["first_name"]
        middle_initial = name_parts["middle_initial"]
        last_name = name_parts["last_name"]

        # --- 2. RETRIEVE OR GENERATE ATOMIC APPLICANT RECORD ---
        cur.execute("SELECT applicant_id FROM applicants WHERE user_id = %s", (user_id,))
        app_row = cur.fetchone()
        
        dob_calc = f"{datetime.now().year - age}-01-01"
        if app_row:
            applicant_id = app_row[0]
            # Update basic demography
            cur.execute(
                """
                UPDATE applicants 
                SET first_name = %s, middle_initial = %s, last_name = %s,
                    date_of_birth = %s, current_location = %s 
                WHERE applicant_id = %s
                """,
                (first_name, middle_initial or None, last_name, dob_calc, address, applicant_id)
            )
        else:
            cur.execute(
                """
                INSERT INTO applicants (user_id, first_name, middle_initial, last_name,
                    date_of_birth, current_location, preferred_location, resume_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (user_id, first_name, middle_initial or None, last_name, dob_calc, address, address, "s3://resumes/placeholder_applicant.pdf")
            )
            applicant_id = cur.lastrowid

        # --- 3. FETCH NORMALIZED JOB SPECIFICATIONS ---
        cur.execute(
            """
            SELECT j.job_id, j.max_applicants, j.application_status, 
                   jd.minimum_age, jd.required_exp_years
            FROM jobs j
            LEFT JOIN job_desc jd ON jd.job_id = j.job_id
            WHERE j.job_name = %s
            """,
            (position,),
        )
        job_info = cur.fetchone()
        if not job_info:
            flash("The selected position does not exist.", "error")
            cur.close()
            return redirect(url_for("applicants.dashboard"))

        job_id, max_allowed, app_status, req_age, req_exp = job_info

        # Check status & applicant limits
        if app_status != "Open":
            flash("Applications for this position are currently closed.", "error")
            cur.close()
            return redirect(url_for("applicants.dashboard"))

        cur.execute("SELECT COUNT(*) FROM applications WHERE job_id = %s", (job_id,))
        if cur.fetchone()[0] >= max_allowed:
            flash("This position has reached its maximum applicant limit.", "error")
            cur.close()
            return redirect(url_for("applicants.dashboard"))

        # Duplicate Application check
        cur.execute("SELECT application_id FROM applications WHERE job_id = %s AND applicant_id = %s", (job_id, applicant_id))
        if cur.fetchone():
            flash("You have already applied for this position.", "error")
            cur.close()
            return redirect(url_for("applicants.dashboard"))

        # --- 4. INSERT EDUCATIONAL ENTITY ---
        if school or degree or major:
            cur.execute("DELETE FROM educations WHERE applicant_id = %s", (applicant_id,))
            cur.execute(
                """
                INSERT INTO educations (applicant_id, degree_level, major, institution, graduation_year)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (applicant_id, education_level or "High School", major or "General Education", school or "N/A", 2024)
            )

        # --- 5. INSERT WORK EXPERIENCE ENTITY ---
        if job_title or company or experience > 0:
            cur.execute("DELETE FROM work_experience WHERE applicant_id = %s", (applicant_id,))
            start_yr = datetime.now().year - experience
            cur.execute(
                """
                INSERT INTO work_experience (applicant_id, job_title, company_name, start_date, end_date, description)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (applicant_id, job_title or "Employee", company or "Company", f"{start_yr}-01-01", f"{datetime.now().year}-01-01", responsibilities or "")
            )

        # --- 6. SKILL MASTER LINKING ---
        # skills_master is curated by HR only (per job posting, via
        # job_required_skills). Applicants can only link to skill names
        # that already exist there — unrecognized skills are simply not
        # linked, never inserted as new master rows.
        if skills:
            cur.execute("DELETE FROM applicant_skills WHERE applicant_id = %s", (applicant_id,))
            skills_list = [s.strip() for s in skills.split(",") if s.strip()]
            for sk in skills_list:
                cur.execute("SELECT skill_id FROM skills_master WHERE skill_name = %s", (sk,))
                sk_row = cur.fetchone()
                if sk_row:
                    skill_id = sk_row[0]
                    cur.execute(
                        "INSERT IGNORE INTO applicant_skills (applicant_id, skill_id) VALUES (%s, %s)",
                        (applicant_id, skill_id)
                    )

        # --- 7. PROCESS RULES & MACHINE LEARNING (CART) ---
        rejection_reasons = []

        if age < req_age:
            rejection_reasons.append(f"Age ({age}) is below requirements ({req_age})")

        if experience < req_exp:
            rejection_reasons.append(f"Experience ({experience} yrs) is below requirements ({req_exp} yrs)")

        skills_list_eval = [s.strip() for s in skills.split(",") if s.strip()]
        if len(skills_list_eval) < 2:
            rejection_reasons.append("Insufficient skills listed (minimum 2 required)")

        try:
            cart_result = cart_predict_from_form(
                age=age,
                education_level=education_level,
                experience=experience,
                skills_raw=skills,
            )
            model_score = cart_result["model_score"]
            confidence = cart_result["probability_percent"]
            session["cart_details"] = cart_result
        except Exception as e:
            logger.error(f"CART prediction error: {e}")
            model_score = 0.5
            confidence = 50.0

        if not rejection_reasons and model_score < 0.55:
            rejection_reasons.append("Assessment score below qualification threshold")

        # Set final eligibility evaluation
        if not rejection_reasons:
            eligibility = "Eligible"
            pre_screen_status = "Passed Screening"
            final_reason = "You meet all requirements for this position."
        else:
            eligibility = "Not Eligible"
            pre_screen_status = "Failed Screening"
            final_reason = "Not Eligible: " + "; ".join(rejection_reasons)

        # --- 8. SUBMIT APPLICATION JUNCTION RECORD ---
        cur.execute(
            """
            INSERT INTO applications
                (job_id, applicant_id, resume_experience_years, pre_screen_status, applied_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            """,
            (job_id, applicant_id, experience, pre_screen_status)
        )
        session["active_application_id"] = cur.lastrowid
        # Section 1 result just landed — recompute the combined verdict
        # (chatbot hasn't run yet, so this will settle as Pending/Rejected).
        sync_overall_status(cur, cur.lastrowid)
        mysql.connection.commit()
        cur.close()

        # Update tracking sessions
        session["name"] = name
        session["position"] = position
        session["result"] = eligibility
        session["confidence"] = int(round(confidence))
        session["reason"] = final_reason

        if eligibility == "Eligible":
            flash(f"Application Submitted! {final_reason}", "success")
            try:
                send_step1_completed_email(email, name, position)
            except Exception as e:
                logger.error(f"Error sending Step 1 email: {e}")
        else:
            flash(f"Application Submitted. Status: {final_reason}", "error")

        return redirect(url_for("applicants.dashboard"))

    except Exception as e:
        logger.error(f"submit_application error: {e}")
        flash(f"Error: {e}", "error")
        return redirect(url_for("applicants.dashboard"))


# ---------- Applicant views ----------


@applicants_bp.route("/applicant")
def applicant_view():
    if "user_id" not in session:
        flash("You need to log in first.", "error")
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
    
    cur.execute(
        """
        SELECT app.pre_screen_status, j.job_name 
        FROM applications app 
        JOIN applicants a ON a.applicant_id = app.applicant_id
        JOIN jobs j ON j.job_id = app.job_id
        WHERE a.user_id = %s
        ORDER BY app.application_id DESC LIMIT 1
        """,
        (user_id,),
    )
    eligibility_row = cur.fetchone()
    cur.close()

    name = session.get("name")
    eligible_applicant = "Eligible" if eligibility_row and eligibility_row[0] == "Passed Screening" else "Not Eligible"
    position = eligibility_row[1] if eligibility_row else session.get("position")
    reason = session.get("reason")
    confidence = session.get("confidence")

    return render_template(
        "applicant.html",
        email=email,
        name=name,
        username=username,
        contact=contact,
        result=eligible_applicant,
        position=position,
        reason=reason,
        confidence=confidence,
    )


@applicants_bp.route("/viewapp")
def view_applicants():
    if "user_id" not in session:
        flash("You must be logged in to view applicants.", "error")
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()
    cur.execute(
        """
        SELECT a.full_name, u.email, u.contact_num, j.job_name 
        FROM applications app
        JOIN applicants a ON a.applicant_id = app.applicant_id
        JOIN users u ON u.user_id = a.user_id
        JOIN jobs j ON j.job_id = app.job_id
        """
    )
    applicants = cur.fetchall()
    cur.close()

    return render_template("view_applicants.html", applicants=applicants)


@applicants_bp.route("/viewchat")
def view_chatbot():
    if "user_id" not in session:
        flash("You must be logged in to view chatbot data.", "error")
        return redirect(url_for("auth.login"))

    # Mocked chatbot interaction for visualization
    chatbot = []
    return render_template("view_chatbot.html", chatbot=chatbot)


# ---------- Pre-application simple form (CART PRESCREEN) ----------


@applicants_bp.route("/prescreenn", methods=["GET", "POST"])
def prescreen():
    if "user_id" not in session:
        flash("You need to log in first.", "error")
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
    result = None

    # ---- Legacy manual CART self-check (kept for backward compatibility) ----
    if request.method == "POST":
        education_level = request.form.get("education_level")
        age = int(request.form.get("age") or 0)
        experience = int(request.form.get("experience") or 0)
        skills_raw = request.form.get("skills", "")

        try:
            cart_result = cart_predict_from_form(
                age=age,
                education_level=education_level,
                experience=experience,
                skills_raw=skills_raw,
            )
            result = cart_result
            session["prescreen_result"] = result
            flash(
                f"Prescreen result: {result['status']} (confidence {result['probability_percent']}%)",
                "info",
            )
        except Exception as e:
            logger.error(f"CART prescreen error: {e}")
            flash("Error during prescreening.", "error")
            result = None
        cur.close()
        return render_template(
            "prescreen.html",
            email=email,
            username=username,
            contact=contact,
            result=result,
            job=None,
        )

    result = session.get("prescreen_result")

    # ---- Load the actual job posting so prescreen.html + /submit-resume ----
    # ---- both know which job_id the uploaded resume is being scanned for --
    job_id = request.args.get("job_id", type=int)
    job = None
    if job_id:
        cur.execute(
            """
            SELECT j.job_id, j.job_name, j.application_status, j.application_deadline,
                   jd.description, jd.department, jd.employment_type,
                   jd.location, jd.salary_range, jd.vacancies
            FROM jobs j
            LEFT JOIN job_desc jd ON jd.job_id = j.job_id
            WHERE j.job_id = %s
            """,
            (job_id,),
        )
        row = cur.fetchone()
        if row:
            job = {
                "id": row[0],
                "title": row[1],
                "application_status": row[2],
                "deadline": row[3],
                "description": row[4],
                "department": row[5],
                "employment_type": row[6],
                "location": row[7],
                "salary_range": row[8],
                "vacancies": row[9],
            }
        else:
            flash("That job posting could not be found.", "error")

    cur.close()

    return render_template(
        "prescreen.html",
        email=email,
        username=username,
        contact=contact,
        result=result,
        job=job,
    )


def _username_fallback(user_id, cur):
    """Best-effort name fallback if the resume parser can't guess a full name."""
    try:
        cur.execute("SELECT username FROM users WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        return row[0] if row else "Applicant"
    except Exception:
        return "Applicant"


@applicants_bp.route("/submit-resume", methods=["POST"])
def submit_resume_application():
    """
    STEP 1 of the resume-scanning pipeline used by templates/prescreen.html.

    Flow: uploaded resume -> extract_text -> extract_all_info (ATS features,
    contact info, skills, education, work experience) -> CART predict_fit
    ("Strong Fit" / "Moderate Fit" / "Weak Fit"). Nothing is written to the
    database at this point. The scanned/parsed result is parked on disk as
    a "pending scan" (see _save_pending_scan) and the applicant is shown
    resume_review.html — a Resume Screening Result card where they can
    double-check (and manually correct) whatever the scanner picked up
    before anything is saved. Confirming there posts to
    /confirm-resume-application (see below), which is the step that
    actually writes to auth_db.
    """
    if "user_id" not in session:
        flash("You must be logged in to apply.", "error")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    job_id = request.form.get("job_id", type=int)
    resume_file = request.files.get("resume")

    if not job_id:
        flash("Missing job reference. Please open this job posting again.", "error")
        return redirect(url_for("applicants.dashboard"))

    if not resume_file or resume_file.filename == "":
        flash("Please upload your resume before submitting.", "error")
        return redirect(url_for("applicants.prescreen", job_id=job_id))

    if not allowed_resume_file(resume_file.filename):
        flash("Unsupported file type. Please upload a PDF, DOC, or DOCX.", "error")
        return redirect(url_for("applicants.prescreen", job_id=job_id))

    save_path = None
    cur = mysql.connection.cursor()
    try:
        # ── 1. Load job + job_desc (same tables HR/admin already write to) ──
        cur.execute(
            """
            SELECT j.job_id, j.job_name, j.max_applicants, j.application_status,
                   jd.description, jd.department, jd.employment_type,
                   jd.location, jd.salary_range, jd.vacancies,
                   jd.education_baseline, jd.required_exp_years, jd.minimum_age
            FROM jobs j
            LEFT JOIN job_desc jd ON jd.job_id = j.job_id
            WHERE j.job_id = %s
            """,
            (job_id,),
        )
        job_row = cur.fetchone()
        if not job_row:
            flash("The selected position does not exist.", "error")
            return redirect(url_for("applicants.dashboard"))

        (job_id, job_name, max_applicants, app_status,
         description, department, employment_type, location, salary_range,
         vacancies, education_baseline, required_exp_years, minimum_age) = job_row

        if app_status != "Open":
            flash("Applications for this position are currently closed.", "error")
            return redirect(url_for("applicants.dashboard"))

        cur.execute("SELECT COUNT(*) FROM applications WHERE job_id = %s", (job_id,))
        if max_applicants and cur.fetchone()[0] >= max_applicants:
            flash("This position has reached its maximum applicant limit.", "error")
            return redirect(url_for("applicants.dashboard"))

        # ── 2. Find (or note the absence of) this user's applicant record ───
        cur.execute("SELECT applicant_id FROM applicants WHERE user_id = %s", (user_id,))
        existing = cur.fetchone()
        applicant_id_existing = existing[0] if existing else None

        if applicant_id_existing:
            cur.execute(
                "SELECT application_id FROM applications WHERE job_id = %s AND applicant_id = %s",
                (job_id, applicant_id_existing),
            )
            if cur.fetchone():
                flash("You have already applied for this position.", "error")
                return redirect(url_for("applicants.dashboard"))

        # ── 3. Save the uploaded resume to disk ──────────────────────────────
        ext = resume_file.filename.rsplit(".", 1)[1].lower()
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        upload_dir = current_app.config.get("UPLOAD_FOLDER", "uploads")
        if not os.path.isabs(upload_dir):
            upload_dir = os.path.join(current_app.root_path, upload_dir)
        os.makedirs(upload_dir, exist_ok=True)
        save_path = os.path.join(upload_dir, unique_name)
        resume_file.save(save_path)

        # ── 4. Extract raw text ───────────────────────────────────────────────
        text = resume_scanner.extract_text(save_path)
        if not text.strip():
            flash(
                "We couldn't read any text from that resume. Please upload a "
                "text-based PDF or DOCX (not a scanned image).",
                "error",
            )
            os.remove(save_path)
            return redirect(url_for("applicants.prescreen", job_id=job_id))

        # ── 5. Build job keywords, then run the full ATS extraction ────────────
        job_keywords = resume_scanner.extract_keywords_from_job_desc(
            description=description or "", job_name=job_name or ""
        )
        extracted = resume_scanner.extract_all_info(text, job_keywords=job_keywords)
        features = extracted["ats_features"]
        contact_info = extracted["contact_info"]

        applicant_years = resume_scanner.calculate_total_experience_years(
            extracted["work_experience"], text=text
        )
        education_check = resume_scanner.evaluate_education_requirement(
            extracted["education"], education_baseline
        )

        # ── 6. Dataset-calibrated fit prediction ─────────────────────────────
        # The elite ATS dataset labels shortlisting from skill, experience,
        # and education match. Supply the real applicant-vs-job comparisons,
        # rather than proxies such as "a date range was found".
        model = resume_scanner.get_cart_model()
        fit_result = resume_scanner.predict_fit(
            features,
            model=model,
            experience_match=applicant_years >= float(required_exp_years or 0),
            education_match=education_check.get("meets", True),
        )
        eligible_labels = current_app.config.get(
            "RESUME_ELIGIBLE_LABELS", {"Strong Fit", "Moderate Fit"}
        )
        is_eligible = fit_result["label"] in eligible_labels

        full_name = (
            contact_info.get("full_name")
            or session.get("name")
            or _username_fallback(user_id, cur)
        )
        # Prefer the name parts the scanner already split out of the resume
        # header; if it couldn't find a name there, fall back to splitting
        # whatever full_name we ended up with (session name / username).
        if contact_info.get("first_name") or contact_info.get("last_name"):
            first_name = contact_info.get("first_name") or ""
            middle_initial = contact_info.get("middle_initial") or ""
            last_name = contact_info.get("last_name") or ""
        else:
            name_parts = resume_scanner.split_full_name(full_name)
            first_name = name_parts["first_name"]
            middle_initial = name_parts["middle_initial"]
            last_name = name_parts["last_name"]
        dob = contact_info.get("date_of_birth") or f"{datetime.now().year - 25}-01-01"
        location_val = contact_info.get("location") or "Not specified"
        email_val = contact_info.get("email") or session.get("email", "")

        # Skills the job actually asks for, split into found / missing so the
        # review page can render the ✓ / ✗ checklist exactly like the
        # "Resume Screening Result" mock-up.
        required_skills_found = [kw for kw, c in features["keyword_hits"].items() if c > 0]
        required_skills_missing = [kw for kw, c in features["keyword_hits"].items() if c == 0]
        # Any other skill the scanner recognised in the resume text that
        # wasn't one of this job's required keywords (still worth saving).
        other_skills = [s for s in extracted["skills"] if s not in features["keyword_hits"]]

        # ── 7. Park everything on disk as a "pending scan" — NOT saved yet ──
        pending = {
            "user_id": user_id,
            "job_id": job_id,
            "job_name": job_name,
            "department": department,
            "employment_type": employment_type,
            "location": location,
            "resume_path": save_path,
            "applicant_id_existing": applicant_id_existing,
            "required_exp_years": required_exp_years or 0,
            "education_baseline": education_baseline,
            "full_name": full_name,
            "first_name": first_name,
            "middle_initial": middle_initial,
            "last_name": last_name,
            "email": email_val,
            "dob": dob,
            "current_location": location_val,
            "experience_years": applicant_years,
            "degree_level": education_check.get("highest_level") or "Not detected",
            "education_meets": education_check.get("meets", True),
            "education_entries": extracted["education"],
            "work_experience": extracted["work_experience"],
            "required_skills_found": required_skills_found,
            "required_skills_missing": required_skills_missing,
            "other_skills": other_skills,
            "match_score": round(fit_result["score"]),
            "fit_label": fit_result["label"],
            "fit_message": fit_result["message"],
            "is_eligible": is_eligible,
        }
        token = _save_pending_scan(pending)
        session["pending_resume_token"] = token

        return render_template(
            "resume_review.html",
            job_id=job_id,
            job_name=job_name,
            token=token,
            scan=pending,
            degree_levels=["Entry-level track", "Diploma", "Associate", "Bachelor's", "Master's", "Doctoral"],
        )

    except Exception as e:
        mysql.connection.rollback()
        logger.error(f"submit_resume_application error: {e}")
        if save_path and os.path.exists(save_path):
            try:
                os.remove(save_path)
            except OSError:
                pass
        flash("Something went wrong while scanning your resume. Please try again.", "error")
        return redirect(url_for("applicants.prescreen", job_id=job_id))
    finally:
        cur.close()


@applicants_bp.route("/confirm-resume-application", methods=["POST"])
def confirm_resume_application():
    """
    STEP 2 of the resume-scanning pipeline. Called from the "Confirm &
    Submit" button on resume_review.html. Loads the pending scan the token
    points to, overlays whatever the applicant corrected on the review
    screen (name, email, years of experience, education level, which
    skills actually apply), and only now writes to auth_db — applicants /
    work_experience / educations / skills_master / applicant_skills /
    applications — exactly like the old single-step flow used to.
    """
    if "user_id" not in session:
        flash("You must be logged in to apply.", "error")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    token = request.form.get("token") or session.get("pending_resume_token")
    pending = _load_pending_scan(token)

    if not pending or pending.get("user_id") != user_id:
        flash("Your resume scan session has expired. Please upload your resume again.", "error")
        return redirect(url_for("applicants.dashboard"))

    job_id = pending["job_id"]
    save_path = pending["resume_path"]

    cur = mysql.connection.cursor()
    try:
        # ── Re-check the job is still open / not full / not already applied ──
        cur.execute(
            "SELECT max_applicants, application_status FROM jobs WHERE job_id = %s",
            (job_id,),
        )
        job_row = cur.fetchone()
        if not job_row:
            flash("The selected position no longer exists.", "error")
            return redirect(url_for("applicants.dashboard"))
        max_applicants, app_status = job_row
        if app_status != "Open":
            flash("Applications for this position are currently closed.", "error")
            return redirect(url_for("applicants.dashboard"))
        cur.execute("SELECT COUNT(*) FROM applications WHERE job_id = %s", (job_id,))
        if max_applicants and cur.fetchone()[0] >= max_applicants:
            flash("This position has reached its maximum applicant limit.", "error")
            return redirect(url_for("applicants.dashboard"))

        cur.execute("SELECT applicant_id FROM applicants WHERE user_id = %s", (user_id,))
        existing = cur.fetchone()
        applicant_id_existing = existing[0] if existing else None
        if applicant_id_existing:
            cur.execute(
                "SELECT application_id FROM applications WHERE job_id = %s AND applicant_id = %s",
                (job_id, applicant_id_existing),
            )
            if cur.fetchone():
                flash("You have already applied for this position.", "error")
                return redirect(url_for("applicants.dashboard"))

        # ── Pull the applicant's corrections from the review form ──────────
        first_name = (request.form.get("first_name") or pending.get("first_name") or "").strip()
        middle_initial = (request.form.get("middle_initial") or pending.get("middle_initial") or "").strip()
        last_name = (request.form.get("last_name") or pending.get("last_name") or "").strip()
        if not first_name and not last_name:
            # Nothing usable came from the split fields — fall back to
            # whatever single name string we had and split it ourselves.
            name_parts = resume_scanner.split_full_name(pending.get("full_name"))
            first_name = first_name or name_parts["first_name"]
            middle_initial = middle_initial or name_parts["middle_initial"]
            last_name = last_name or name_parts["last_name"]
        full_name = " ".join(
            p for p in [first_name, f"{middle_initial}." if middle_initial else "", last_name] if p
        )
        email_val = (request.form.get("email") or pending["email"]).strip()
        try:
            experience_years = float(request.form.get("experience_years", pending["experience_years"]))
        except (TypeError, ValueError):
            experience_years = pending["experience_years"]
        degree_level = request.form.get("degree_level") or pending["degree_level"]
        dob = pending["dob"]
        location_val = (request.form.get("current_location") or pending["current_location"]).strip()

        # Skills: every checkbox named "skill" that's checked = kept/confirmed.
        # Anything the applicant unchecked (that the scanner had flagged) is
        # dropped, matching what they told us was inaccurate.
        confirmed_skills = request.form.getlist("skill")
        if not confirmed_skills:
            # No checkboxes came through (e.g. JS-disabled form) — fall back
            # to whatever the scanner originally found so nothing is lost.
            confirmed_skills = pending["required_skills_found"] + pending["other_skills"]

        required_exp_years = pending.get("required_exp_years", 0)
        education_baseline = pending.get("education_baseline")
        degree_order = ["Entry-level track", "Diploma", "Associate", "Bachelor's", "Master's", "Doctoral"]
        try:
            education_meets = (
                degree_order.index(degree_level) >= degree_order.index(
                    resume_scanner.evaluate_education_requirement([], education_baseline)["required_level"]
                )
                if resume_scanner.evaluate_education_requirement([], education_baseline)["required_level"]
                else True
            )
        except (ValueError, KeyError):
            education_meets = pending.get("education_meets", True)

        is_eligible = pending["is_eligible"]
        fit_label = pending["fit_label"]
        match_score = pending["match_score"]

        # ── Upsert applicants row ───────────────────────────────────────────
        if applicant_id_existing:
            applicant_id = applicant_id_existing
            cur.execute(
                """
                UPDATE applicants
                SET first_name = %s, middle_initial = %s, last_name = %s,
                    date_of_birth = %s, current_location = %s, resume_url = %s
                WHERE applicant_id = %s
                """,
                (first_name, middle_initial or None, last_name, dob, location_val, save_path, applicant_id),
            )
        else:
            cur.execute(
                """
                INSERT INTO applicants
                    (user_id, first_name, middle_initial, last_name, date_of_birth,
                     current_location, preferred_location, resume_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (user_id, first_name, middle_initial or None, last_name, dob, location_val, location_val, save_path),
            )
            applicant_id = cur.lastrowid

        # ── Replace work_experience / educations / skills with the confirmed scan ──
        cur.execute("DELETE FROM work_experience WHERE applicant_id = %s", (applicant_id,))
        for exp in pending["work_experience"]:
            if not exp.get("start_date"):
                continue  # start_date is NOT NULL in schema.sql — skip unparsable entries
            cur.execute(
                """
                INSERT INTO work_experience
                    (applicant_id, job_title, company_name, start_date, end_date, description)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    applicant_id,
                    exp.get("job_title") or "N/A",
                    exp.get("company_name") or "N/A",
                    exp.get("start_date"),
                    exp.get("end_date"),
                    exp.get("description"),
                ),
            )

        cur.execute("DELETE FROM educations WHERE applicant_id = %s", (applicant_id,))
        education_entries = pending["education_entries"]
        if degree_level and degree_level != "Not detected" and not any(
            (e.get("degree_level") or "") == degree_level for e in education_entries
        ):
            # The applicant corrected/overrode the degree level — save it
            # even if the scanner never picked up a matching block of text.
            education_entries = education_entries + [{
                "degree_level": degree_level, "major": None,
                "institution": None, "graduation_year": None,
            }]
        for edu in (education_entries or [{"degree_level": degree_level}]):
            cur.execute(
                """
                INSERT INTO educations
                    (applicant_id, degree_level, major, institution, graduation_year)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    applicant_id,
                    edu.get("degree_level") or degree_level or "N/A",
                    edu.get("major") or "N/A",
                    edu.get("institution") or "N/A",
                    edu.get("graduation_year") or datetime.now().year,
                ),
            )

        # skills_master is curated by HR only (per job posting, via
        # job_required_skills). The resume scanner may recognize skill
        # keywords that HR never added — those are confirmed on-screen but
        # NOT written into skills_master; we only link the ones that are
        # already in the master dictionary.
        cur.execute("DELETE FROM applicant_skills WHERE applicant_id = %s", (applicant_id,))
        for skill_name in confirmed_skills:
            cur.execute("SELECT skill_id FROM skills_master WHERE skill_name = %s", (skill_name,))
            sk_row = cur.fetchone()
            if sk_row:
                skill_id = sk_row[0]
                cur.execute(
                    "INSERT IGNORE INTO applicant_skills (applicant_id, skill_id) VALUES (%s, %s)",
                    (applicant_id, skill_id),
                )

        # ── Record the application/screening result ─────────────────────────
        pre_screen_status = "Passed Screening" if is_eligible else "Failed Screening"
        cur.execute(
            """
            INSERT INTO applications
                (job_id, applicant_id, resume_experience_years, pre_screen_status, applied_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            """,
            (job_id, applicant_id, experience_years, pre_screen_status),
        )
        session["active_application_id"] = cur.lastrowid

        # Section 1 result just landed — recompute the combined verdict.
        sync_overall_status(cur, cur.lastrowid)

        mysql.connection.commit()

        # ── Prime the session for dashboard.html + the interview phase ──────
        session["name"] = full_name
        session["position"] = pending["job_name"]
        session["experience"] = int(experience_years)
        session["result"] = "Eligible" if is_eligible else "Not Eligible"
        session["confidence"] = int(match_score)
        session["reason"] = pending["fit_message"]
        session["resume_screening_summary"] = {
            "match_score": match_score,
            "label": fit_label,
            "skills_found": confirmed_skills,
            "skills_missing": [s for s in pending["required_skills_missing"] if s not in confirmed_skills],
            "experience_years_found": experience_years,
            "experience_years_required": required_exp_years,
            "education_meets": education_meets,
            "proceed_to_interview": is_eligible,
        }
        session.pop("pending_resume_token", None)
        _delete_pending_scan(token)

        if is_eligible:
            flash(
                f"Resume screened: {fit_label} — you're eligible to proceed "
                f"to the interview simulation.",
                "success",
            )
            try:
                send_step1_completed_email(email_val, full_name, pending["job_name"])
            except Exception as e:
                logger.error(f"Error sending Step 1 email: {e}")
        else:
            flash(f"Resume screened: {fit_label}. {pending['fit_message']}", "error")

        return redirect(url_for("applicants.dashboard"))

    except Exception as e:
        mysql.connection.rollback()
        logger.error(f"confirm_resume_application error: {e}")
        flash("Something went wrong while saving your application. Please try again.", "error")
        return redirect(url_for("applicants.prescreen", job_id=job_id))
    finally:
        cur.close()


@applicants_bp.route("/cancel-resume-review", methods=["POST"])
def cancel_resume_review():
    """
    "Re-upload a different resume" on resume_review.html. Discards the
    pending scan (and the resume file that was saved for it) without
    touching the database, then sends the applicant back to prescreen.html.
    """
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    token = request.form.get("token") or session.get("pending_resume_token")
    job_id = request.form.get("job_id", type=int)
    pending = _load_pending_scan(token)

    if pending:
        resume_path = pending.get("resume_path")
        if resume_path and os.path.exists(resume_path):
            try:
                os.remove(resume_path)
            except OSError:
                pass
        job_id = job_id or pending.get("job_id")

    _delete_pending_scan(token)
    session.pop("pending_resume_token", None)
    flash("Scan discarded. You can upload your resume again.", "success")
    return redirect(url_for("applicants.prescreen", job_id=job_id))


@applicants_bp.route("/preapp", methods=["GET", "POST"])
def preapp():
    if "user_id" not in session:
        flash("You need to log in first.", "error")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    cur = mysql.connection.cursor()

    if request.method == "POST":
        position = request.form.get("position")
        yearexperience = int(request.form.get("yearexperience") or 0)

        cur.execute(
            "SELECT username, email, contact_num FROM users WHERE user_id = %s",
            (user_id,),
        )
        user_info = cur.fetchone()
        if not user_info:
            flash("User not found.", "error")
            cur.close()
            return redirect(url_for("auth.login"))

        name, email, contact = user_info

        # Create base profile if not existing
        cur.execute("SELECT applicant_id FROM applicants WHERE user_id = %s", (user_id,))
        app_row = cur.fetchone()
        if not app_row:
            name_parts = resume_scanner.split_full_name(name)
            cur.execute(
                """
                INSERT INTO applicants (user_id, first_name, middle_initial, last_name, date_of_birth, current_location)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, name_parts["first_name"], name_parts["middle_initial"] or None,
                 name_parts["last_name"], "1998-01-01", "Unknown")
            )
            applicant_id = cur.lastrowid
        else:
            applicant_id = app_row[0]

        # Get job id matching positional requirements
        cur.execute("SELECT job_id FROM jobs WHERE job_name = %s", (position,))
        job_row = cur.fetchone()
        if job_row:
            job_id = job_row[0]
            cur.execute(
                """
                INSERT INTO applications (job_id, applicant_id, pre_screen_status)
                VALUES (%s, %s, 'Pending')
                """,
                (job_id, applicant_id)
            )
            
            # Record base work experience 
            cur.execute(
                """
                INSERT INTO work_experience (applicant_id, job_title, company_name, start_date)
                VALUES (%s, %s, %s, %s)
                """,
                (applicant_id, "Candidate", "Company", f"{datetime.now().year - yearexperience}-01-01")
            )
            mysql.connection.commit()

        cur.close()
        return redirect(url_for("applicants.preapp"))

    # Fetch latest preapp
    cur.execute(
        """
        SELECT a.full_name, u.email, u.contact_num, j.job_name, 
               COALESCE((SELECT SUM(TIMESTAMPDIFF(YEAR, start_date, COALESCE(end_date, CURDATE()))) FROM work_experience WHERE applicant_id = a.applicant_id), 0) AS years_experience,
               app.pre_screen_status
        FROM applications app
        JOIN applicants a ON a.applicant_id = app.applicant_id
        JOIN users u ON u.user_id = a.user_id
        JOIN jobs j ON j.job_id = app.job_id
        WHERE u.user_id = %s
        ORDER BY app.application_id DESC
        LIMIT 1
        """,
        (user_id,),
    )
    applicant = cur.fetchone()
    cur.close()

    if applicant:
        name, email, contact, position, yearexperience, status = applicant
        app_needed = False
    else:
        name = email = contact = position = yearexperience = status = None
        app_needed = True

    return render_template(
        "pre-app.html",
        name=name,
        email=email,
        contact=contact,
        position=position,
        yearexperience=yearexperience,
        eligibility="Eligible" if status == "Passed Screening" else ("Pending" if status == "Pending" else "Not Eligible"),
        level="N/A",
        status=status,
        confidence=50,
        app_needed=app_needed,
    )


# ---------- Profile & Photo Management ----------


def _allowed_profile_file(filename: str) -> bool:
    allowed = current_app.config.get(
        "ALLOWED_PROFILE_EXTENSIONS", {"png", "jpg", "jpeg", "gif"}
    )
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


@applicants_bp.route("/upload_photo", methods=["POST"])
def upload_photo():
    if "user_id" not in session:
        flash("You must be logged in to upload a profile photo.", "error")
        return redirect(url_for("auth.login"))

    if "profile_photo" not in request.files:
        flash("No file part", "error")
        return redirect(url_for("applicants.profile"))

    file = request.files["profile_photo"]
    if file.filename == "":
        flash("No selected file", "error")
        return redirect(url_for("applicants.profile"))

    if file and _allowed_profile_file(file.filename):
        image_data = file.read()
        cur = mysql.connection.cursor()
        cur.execute(
            "UPDATE users SET profile_photo = %s WHERE user_id = %s",
            (image_data, session["user_id"]),
        )
        mysql.connection.commit()
        cur.close()
        flash("Profile photo saved successfully", "success")
        return redirect(url_for("applicants.profile"))

    flash("Invalid file type", "error")
    return redirect(url_for("applicants.profile"))


@applicants_bp.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    cur = mysql.connection.cursor()

    cur.execute(
        "SELECT email, username, contact_num, user_type FROM users WHERE user_id = %s",
        (user_id,),
    )
    user = cur.fetchone()

    cur.execute("SELECT * FROM applicants WHERE user_id = %s", (user_id,))
    applicant = cur.fetchone()

    cur.execute(
        """
        SELECT j.job_name, app.pre_screen_status, app.applied_at 
        FROM applications app 
        JOIN applicants a ON a.applicant_id = app.applicant_id
        JOIN jobs j ON j.job_id = app.job_id
        WHERE a.user_id = %s
        """,
        (user_id,)
    )
    applications = cur.fetchall()
    cur.close()

    return render_template(
        "profile.html",
        email=user[0],
        username=user[1],
        contact=user[2],
        profile_photo=None,
        position=applications[0][0] if applications else None,
        eligibility=applications[0][1] if applications else None,
        yearexperience=5 if applicant else None,
        qualified=None,
        applications=applications,
    )


# ---------- HR views per job + applicant approve/deny ----------


@applicants_bp.route("/job/<path:position>")
def job_applicants(position):
    if "user_id" not in session:
        if request.args.get("modal") == "1":
            return jsonify({"error": "not_logged_in"}), 401
        flash("You must be logged in to view applicants.", "error")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    cur = mysql.connection.cursor()
    cur.execute("SELECT user_type FROM users WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    if not row or row[0] != "HR":
        cur.close()
        if request.args.get("modal") == "1":
            return jsonify({"error": "not_authorized"}), 403
        flash("You are not authorized to view this page.", "error")
        return redirect(url_for("applicants.dashboard"))

    position = unquote(position)

    # Perform structural JOIN to isolate applicants per job description
    cur.execute(
        """
        SELECT 
            app.application_id,
            a.full_name,
            u.email,
            u.contact_num,
            COALESCE((SELECT SUM(TIMESTAMPDIFF(YEAR, start_date, COALESCE(end_date, CURDATE()))) FROM work_experience WHERE applicant_id = a.applicant_id), 0) AS years_experience,
            COALESCE((SELECT degree_level FROM educations WHERE applicant_id = a.applicant_id ORDER BY graduation_year DESC LIMIT 1), 'N/A') AS education_level,
            app.pre_screen_status
        FROM applications app
        JOIN applicants a ON a.applicant_id = app.applicant_id
        JOIN users u ON u.user_id = a.user_id
        JOIN jobs j ON j.job_id = app.job_id
        WHERE j.job_name = %s
        ORDER BY app.application_id DESC
        """,
        (position,),
    )
    rows = cur.fetchall()
    cur.close()

    applicants = []
    for r in rows:
        applicants.append(
            {
                "id": r[0],
                "name": r[1],
                "email": r[2],
                "contact": r[3],
                "experience": r[4],
                "education_level": r[5],
                "level": "N/A",
                "qualified": r[6],
                "confidence": 85,
                "eligibility": "Eligible" if r[6] == "Passed Screening" else "Not Eligible",
            }
        )

    if request.args.get("modal") == "1":
        return jsonify({"position": position, "applicants": applicants})

    return render_template(
        "job_applicants.html",
        position=position,
        applicants=applicants,
    )


@applicants_bp.route("/applicant-decision-json", methods=["POST"])
def applicant_decision_json():
    if "user_id" not in session:
        return jsonify({"error": "not_logged_in"}), 401

    data = request.get_json() or {}
    application_id = data.get("applicant_id")  # maps to application junction identity
    decision = data.get("decision")
    position = data.get("position")

    if not application_id or decision not in ("approve", "deny") or not position:
        return jsonify({"error": "invalid_data"}), 400

    new_status = "Passed Screening" if decision == "approve" else "Failed Screening"

    try:
        cur = mysql.connection.cursor()

        # Update applications status directly inside the junction records
        cur.execute(
            "UPDATE applications SET pre_screen_status = %s WHERE application_id = %s",
            (new_status, application_id),
        )

        # Section 1 result just changed — recompute the combined verdict.
        sync_overall_status(cur, application_id)

        cur.execute(
            """
            SELECT a.full_name, u.email 
            FROM applications app 
            JOIN applicants a ON a.applicant_id = app.applicant_id
            JOIN users u ON u.user_id = a.user_id
            WHERE app.application_id = %s
            """,
            (application_id,),
        )
        app_row = cur.fetchone()
        mysql.connection.commit()
        cur.close()

        if decision == "approve" and app_row:
            name, email = app_row
            try:
                send_step1_completed_email(email, name, position)
            except Exception as e:
                logger.error(f"Error sending Step 1 email: {e}")

        return jsonify({
            "ok": True,
            "eligibility": "Eligible" if decision == "approve" else "Not Eligible",
            "status_label": "Approved" if decision == "approve" else "Denied",
            "status_code": 1 if decision == "approve" else 2
        })

    except Exception as e:
        logger.error(f"applicant_decision_json error: {e}")
        return jsonify({"error": str(e)}), 500


# ---------- Misc helpers ----------


# ---------- Misc helpers ----------


@applicants_bp.route("/save_experience", methods=["POST"])
def save_experience():
    user_id = session.get("user_id")
    yearexperience = request.form.get("yearexperience")

    if user_id and yearexperience:
        try:
            cur = mysql.connection.cursor()
            
            # Find the applicant_id linked to this user
            cur.execute("SELECT applicant_id FROM applicants WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            
            if row:
                applicant_id = row[0]
                # Check for an existing work experience record
                cur.execute("SELECT work_exp_id FROM work_experience WHERE applicant_id = %s LIMIT 1", (applicant_id,))
                exp_row = cur.fetchone()
                
                start_yr = datetime.now().year - int(yearexperience)
                start_date = f"{start_yr}-01-01"
                
                if exp_row:
                    cur.execute(
                        "UPDATE work_experience SET start_date = %s WHERE work_exp_id = %s",
                        (start_date, exp_row[0])
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO work_experience (applicant_id, job_title, company_name, start_date) 
                        VALUES (%s, 'Candidate', 'Company', %s)
                        """,
                        (applicant_id, start_date)
                    )
                mysql.connection.commit()
                session["experience"] = int(yearexperience)
                cur.close()
                return jsonify({"success": "Experience saved successfully"})
            
            cur.close()
            return jsonify({"error": "Applicant profile not found"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    return jsonify({"error": "Invalid data"}), 400


@applicants_bp.route("/progress")
def show_progress():
    """
    Progress view per position based on chatbot qualification status.
    Uses the normalized relational mappings instead of legacy flat tables.
    """
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            """
            SELECT 
                j.job_name,
                COUNT(
                    CASE 
                        WHEN LOWER(c.qualification_status) = 'qualified'
                        THEN 1 ELSE NULL
                    END
                ) AS percentage
            FROM applications app
            JOIN applicants a ON a.applicant_id = app.applicant_id
            JOIN jobs j ON j.job_id = app.job_id
            LEFT JOIN chatbot c ON c.application_id = app.application_id
            GROUP BY j.job_name
            """
        )
        progress_data = cur.fetchall()
        cur.close()
        return render_template("progress.html", progress_data=progress_data)
    except Exception as e:
        logger.error(f"Error in show_progress: {e}")
        return f"Error: {e}", 500


@applicants_bp.route("/check_email")
def check_email():
    email = request.args.get("email")
    if not email:
        return jsonify({"exists": False})
        
    try:
        cur = mysql.connection.cursor()
        # Relational check: join users with applicants since email is normalized in users table
        cur.execute(
            """
            SELECT a.applicant_id 
            FROM applicants a 
            JOIN users u ON u.user_id = a.user_id 
            WHERE u.email = %s
            """, 
            (email,)
        )
        existing_user = cur.fetchone()
        cur.close()
        return jsonify({"exists": bool(existing_user)})
    except Exception as e:
        logger.error(f"Error in check_email: {e}")
        return jsonify({"error": str(e)}), 500


@applicants_bp.route("/applicants")
def view_applications():
    """
    Comprehensive list of applicants utilizing structural relationships 
    (joining users to fetch normalized user contact information and emails).
    """
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            """
            SELECT 
                a.applicant_id,
                a.full_name,
                u.email,
                u.contact_num,
                a.current_location,
                a.preferred_location,
                a.resume_url
            FROM applicants a
            JOIN users u ON u.user_id = a.user_id
            """
        )
        applications = cur.fetchall()
        cur.close()
        return render_template("applications.html", applications=applications)
    except Exception as e:
        logger.error(f"Error in view_applications: {e}")
        return f"Error: {e}", 500


@applicants_bp.route("/get_applicants")
def get_applicants():
    """
    JSON API returning applicant names, jobs, and calculated experience totals 
    directly from work history records.
    """
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            """
            SELECT 
                a.full_name, 
                j.job_name,
                COALESCE(
                    (SELECT SUM(TIMESTAMPDIFF(YEAR, start_date, COALESCE(end_date, CURDATE()))) 
                     FROM work_experience 
                     WHERE applicant_id = a.applicant_id), 0
                ) AS years_experience
            FROM applications app
            JOIN applicants a ON a.applicant_id = app.applicant_id
            JOIN jobs j ON j.job_id = app.job_id
            """
        )
        rows = cur.fetchall()
        cur.close()

        applicants = [
            {"name": r[0], "position": r[1], "experience": int(r[2])} for r in rows
        ]
        return jsonify(applicants)
    except Exception as e:
        logger.error(f"Error in get_applicants: {e}")
        return jsonify({"error": str(e)}), 500