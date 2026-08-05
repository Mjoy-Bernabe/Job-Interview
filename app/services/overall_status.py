# services/overall_status.py
"""
Combines the two independent, per-application pipeline results —

  * Section 1: resume pre-screening  -> applications.pre_screen_status
  * Section 2: chatbot interview     -> chatbot.qualification_status

into a single overall verdict ("Passed Screening" / "Rejected" / "Pending"),
persisted in application_overall_status (one row per application_id).

Neither source column is ever touched by this module — it only reads them
and writes the combined result. Call sync_overall_status(cur, application_id)
any time either source value changes, in the SAME transaction as that
change, before you commit.
"""

# pre_screen_status values that count as "passed" Section 1.
PASSING_PRE_SCREEN_STATUSES = (
    "Passed Screening",
    "Approved",
    "Eligible",
    "Shortlisted",
    "Hired",
    "Talent Pool",
)


def compute_overall_status(pre_screen_status, chatbot_qualification_status):
    """
    Pure function, no DB access — derive the combined verdict from the two
    stage results so the rule is easy to read/test/reuse on its own.
    """
    if pre_screen_status not in PASSING_PRE_SCREEN_STATUSES:
        # Failed (or hasn't cleared) Section 1 — rejected regardless of
        # whether Section 2 ever ran.
        return "Rejected"

    if not chatbot_qualification_status:
        # Passed Section 1, Section 2 not completed yet.
        return "Pending"

    if chatbot_qualification_status == "Qualified":
        return "Passed Screening"

    # Passed Section 1 but the chatbot interview did not qualify them.
    return "Rejected"


def sync_overall_status(cur, application_id):
    """
    Recompute application_overall_status for one application from its
    CURRENT applications.pre_screen_status + chatbot.qualification_status,
    and upsert the row. Does not commit — the caller commits as part of
    whatever transaction triggered the change.

    Returns the computed overall_status string, or None if the
    application_id doesn't exist.
    """
    cur.execute(
        "SELECT pre_screen_status FROM applications WHERE application_id = %s",
        (application_id,),
    )
    app_row = cur.fetchone()
    if not app_row:
        return None
    pre_screen_status = app_row[0]

    cur.execute(
        "SELECT qualification_status FROM chatbot WHERE application_id = %s",
        (application_id,),
    )
    chatbot_row = cur.fetchone()
    chatbot_status = chatbot_row[0] if chatbot_row else None

    overall_status = compute_overall_status(pre_screen_status, chatbot_status)

    cur.execute(
        """
        INSERT INTO application_overall_status
            (application_id, pre_screen_snapshot, chatbot_snapshot, overall_status)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            pre_screen_snapshot = VALUES(pre_screen_snapshot),
            chatbot_snapshot = VALUES(chatbot_snapshot),
            overall_status = VALUES(overall_status)
        """,
        (application_id, pre_screen_status, chatbot_status, overall_status),
    )
    return overall_status
