# blueprints/hr.py
import io
import csv
from flask import Response
from flask import (
    Blueprint,
    render_template,
    request,
    session,
    redirect,
    url_for,
    jsonify,
    current_app
)
from extensions import mysql, mail
from flask_mail import Message
import datetime
from .schedule import get_progress_data

hr_bp = Blueprint("hr", __name__)

@hr_bp.route("/hr")
def hr_dashboard():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
        
    user_id = session["user_id"]
    cur = mysql.connection.cursor()
    
    # 1) Logged-in HR user info
    cur.execute(
        "SELECT email, username, user_type FROM users WHERE user_id = %s",
        (user_id,)
    )
    user = cur.fetchone()
    
    if not user:
        cur.close()
        return redirect(url_for("auth.login"))

    email, username, user_type = user

    # Security check: only HR accounts may view the HR dashboard. Without
    # this, any logged-in session (e.g. an Applicant) could load /hr
    # directly by URL and see the HR portal.
    if (user_type or "").strip().lower() not in ("hr", "hrpage"):
        session.clear()
        return redirect(url_for("auth.staff_login"))

    # 2) Standard Application Metrics
    cur.execute("SELECT COUNT(*) FROM applications")
    total_requests = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM applications WHERE screening_status = 'Pending'")
    pending_applications = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM applications WHERE screening_status IN ('Approved', 'Eligible', 'Passed Screening')")
    approved_applications = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM applications WHERE screening_status IN ('Rejected', 'Denied', 'Not Qualified')")
    rejected_applicants = cur.fetchone()[0] or 0

    avg_interview_score = 0.0

    # CART: Eligible vs Not Eligible (pre-screening)
    cur.execute("SELECT COUNT(*) FROM applications WHERE screening_status IN ('Passed Screening','Approved','Eligible','Shortlisted','Hired','Talent Pool')")
    cart_eligible = cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM applications WHERE screening_status NOT IN ('Passed Screening','Approved','Eligible','Shortlisted','Hired','Talent Pool')")
    cart_not_eligible = cur.fetchone()[0] or 0

    # ANN / chatbot: Qualified vs Not Qualified
    cur.execute("SELECT COUNT(*) FROM chatbot WHERE qualification_status = 'Qualified'")
    ann_qualified = cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM chatbot WHERE qualification_status != 'Qualified'")
    ann_not_qualified = cur.fetchone()[0] or 0

    # Pipeline counts
    cur.execute("SELECT COUNT(*) FROM applications WHERE screening_status = 'Hired'")
    hired_count = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM applications WHERE screening_status IN ('Interview Scheduled', 'Interviewed', 'Interview Done', 'Interview Completed')")
    interviewed_count = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM applications WHERE screening_status IN ('Interview Scheduled', 'Approved')")
    interview_scheduled = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM applications WHERE shortlisted = 1")
    try:
        shortlisted_count = cur.fetchone()[0] or 0
    except Exception:
        shortlisted_count = 0

    cur.execute("SELECT COUNT(*) FROM applications WHERE screening_status = 'Talent Pool'")
    talent_pool_count = cur.fetchone()[0] or 0

    # Trend data (last 6 months)
    cur.execute("""
        SELECT DATE_FORMAT(applied_at, '%b') AS month_label, COUNT(*) AS cnt
        FROM applications
        WHERE applied_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
        GROUP BY DATE_FORMAT(applied_at, '%Y-%m'), DATE_FORMAT(applied_at, '%b')
        ORDER BY MIN(applied_at) ASC
        LIMIT 6
    """)
    trend_rows = cur.fetchall()
    trend_labels = [r[0] for r in trend_rows]
    trend_counts = [r[1] for r in trend_rows]

    # 3) Job Position Distribution
    cur.execute("""
        SELECT j.job_name, COUNT(a.application_id) AS total_count
        FROM applications a
        JOIN jobs j ON j.job_id = a.job_id
        GROUP BY j.job_id, j.job_name
        ORDER BY total_count DESC, j.job_name ASC
    """)
    position_distribution = [
        {"position": row[0] or "Unassigned", "count": row[1] or 0}
        for row in cur.fetchall()
    ]

    # 4) Recent Applicants (full details for Candidate Pipeline)
    cur.execute("""
        SELECT 
            a.application_id,
            u.username,
            u.email,
            u.contact_num,
            j.job_name,
            a.screening_status,
            a.applied_at,
            COALESCE(c.qualification_status, 'Pending') AS ann_status,
            COALESCE(c.average_score * 100, 0.0) AS ann_score,
            ap.resume_url,
            COALESCE(a.shortlisted, 0) AS shortlisted,
            COALESCE(a.interview_result, '') AS interview_result,
            COALESCE(a.final_interview_status, '') AS final_status,
            a.final_interview_date,
            COALESCE(a.final_interviewer, '') AS final_interviewer,
            COALESCE(a.virtual_interview_status, 'Pending') AS virtual_interview_status,
            COALESCE(a.transcript_status, 'Not Generated') AS transcript_status,
            COALESCE(a.interview_type, 'Chat') AS interview_type
        FROM applications a
        JOIN applicants ap ON ap.applicant_id = a.applicant_id
        JOIN users u ON u.user_id = ap.user_id
        JOIN jobs j ON j.job_id = a.job_id
        LEFT JOIN chatbot c ON c.user_id = u.user_id AND c.position = j.job_name
        ORDER BY a.application_id DESC
        LIMIT 15
    """)
    applicant_rows = cur.fetchall()

    recent_applicants = []
    for row in applicant_rows:
        applied_date = row[6]
        applied_date_val = applied_date if isinstance(applied_date, (datetime.date, datetime.datetime)) else None

        db_status = row[5]
        ann_status = row[7]
        ann_score = row[8]

        cart_status = 'Eligible' if db_status in ('Passed Screening', 'Approved', 'Eligible', 'Rejected', 'Talent Pool', 'Hired', 'Shortlisted') else 'Not Eligible'
        hr_status = db_status if db_status in ('Approved', 'Rejected', 'Talent Pool', 'Hired') else 'Pending'

        recent_applicants.append({
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "role": row[4],
            "cart_status": cart_status,
            "ann_status": ann_status,
            "hr_status": hr_status,
            "score": float(ann_score) if ann_score is not None else 0.0,
            "applied_date": applied_date_val,
            "resume_url": row[9],
            "shortlisted": "Yes" if row[10] else "No",
            "interview_result": row[11] or "Needs Review",
            "final_status": row[12] or "Pending",
            "final_date": row[13].strftime("%Y-%m-%d") if isinstance(row[13], (datetime.date, datetime.datetime)) else (str(row[13]) if row[13] else ""),
            "final_interviewer": row[14] or "",
            "virtual_interview_status": row[15] or "Pending",
            "transcript_status": row[16] or "Not Generated",
            "interview_type": row[17] or "Chat",
        })

    # 5) Upcoming Interviews
    cur.execute("""
        SELECT u.username, j.job_name
        FROM applications a
        JOIN applicants ap ON ap.applicant_id = a.applicant_id
        JOIN users u ON u.user_id = ap.user_id
        JOIN jobs j ON j.job_id = a.job_id
        WHERE a.screening_status IN ('Eligible', 'Approved')
        LIMIT 3
    """)
    interview_rows = cur.fetchall()
    
    upcoming_interviews = []
    for row in interview_rows:
        upcoming_interviews.append({
            "candidate_name": row[0],
            "position": row[1],
            "day": "Today",
            "date_str_short": datetime.date.today().strftime("%b %d"),
            "start_time": "10:00 AM",
        })

    # 6) Machine Learning Metrics Stub
    # Note: Because the DB schema only has a single `screening_status` column,
    # the advanced matrix tracking for ANN/CART is zeroed out to prevent errors.
    cart_ann_matrix = {
        "eligible_qualified": 0, "eligible_not_qualified": 0,
        "not_eligible_qualified": 0, "not_eligible_not_qualified": 0,
    }
    cart_metrics = {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "accuracy": 0.0, "error_rate": 0.0, "total": 0}
    ann_metrics = {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "accuracy": 0.0, "error_rate": 0.0, "total": 0}

    # 7) Recruitment Progress
    try:
        progress_data = get_progress_data()
    except Exception:
        progress_data = []

    # 8) Job Posts List
    cur.execute("""
        SELECT 
            j.job_name, j.max_applicants, j.application_status, 
            j.opening_date, j.application_deadline,
            jd.education_baseline, NULL AS target_school,
            jd.required_exp_years, jd.minimum_age, jd.location,
            jd.employment_type, jd.department, jd.salary_range,
            jd.vacancies,
            jd.work_setup, jd.work_schedule,
            jd.required_degree, jd.required_course,
            jd.required_gender, jd.required_civil_status,
            (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.job_id) AS applicant_count,
            (SELECT GROUP_CONCAT(sm.skill_name ORDER BY sm.skill_name SEPARATOR ', ')
             FROM job_required_skills jrs
             JOIN skills_master sm ON sm.skill_id = jrs.skill_id
             WHERE jrs.job_desc_id = jd.job_desc_id) AS skills
        FROM jobs j
        LEFT JOIN job_desc jd ON jd.job_id = j.job_id
        ORDER BY j.job_name ASC
    """)
    job_posts = [
        {
            "position": row[0],
            "max_allowed": row[1],
            "form_access": row[2] or "Open",
            "opening_date": row[3],
            "deadline_date": row[4],
            "education_level": row[5],
            "target_school": row[6],
            "experience_years": row[7],
            "min_age": row[8],
            "location": row[9],
            "employment_type": row[10],
            "department": row[11],
            "salary_range": row[12],
            "vacancies": row[13],
            "applicant_count": row[14],
            "skills": row[15] or "",
            "work_setup": row[16] or "Onsite",
            "work_schedule": row[17] or "",
            "required_degree": row[18] or "",
            "required_course": row[19] or "",
            "required_gender": row[20] or "Any",
            "required_civil_status": row[21] or "Any",
        }
        for row in cur.fetchall()
    ]
    cur.close()

    return render_template(
        "Hrpage.html",
        username=username or "HR Manager",
        email=email,
        total_requests=total_requests,
        pending_applications=pending_applications,
        approved_applications=approved_applications,
        rejected_applicants=rejected_applicants,
        avg_interview_score=avg_interview_score,
        position_distribution=position_distribution,
        jobs=job_posts,
        upcoming_interviews=upcoming_interviews,
        recent_applicants=recent_applicants,
        progress_data=progress_data,
        cart_eligible=cart_eligible,
        cart_not_eligible=cart_not_eligible,
        ann_qualified=ann_qualified,
        ann_not_qualified=ann_not_qualified,
        hired_count=hired_count,
        interviewed_count=interviewed_count,
        interview_scheduled=interview_scheduled,
        shortlisted_count=shortlisted_count,
        talent_pool_count=talent_pool_count,
        trend_labels=trend_labels,
        trend_counts=trend_counts,
        cart_ann_matrix=cart_ann_matrix,
        cart_metrics=cart_metrics,
        ann_metrics=ann_metrics,
    )

@hr_bp.route("/applicant-details/<int:app_id>")
def get_applicant_details(app_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT 
            u.username,
            u.email,
            j.job_name,
            a.screening_status,
            COALESCE(jd.required_exp_years, 0),
            GROUP_CONCAT(DISTINCT sk.skill_name ORDER BY sk.skill_name SEPARATOR ', ') AS skills
        FROM applications a
        JOIN applicants ap ON ap.applicant_id = a.applicant_id
        JOIN users u ON u.user_id = ap.user_id
        JOIN jobs j ON j.job_id = a.job_id
        LEFT JOIN job_desc jd ON jd.job_id = j.job_id
        LEFT JOIN applicant_skills askill ON askill.applicant_id = ap.applicant_id
        LEFT JOIN skills_master sk ON sk.skill_id = askill.skill_id
        WHERE a.application_id = %s
        GROUP BY u.username, u.email, j.job_name, a.screening_status, jd.required_exp_years
    """, (app_id,))
    
    row = cur.fetchone()
    cur.close()
    
    if not row:
        return jsonify({"error": "Not found"}), 404
        
    return jsonify({
        "name": row[0],
        "email": row[1],
        "role": row[2],
        "status": row[3],
        "experience": row[4],
        "skills": row[5] if row[5] else "None listed",
        "qa_data": None
    })

@hr_bp.route("/hr/skills/search")
def search_skills():
    """
    Autocomplete lookup against the HR-curated skills_master dictionary,
    used by the "Add skills" search box on the job-posting form. Read-only —
    it never creates rows; new skills only get inserted when the job form
    is actually submitted (see schedule.update_requirements).
    """
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    query = (request.args.get("q") or "").strip()
    cur = mysql.connection.cursor()

    if query:
        cur.execute(
            """
            SELECT skill_name FROM skills_master
            WHERE skill_name LIKE %s
            ORDER BY skill_name ASC
            LIMIT 10
            """,
            (f"%{query}%",),
        )
    else:
        cur.execute(
            "SELECT skill_name FROM skills_master ORDER BY skill_name ASC LIMIT 10"
        )

    skills = [row[0] for row in cur.fetchall()]
    cur.close()
    return jsonify({"skills": skills})

@hr_bp.route("/hr/applicant-decision-json", methods=["POST"])
def applicant_decision_json():
    if "user_id" not in session:
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401

    data = request.get_json() or {}
    app_id = data.get("applicant_id")
    decision = data.get("decision")
    
    if not app_id or decision not in ("approve", "reject"):
        return jsonify({"ok": False, "msg": "Invalid data"}), 400
        
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT u.username, u.email
            FROM applications a
            JOIN applicants ap ON ap.applicant_id = a.applicant_id
            JOIN users u ON u.user_id = ap.user_id
            WHERE a.application_id = %s
        """, (app_id,))
        
        row = cur.fetchone()
        
        if not row:
            cur.close()
            return jsonify({"ok": False, "msg": "Applicant not found"}), 404
            
        app_name, app_email = row
        new_status = "Approved" if decision == "approve" else "Rejected"
        
        cur.execute(
            "UPDATE applications SET screening_status = %s WHERE application_id = %s",
            (new_status, app_id)
        )
        mysql.connection.commit()
        cur.close()

        # Email Notification Logic
        if decision == "approve":
            subject = "AceView Application Update - Congratulations!"
            body = f"""Dear {app_name},
We are pleased to inform you that your application has been APPROVED for the next stage of our recruitment process.
Our HR team will contact you soon with the next steps and schedule details.

Best regards,
AceView Recruitment Team"""
        else:
            subject = "AceView Application Update"
            body = f"""Dear {app_name},
Thank you for taking the time to apply and interview with us.
After careful consideration, we regret to inform you that you have not been selected at this time.
We encourage you to apply again in the future for other opportunities.

Best regards,
AceView Recruitment Team"""

        try:
            default_sender = current_app.config.get("MAIL_DEFAULT_SENDER") or current_app.config.get("MAIL_USERNAME")
            msg = Message(subject=subject, recipients=[app_email], sender=default_sender)
            msg.body = body
            mail.send(msg)
        except Exception as mail_err:
            print("DECISION EMAIL ERROR:", mail_err)
            
    except Exception as e:
        print("DECISION GENERAL ERROR:", e)
        return jsonify({"ok": False, "msg": "Server error"}), 500
        
    return jsonify({"ok": True})

@hr_bp.route("/hr/logout")
def logout():
    # Every /hr* route (including this one) is bound to its own
    # "hr_session" cookie (see session_utils.py), so clearing `session`
    # here only clears the HR portal — an Admin session logged in at the
    # same time, in another tab, is untouched.
    session.clear()
    response = redirect(url_for("auth.staff_login"))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, post-check=0, pre-check=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@hr_bp.route("/hr/export-all")
def export_all_data():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
        
    cur = mysql.connection.cursor()
    # Fetching core candidate data based on your existing database structure
    cur.execute("""
        SELECT u.username, u.email, j.job_name, a.screening_status, a.applied_at
        FROM applications a
        JOIN applicants ap ON ap.applicant_id = a.applicant_id
        JOIN users u ON u.user_id = ap.user_id
        JOIN jobs j ON j.job_id = a.job_id
    """)
    rows = cur.fetchall()
    cur.close()

    # Generate the CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Email', 'Position', 'Status', 'Applied Date']) # Header row
    for row in rows:
        writer.writerow(row)

    # Return as a downloadable file
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=applicant_data.csv"}
    )