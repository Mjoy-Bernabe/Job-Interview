# session_utils.py
"""
Per-portal session cookies for Admin and HR.

Why this exists
---------------
Admin and HR log in through the same page (/staff-login). Flask's default
session mechanism stores everything in ONE cookie per browser, so logging
in as HR in one tab and then as Admin in another tab (same browser) simply
overwrites that single cookie — the second login silently kicks out the
first. That's the "conflict" between the Admin and HR portals: they can't
both be logged in at the same time even though the applicant portal is
completely separate.

The fix is to give each portal its own signed cookie:
  - "admin_session"  -> used for every /admin/* page
  - "hr_session"     -> used for /hr, /applicant-details/*, and the HR
                        decision endpoint
  - "session"        -> the normal Flask default, still used for
                        Applicants and shared/public pages (login,
                        register, forgot-password, etc.)

Because these are three separate cookies, being logged in as Admin does
not touch the HR cookie and vice versa, so both can be active
simultaneously in the same browser.
"""
from flask import g, request, has_request_context, current_app
from flask.sessions import SecureCookieSessionInterface

ADMIN_COOKIE = "admin_session"
HR_COOKIE = "hr_session"
DEFAULT_COOKIE = "session"  # Applicants + shared/public pages

# Path prefixes that always belong to a given portal's cookie.
_ADMIN_PATH_PREFIXES = ("/admin",)
_HR_PATH_PREFIXES = ("/hr", "/applicant-details", "/applicant-decision-json")


def cookie_name_for_path(path):
    if path.startswith(_ADMIN_PATH_PREFIXES):
        return ADMIN_COOKIE
    if path.startswith(_HR_PATH_PREFIXES):
        return HR_COOKIE
    return DEFAULT_COOKIE


class PortalSessionInterface(SecureCookieSessionInterface):
    """
    Decides which cookie Flask's `session` proxy reads from / writes to.

    Most pages (/admin/*, /hr, ...) always belong to one portal, so the
    request path alone is enough. The one shared page - /staff-login -
    doesn't know which portal the person is logging into until AFTER the
    credentials are checked against the database. For that case, the view
    calls `use_portal_cookie()` once it knows the role; that sets a hint
    on `g` which this method checks first.
    """

    def get_cookie_name(self, app):
        if has_request_context():
            hint = getattr(g, "portal_cookie", None)
            if hint:
                return hint
            return cookie_name_for_path(request.path)
        return DEFAULT_COOKIE


def use_portal_cookie(cookie_name):
    """Call inside a view once the role is known, so this response's
    session data is written to the correct portal cookie instead of
    whatever the request path would default to."""
    g.portal_cookie = cookie_name


def read_portal_session(cookie_name):
    """
    Decode a specific portal's session cookie directly off the incoming
    request, independent of whichever cookie the generic `session` proxy
    happens to be bound to for the current path. This is what lets the
    shared /staff-login page check "is there already an active HR
    session?" and "is there already an active Admin session?" at the same
    time, instead of only seeing one of them.
    """
    raw = request.cookies.get(cookie_name)
    if not raw:
        return {}
    serializer = current_app.session_interface.get_signing_serializer(current_app)
    if serializer is None:
        return {}
    try:
        max_age = int(current_app.permanent_session_lifetime.total_seconds())
        return serializer.loads(raw, max_age=max_age)
    except Exception:
        return {}
