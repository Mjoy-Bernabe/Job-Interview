# How to apply this patch

Copy these into D:\xampp\htdocs\Simulation\Job-Interview, overwriting files
with the same name:

    services\overall_status.py      <-- NEW file (may not exist yet)
    blueprints\applicants.py        <-- overwrite
    blueprints\hr.py                <-- overwrite
    blueprints\summary.py           <-- overwrite
    templates\summary.html          <-- overwrite
    templates\Hrpage.html           <-- overwrite (fixes the Pre-Screening
                                         column always showing "Not Qualified")
    schema.sql                      <-- reference only

## 1. Copy the files
Keep the same relative folder paths.

## 2. Clear stale bytecode
Delete these folders so Python doesn't load a cached old version:
    blueprints\__pycache__
    services\__pycache__

## 3. Create the new database table (if not already done)
Run migration_overall_status_only.sql against your database. It only adds
one new table, it doesn't touch existing data.

## 4. Restart the app

---

## What's fixed in this update
The Candidate Pipeline's "Pre-Screening" column always showed "Not Qualified"
regardless of the real screening result, because of two bugs in Hrpage.html:

1. The table row checked `app.cart_status == 'Qualified'`, but the backend
   only ever sets cart_status to 'Eligible' or 'Not Eligible' -- the two
   values never matched, so it always fell through to the "Not Qualified"
   else-branch. Now it checks for 'Eligible' and labels the badge
   accordingly.

2. The applicant-detail modal (View Report) read `data.cart_status` from
   the /applicant-details/<id> API, but that endpoint never actually
   returned a field by that name -- it was always undefined. The modal now
   derives the same Eligible/Not Eligible badge from the real `data.status`
   field the API returns.

Also removed 'Rejected' from the list of statuses that counted as passing
pre-screening in hr.py -- a rejected application should never show as
Eligible.
