# config.py
import os


class Config:
    # core
    SECRET_KEY = os.environ.get("SECRET_KEY", "supersecretkey")

    # MySQL
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DB = os.environ.get("MYSQL_DB", "auth_db")

    # uploads
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "uploads")
    PROFILE_UPLOAD_FOLDER = os.environ.get(
        "PROFILE_UPLOAD_FOLDER", "static/uploads")
    ALLOWED_RESUME_EXTENSIONS = {"pdf", "doc", "docx"}
    ALLOWED_PROFILE_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
    MAX_RESUME_SIZE = int(os.environ.get(
        "MAX_RESUME_SIZE", 10 * 1024 * 1024))  # 10 MB

    # resume scanner (prescreen.html -> /submit-resume)
    # CART labels from services/resume_scanner that are allowed to proceed
    # to the interview simulation phase. Weak Fit is always rejected.
    RESUME_ELIGIBLE_LABELS = {"Strong Fit", "Moderate Fit"}

    # mail
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "aceview18@gmail.com")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "uelmqlulrxbbkikx")

    # limiter
    RATELIMIT_DEFAULT = "10 per minute"

    # pdf / summary
    SUMMARY_REPORT_DIR = os.environ.get(
        "SUMMARY_REPORT_DIR", "summary_reports")
