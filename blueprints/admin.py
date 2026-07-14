# blueprints/admin.py
# pyrefly: ignore [missing-import]
from flask import Blueprint, render_template, session, redirect, url_for
from extensions import mysql

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin/logout")
def logout():
    # Every /admin/* route (including this one) is bound to its own
    # "admin_session" cookie (see session_utils.py), so clearing `session`
    # here only clears the Admin portal — an HR session logged in at the
    # same time, in another tab, is untouched.
    session.clear()
    response = redirect(url_for("auth.staff_login"))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, post-check=0, pre-check=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@admin_bp.route("/admin/dashboard")
def dashboard():
    # 1. Security Check: Ensure user is logged in
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    cur = mysql.connection.cursor()

    # 2. Security Check: Ensure the user is actually an Admin
    cur.execute("SELECT username, user_type FROM users WHERE user_id = %s", (user_id,))
    user = cur.fetchone()
    
    if not user or user[1] != 'Admin':
        cur.close()
        # If they aren't an admin, kick them out to the regular login
        return redirect(url_for("auth.login"))

    username = user[0]

    # 3. Gather Admin-specific Data (Example Queries)
    # Total Users
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    # Total HR Staff
    cur.execute("SELECT COUNT(*) FROM users WHERE user_type = 'HR'")
    total_hr = cur.fetchone()[0]

    # Total Applicants
    cur.execute("SELECT COUNT(*) FROM users WHERE user_type = 'Applicant'")
    total_applicants = cur.fetchone()[0]

    cur.close()

    # 4. Render the Admin Template
    return render_template(
        "admin_dashboard.html",
        username=username,
        total_users=total_users,
        total_hr=total_hr,
        total_applicants=total_applicants
    )

@admin_bp.route("/admin/recruitment")
def recruitment():
    # 1. Security Check: Ensure user is logged in
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    cur = mysql.connection.cursor()

    # 2. Security Check: Ensure the user is actually an Admin
    cur.execute("SELECT username, user_type FROM users WHERE user_id = %s", (user_id,))
    user = cur.fetchone()
    
    if not user or user[1] != 'Admin':
        cur.close()
        return redirect(url_for("auth.login"))

    username = user[0]
    cur.close()

    return render_template(
        "admin_recruitment.html",
        username=username
    )

@admin_bp.route("/admin/analytics")
def analytics():
    # 1. Security Check: Ensure user is logged in
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    cur = mysql.connection.cursor()

    # 2. Security Check: Ensure the user is actually an Admin
    cur.execute("SELECT username, user_type FROM users WHERE user_id = %s", (user_id,))
    user = cur.fetchone()
    
    if not user or user[1] != 'Admin':
        cur.close()
        return redirect(url_for("auth.login"))

    username = user[0]

    # Analytics queries
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE user_type = 'HR'")
    active_hr = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE user_type = 'Applicant'")
    active_applicants = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM applications")
    total_apps = cur.fetchone()[0]

    cur.close()

    return render_template(
        "admin_analytics.html",
        username=username,
        total_users=total_users,
        active_hr=active_hr,
        active_applicants=active_applicants,
        total_apps=total_apps
    )

@admin_bp.route("/admin/users")
def user_management():
    # 1. Security Check: Ensure user is logged in
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    cur = mysql.connection.cursor()

    # 2. Security Check: Ensure the user is actually an Admin
    cur.execute("SELECT username, user_type FROM users WHERE user_id = %s", (user_id,))
    user = cur.fetchone()
    
    if not user or user[1] != 'Admin':
        cur.close()
        return redirect(url_for("auth.login"))

    username = user[0]

    # Query all users
    cur.execute('''
        SELECT u.user_id, u.username, a.full_name, u.email, u.user_type
        FROM users u
        LEFT JOIN applicants a ON u.user_id = a.user_id
        ORDER BY u.user_id DESC
    ''')
    db_users = cur.fetchall()
    
    users_data = []
    for row in db_users:
        name = row[2] if row[2] else row[1]
        users_data.append({
            'id': row[0],
            'name': name,
            'email': row[3],
            'role': row[4],
            'status': 'Active'
        })
    total_users = len(users_data)
    cur.close()

    return render_template(
        "admin_usermanagement.html",
        username=username,
        users=users_data,
        total_users=total_users
    )

@admin_bp.route("/admin/troubleshooting")
def troubleshooting():
    # 1. Security Check: Ensure user is logged in
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    cur = mysql.connection.cursor()

    # 2. Security Check: Ensure the user is actually an Admin
    cur.execute("SELECT username, user_type FROM users WHERE user_id = %s", (user_id,))
    user = cur.fetchone()
    
    if not user or user[1] != 'Admin':
        cur.close()
        return redirect(url_for("auth.login"))

    username = user[0]
    cur.close()

    return render_template(
        "admin_troubleshooting.html",
        username=username,
        active_page="troubleshooting"
    )

@admin_bp.route("/admin/notifications")
def notifications():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    cur = mysql.connection.cursor()
    cur.execute("SELECT username, user_type FROM users WHERE user_id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()

    if not user or user[1] != 'Admin':
        return redirect(url_for("auth.login"))

    return render_template(
        "admin_notifications.html",
        username=user[0],
        active_page="notifications"
    )

@admin_bp.route("/admin/audit-logs")
def audit_logs():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    cur = mysql.connection.cursor()
    cur.execute("SELECT username, user_type FROM users WHERE user_id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()

    if not user or user[1] != 'Admin':
        return redirect(url_for("auth.login"))

    return render_template(
        "admin_logs.html",
        username=user[0],
        active_page="audit_logs"
    )

