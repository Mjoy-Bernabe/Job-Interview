# blueprints/auth.py
import requests
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import mysql, logger
from app.services.otp_service import generate_otp, verify_otp
from app.services.email_service import send_otp_email
from app.session_utils import ADMIN_COOKIE, HR_COOKIE, use_portal_cookie

auth_bp = Blueprint("auth", __name__)


def _role_target(user_type):
    role = (user_type or "").strip().lower()
    # Separate HR and Admin routing here
    if role in ("hr", "hrpage"):
        return "hr.hr_dashboard"
    if role == "admin":
        return "admin.dashboard"
    if role == "applicant":
        return "applicants.dashboard"
    return None


def _current_session_role():
    """Return the lowercase user_type for the currently logged-in session,
    or None if there is no session / the user no longer exists."""
    if "user_id" not in session:
        return None
    cur = mysql.connection.cursor()
    cur.execute("SELECT user_type FROM users WHERE user_id = %s", (session["user_id"],))
    result = cur.fetchone()
    cur.close()
    if not result:
        return None
    return (result[0] or "").strip().lower()


def _bounce_if_logged_in(allowed_roles):
    """
    If the person already has an active session, decide what to do with it
    for THIS particular login/registration page:

    - If their session role belongs on this page (e.g. an Applicant hitting
      /login, or HR/Admin hitting /staff-login), send them straight to their
      dashboard, as before.
    - If their session role does NOT belong here (e.g. an Applicant session
      hitting /staff-login, or an HR/Admin session hitting /login), the old
      code silently redirected them to their OTHER portal's dashboard, which
      looked like "the wrong portal's page is showing". Instead we clear the
      stale session so this login page renders normally and the person can
      log in as the role this page is actually for.

    Returns a redirect response if the person should be bounced away, or
    None if the caller should continue rendering its own login page.

    NOTE: this is for the /login and /register (Applicant) pages only,
    which use the plain default session cookie. /staff-login and
    /register-staff intentionally do NOT use any bounce logic — see the
    comment at the top of staff_login() for why.
    """
    role = _current_session_role()
    if role is None:
        return None

    if role in allowed_roles:
        target = _role_target(role)
        if target:
            return redirect(url_for(target))
        return None

    # Logged in, but under a role that doesn't belong on this page —
    # log that stale session out so the correct login form shows instead
    # of the other role's dashboard.
    session.clear()
    return None


@auth_bp.route("/")
def index():
    return render_template("index.html")


# ---------- 1. APPLICANT LOGIN ----------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    bounce = _bounce_if_logged_in(allowed_roles={"applicant"})
    if bounce:
        return bounce

    error = None
    if request.method == "POST":
        # # --- Verify reCAPTCHA ---
        # recaptcha_response = request.form.get('g-recaptcha-response')
        # if not recaptcha_response:
        #     error = "Please complete the reCAPTCHA verification."
        #     return render_template("login.html", error=error)

        # secret_key = "6LfLvBEsAAAAACY2WgJ9qMIEjaNDEWMOPH_Xw73w"
        # verify_url = "https://www.google.com/recaptcha/api/siteverify"
        # data = {
        #     'secret': secret_key,
        #     'response': recaptcha_response
        # }

        # try:
        #     verify_response = requests.post(verify_url, data=data).json()
        #     if not verify_response.get('success'):
        #         error = "reCAPTCHA verification failed. Please try again."
        #         return render_template("login.html", error=error)
        # except:
        #     error = "Unable to verify reCAPTCHA. Please try again."
        #     return render_template("login.html", error=error)

        # --- Login Logic ---
        email = request.form["email"]
        password = request.form["password"]

        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT user_id, password_hash, user_type FROM users WHERE email = %s",
            (email,),
        )
        result = cur.fetchone()
        cur.close()

        if result:
            if check_password_hash(result[1], password):
                # STRICT ROLE CHECK: Deny HR/Admin here
                if result[2] in ('HR', 'Admin'):
                    error = "Staff members must use the Staff Login portal (/staff-login)."
                else:
                    session["user_id"] = result[0]
                    session["email"] = email
                    flash("Login successful! Welcome, Applicant.", "success")
                    return redirect(url_for("applicants.dashboard"))
            else:
                error = "Incorrect password."
        else:
            error = "Email not found."

    return render_template("login.html", error=error)


# ---------- 2. STAFF LOGIN (HR / ADMIN) ----------
@auth_bp.route("/staff-login", methods=["GET", "POST"])
def staff_login():
    # NOTE: We deliberately do NOT auto-redirect GET requests here based on
    # an existing HR or Admin session. Admin and HR have separate cookies
    # (see session_utils.py) specifically so both can be logged in at once
    # in the same browser — if this page bounced you straight to whichever
    # one is already active, you could never reach the form to log into
    # the OTHER role while the first stays logged in. So this page always
    # shows the form; logging in just writes to the correct cookie for the
    # role you authenticate as, leaving any other active portal untouched.

    error = None
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        cur = mysql.connection.cursor()
        cur.execute("SELECT user_id, password_hash, user_type FROM users WHERE email = %s", (email,))
        result = cur.fetchone()
        cur.close()

        if result:
            if check_password_hash(result[1], password):
                # STRICT ROLE CHECK: Deny Applicants here
                if result[2] == 'Applicant':
                    error = "Applicants must use the standard login page (/login)."
                else:
                    target = _role_target(result[2])

                    # Point this login at the correct portal cookie BEFORE
                    # writing to `session`, so HR and Admin logins land in
                    # their own cookie (admin_session / hr_session) instead
                    # of overwriting each other. This is what lets someone
                    # stay logged in as HR in one tab and Admin in another.
                    if target == "hr.hr_dashboard":
                        use_portal_cookie(HR_COOKIE)
                    elif target == "admin.dashboard":
                        use_portal_cookie(ADMIN_COOKIE)

                    session.clear()
                    session["user_id"] = result[0]
                    session["email"] = email

                    # Direct them to their specific dashboards
                    if target == "hr.hr_dashboard":
                        flash("Login successful! Welcome to the HR Portal.", "success")
                        return redirect(url_for("hr.hr_dashboard"))
                    elif target == "admin.dashboard":
                        flash("Login successful! Welcome, Admin.", "success")
                        return redirect(url_for("admin.dashboard"))
                    else:
                        error = "Role recognized, but dashboard not found."
            else:
                error = "Incorrect password."
        else:
            error = "Email not found."

    return render_template("staff_log.html", error=error)


# ---------- 3. STAFF REGISTRATION ----------
@auth_bp.route("/register-staff", methods=["GET", "POST"])
def register_staff():

    if request.method == "POST":
        # --- Verify reCAPTCHA ---
        recaptcha_response = request.form.get("g-recaptcha-response")
        secret_key = "6LfLvBEsAAAAACY2WgJ9qMIEjaNDEWMOPH_Xw73w"

        try:
            recaptcha_verify = requests.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={"secret": secret_key, "response": recaptcha_response}
            ).json()

            if not recaptcha_verify.get("success"):
                return render_template("register_staff.html", error="Recaptcha verification failed.")
        except:
            return render_template("register_staff.html", error="Unable to verify reCAPTCHA.")

        # --- Capture Form Data ---
        email = request.form["email"]
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        contact_num = request.form.get("contact_num")
        
        # Ensure only HR or Admin can be selected here
        usertype = request.form.get("user_type")
        if usertype not in ["Admin", "HR"]:
            return render_template("register_staff.html", error="Invalid staff role selected.")

        cur = mysql.connection.cursor()
        
        # Check if email or username is taken
        cur.execute("SELECT email, username FROM users WHERE email = %s OR username = %s", (email, username))
        existing_user = cur.fetchone()
        
        if existing_user:
            cur.close()
            existing_email, existing_username = existing_user
            if existing_email == email:
                return render_template("register_staff.html", error="Email already registered.")
            else:
                return render_template("register_staff.html", error="Username is already taken.")

        # Insert new staff member
        cur.execute("""
            INSERT INTO users (email, username, password_hash, user_type, contact_num)
            VALUES (%s, %s, %s, %s, %s)
        """, (email, username, password, usertype, contact_num))

        mysql.connection.commit()
        cur.close()

        flash(f"Staff account created successfully for {username}. Please log in.", "success")
        return redirect(url_for("auth.staff_login"))

    return render_template("register_staff.html")


# ---------- 4. SESSION / LOGOUT / APPLICANT REGISTRATION ----------
@auth_bp.route("/check_session")
def check_session():
    """
    Check if user is logged in. Admin and HR each have their own cookie
    now (see session_utils.py), and this endpoint is called from the
    shared staff-login page, so it checks all three portals rather than
    just the default cookie.
    """
    from app.session_utils import ADMIN_COOKIE, HR_COOKIE, read_portal_session

    # Default cookie (Applicant, or whatever this path resolves to)
    if "user_id" in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT user_type FROM users WHERE user_id = %s", (session["user_id"],))
        result = cur.fetchone()
        cur.close()
        if result:
            # NOTE: both "user_type" and "usertype" are included since the
            # front-end pages read different key spellings.
            return {"logged_in": True, "user_type": result[0], "usertype": result[0]}

    # Staff cookies
    for cookie_name in (ADMIN_COOKIE, HR_COOKIE):
        data = read_portal_session(cookie_name)
        user_id = data.get("user_id")
        if user_id:
            cur = mysql.connection.cursor()
            cur.execute("SELECT user_type FROM users WHERE user_id = %s", (user_id,))
            result = cur.fetchone()
            cur.close()
            if result:
                return {"logged_in": True, "user_type": result[0], "usertype": result[0]}

    return {"logged_in": False}


@auth_bp.route("/logout")
def logout():
    # This is the Applicant portal's logout (default session cookie).
    # Admin and HR now have their own dedicated logout routes
    # (admin.logout / hr.logout) so logging out of one portal never
    # touches the other's cookie — see session_utils.py.
    session.clear()
    response = redirect(url_for("auth.login"))
    # Prevent caching
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, post-check=0, pre-check=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    bounce = _bounce_if_logged_in(allowed_roles={"applicant"})
    if bounce:
        return bounce

    if request.method == "POST":
        # --- Verify reCAPTCHA ---
        recaptcha_response = request.form.get("g-recaptcha-response")
        secret_key = "6LfLvBEsAAAAACY2WgJ9qMIEjaNDEWMOPH_Xw73w"

        recaptcha_verify = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": secret_key, "response": recaptcha_response}
        ).json()

        if not recaptcha_verify.get("success"):
            return render_template("register.html", error="Recaptcha verification failed.")

        # --- Continue registration ---
        email = request.form["email"]
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        usertype = "Applicant" # Hardcoded to Applicant for public registration
        contact_num = request.form.get("contact_num") or request.form.get("contact_number")

        cur = mysql.connection.cursor()
        
        # Check if both email or username are already taken
        cur.execute("SELECT email, username FROM users WHERE email = %s OR username = %s", (email, username))
        existing_user = cur.fetchone()
        
        if existing_user:
            cur.close()
            existing_email, existing_username = existing_user
            if existing_email == email:
                return render_template("register.html", error="Email already registered.")
            else:
                return render_template("register.html", error="Username is already taken. Please choose another.")

        # Insert new user
        cur.execute("""
            INSERT INTO users (email, username, password_hash, user_type, contact_num)
            VALUES (%s, %s, %s, %s, %s)
        """, (email, username, password, usertype, contact_num))

        mysql.connection.commit()
        cur.close()

        flash("Registration successful. You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


# ---------- 5. SUPPORT / PRIVACY ----------
@auth_bp.route("/support")
def support():
    return render_template("support.html")

@auth_bp.route("/landing")
def landing():
    return render_template("index.html")

@auth_bp.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ---------- 6. FORGOT PASSWORD / OTP ----------
@auth_bp.route("/forgot", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]
        cur = mysql.connection.cursor()
        cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if not user:
            flash("Email not found.", "error")
            return redirect(url_for("auth.forgot_password"))

        otp = generate_otp(email)
        if send_otp_email(email, otp):
            flash("OTP sent to your email.", "info")
            return redirect(url_for("auth.verify_otp_route", email=email))
        
        flash("Failed to send OTP.", "error")
        return redirect(url_for("auth.forgot_password"))

    return render_template("forgotpass.html")


@auth_bp.route("/verify_otp/<email>", methods=["GET", "POST"])
def verify_otp_route(email):
    if request.method == "POST":
        otp_input = request.form["otp"]
        if verify_otp(email, otp_input):
            session["verified_email"] = email
            session["verification_time"] = True  # flag only
            flash("OTP verified. You may now reset your password.", "success")
            return redirect(url_for("auth.reset_password", token=email))

        flash("Invalid or expired OTP.", "error")
        return render_template("verify_otp.html", email=email)

    return render_template("verify_otp.html", email=email)


@auth_bp.route("/resend_otp", methods=["POST"])
def resend_otp():
    data = request.get_json()
    email = data.get("email")

    if not email:
        return {"success": False, "message": "Email is required."}

    cur = mysql.connection.cursor()
    cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    cur.close()

    if not user:
        return {"success": False, "message": "Email not found in our system."}

    otp = generate_otp(email)
    ok = send_otp_email(email, otp)
    
    if ok:
        return {"success": True, "message": "OTP resent successfully."}
    return {"success": False, "message": "Failed to send OTP."}


@auth_bp.route("/reset/<token>", methods=["GET", "POST"])
def reset_password(token):
    verified_email = session.get("verified_email")
    if not verified_email or verified_email != token:
        flash("Session expired or invalid. Please verify your OTP again.", "error")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        new_password = generate_password_hash(request.form["password"])
        cur = mysql.connection.cursor()
        cur.execute(
            "UPDATE users SET password_hash = %s WHERE email = %s",
            (new_password, token),
        )
        mysql.connection.commit()
        cur.close()
        
        session.pop("verified_email", None)
        session.pop("verification_time", None)
        flash("Password has been reset successfully.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset.html")