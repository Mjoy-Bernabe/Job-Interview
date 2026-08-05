# blueprints/schedule.py
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
import json
import datetime
from app.extensions import mysql

schedule_bp = Blueprint("schedule", __name__)


def get_progress_data():
    """
    Reusable helper that returns a list of dicts like:
    {
        "position": "Business Analyst",
        "current": 5,
        "max_allowed": 10,
        "percent": 50
    }
    """
    cur = mysql.connection.cursor()

    cur.execute(
        """
        SELECT j.job_name, j.max_applicants, COUNT(a.application_id) AS current_count
        FROM jobs j
        LEFT JOIN applications a ON a.job_id = j.job_id
        GROUP BY j.job_id, j.job_name, j.max_applicants
        ORDER BY j.job_name ASC
        """
    )
    rows = cur.fetchall()
    progress_data = []

    for pos, max_allowed, current in rows:
        max_allowed = max_allowed or 0
        current = current or 0
        percent = int((current / max_allowed) *
                      100) if max_allowed and max_allowed > 0 else 0
        progress_data.append(
            {
                "position": pos,
                "current": current,
                "max_allowed": max_allowed,
                "percent": percent,
            }
        )

    cur.close()
    return progress_data


@schedule_bp.route("/schedule")
def schedule_page():
    """If you still want the old blue page to work."""
    progress_data = get_progress_data()
    return render_template("Settinghr.html", progress_data=progress_data)


# --- EXTENDED REQUIREMENTS (Recruitment tab & old page both use this) ---
@schedule_bp.route("/update_requirements", methods=["POST"])
def update_requirements():
    # Core (jobs table)
    position = request.form.get("position")
    max_allowed = request.form.get("max_allowed")
    form_access = request.form.get("form_access") or "Open"
    opening_date = request.form.get("opening_date") or None
    deadline_date = request.form.get("deadline_date") or None

    # Descriptive fields (job_desc table)
    department = request.form.get("department") or "General"
    employment_type = request.form.get("employment_type") or "Full-time"
    location = request.form.get("location") or "Not specified"
    work_setup = request.form.get("work_setup") or "Onsite"
    work_schedule = request.form.get("work_schedule") or None
    salary_range = request.form.get("salary_range") or None
    vacancies = request.form.get("vacancies")
    education_level = request.form.get("education_level") or "Not specified"
    required_degree = request.form.get("degree") or None
    required_course = request.form.get("course") or None
    experience_years = request.form.get("experience_years")
    min_age = request.form.get("min_age")
    school = request.form.get("school")  # education / CART notes
    job_description = request.form.get("job_description") or "Not specified"

    # Applicant-requirement fields — "" from the "Any" option means no filter
    required_gender = request.form.get("gender") or "Any"
    required_civil_status = request.form.get("civil_status") or "Any"

    # Required skills (job_required_skills bridge table). This is the ONLY
    # place allowed to add brand-new rows to skills_master — HR curates the
    # skill dictionary per job posting; applicants can only ever link to
    # skills that already exist here.
    skills_raw = request.form.get("skills") or ""
    skill_names = [s.strip() for s in skills_raw.split(",") if s.strip()]

    # Safe numeric conversion
    exp_val = int(experience_years) if experience_years and experience_years.isdigit() else 0
    age_val = int(min_age) if min_age and min_age.isdigit() else 18
    vacancies_val = int(vacancies) if vacancies and vacancies.isdigit() else 1

    if not position or not max_allowed:
        flash("Job Title and Max Applicants are required fields.", "danger")
        return redirect(request.referrer or url_for("hr.hr_dashboard"))

    # opening_date/application_deadline are NOT NULL on `jobs` — fall back to today
    # so a job posted without dates picked still saves successfully.
    opening_date = opening_date or datetime.date.today().isoformat()
    deadline_date = deadline_date or opening_date

    try:
        cur = mysql.connection.cursor()

        cur.execute("SELECT job_id FROM jobs WHERE job_name = %s", (position,))
        existing = cur.fetchone()

        if existing:
            job_id = existing[0]
            cur.execute(
                """
                UPDATE jobs
                SET max_applicants = %s,
                    application_status = %s,
                    opening_date = %s,
                    application_deadline = %s
                WHERE job_id = %s
                """,
                (max_allowed, form_access, opening_date, deadline_date, job_id),
            )
        else:
            cur.execute(
                """
                INSERT INTO jobs
                    (job_name, max_applicants, application_status, opening_date, application_deadline)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (position, max_allowed, form_access, opening_date, deadline_date),
            )
            job_id = cur.lastrowid

        cur.execute("SELECT job_desc_id FROM job_desc WHERE job_id = %s", (job_id,))
        desc_row = cur.fetchone()

        if desc_row:
            job_desc_id = desc_row[0]
            cur.execute(
                """
                UPDATE job_desc
                SET description = %s,
                    department = %s,
                    employment_type = %s,
                    work_setup = %s,
                    work_schedule = %s,
                    location = %s,
                    salary_range = %s,
                    vacancies = %s,
                    education_baseline = %s,
                    required_degree = %s,
                    required_course = %s,
                    required_exp_years = %s,
                    minimum_age = %s,
                    required_gender = %s,
                    required_civil_status = %s,
                    education_notes = %s
                WHERE job_id = %s
                """,
                (
                    job_description, department, employment_type, work_setup, work_schedule,
                    location, salary_range, vacancies_val, education_level,
                    required_degree, required_course, exp_val, age_val,
                    required_gender, required_civil_status, school, job_id,
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO job_desc
                    (job_id, description, department, employment_type, work_setup, work_schedule,
                     location, salary_range, vacancies, education_baseline,
                     required_degree, required_course, required_exp_years, minimum_age,
                     required_gender, required_civil_status, education_notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    job_id, job_description, department, employment_type, work_setup, work_schedule,
                    location, salary_range, vacancies_val, education_level,
                    required_degree, required_course, exp_val, age_val,
                    required_gender, required_civil_status, school,
                ),
            )
            job_desc_id = cur.lastrowid

        # --- Required skills (job_required_skills) ---
        # HR is the only actor allowed to create new skills_master rows.
        # Re-sync this job posting's required-skill links from scratch.
        cur.execute(
            "DELETE FROM job_required_skills WHERE job_desc_id = %s", (job_desc_id,)
        )
        for skill_name in skill_names:
            cur.execute(
                "SELECT skill_id FROM skills_master WHERE skill_name = %s", (skill_name,)
            )
            sk_row = cur.fetchone()
            if sk_row:
                skill_id = sk_row[0]
            else:
                cur.execute(
                    "INSERT INTO skills_master (skill_name) VALUES (%s)", (skill_name,)
                )
                skill_id = cur.lastrowid
            cur.execute(
                "INSERT IGNORE INTO job_required_skills (job_desc_id, skill_id) VALUES (%s, %s)",
                (job_desc_id, skill_id),
            )

        mysql.connection.commit()
        cur.close()
        flash(f"Job post for {position} saved successfully!", "success")

    except Exception as e:
        print(f"--- ERROR: {e} ---")
        flash(f"Error updating requirements: {e}", "danger")

    # 🔁 back to HR page or wherever the form came from
    return redirect(request.referrer or url_for("hr.hr_dashboard"))


@schedule_bp.route("/set_pax", methods=["POST"])
def set_pax():
    position = request.form.get("position")
    max_allowed = request.form.get("max_allowed")

    if not position or not max_allowed:
        flash("Position and Max Applicants are required.", "danger")
        return redirect(request.referrer or url_for("hr.hr_dashboard"))

    try:
        cur = mysql.connection.cursor()
        cur.execute(
            """
            UPDATE jobs
            SET max_applicants = %s
            WHERE job_name = %s
            """,
            (max_allowed, position),
        )
        mysql.connection.commit()
        cur.close()
        flash("Max applicants limit set successfully!", "success")
    except Exception as e:
        flash(f"Error setting max limit: {e}", "danger")

    return redirect(request.referrer or url_for("hr.hr_dashboard"))


@schedule_bp.route("/set_chat", methods=["POST"])
def set_chat():
    position = request.form.get("position")
    max_allowed = request.form.get("max_allowed")

    if not position or not max_allowed:
        flash("All fields are required!", "danger")
        return redirect(request.referrer or url_for("hr.hr_dashboard"))

    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM chatbot_limits WHERE position = %s", (position,))
    existing = cur.fetchone()
    if existing:
        cur.execute(
            "UPDATE chatbot_limits SET max_allowed = %s WHERE position = %s",
            (max_allowed, position),
        )
    else:
        cur.execute(
            "INSERT INTO chatbot_limits (position, max_allowed) VALUES (%s, %s)",
            (position, max_allowed),
        )

    mysql.connection.commit()
    cur.close()
    flash(f"Limit set for {position} successfully!", "success")
    return redirect(request.referrer or url_for("hr.hr_dashboard"))


@schedule_bp.route("/save_schedule", methods=["POST"])
def save_schedule():
    date = request.form.get("date")
    time = request.form.get("time")
    end_date = request.form.get("endDate") or None
    recurring_days = request.form.getlist("recurring")
    recurring_json = json.dumps(recurring_days) if recurring_days else None

    try:
        cur = mysql.connection.cursor()
        cur.execute(
            """
            INSERT INTO schedules (schedule_date, schedule_time, recurring_days, end_date)
            VALUES (%s, %s, %s, %s)
            """,
            (date, time, recurring_json, end_date),
        )
        mysql.connection.commit()
        cur.close()
        flash("Schedule saved successfully!", "success")
    except Exception as e:
        flash(f"Error saving schedule: {e}", "danger")

    return redirect(request.referrer or url_for("hr.hr_dashboard"))
