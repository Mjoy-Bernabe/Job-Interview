import MySQLdb
import json
import datetime

# Database Connection details from config
db_config = {
    "host": "127.0.0.1",
    "user": "root",
    "passwd": "",
    "db": "auth_db",
    "port": 3307
}

def seed():
    print("Connecting to database...")
    db = MySQLdb.connect(**db_config)
    cur = db.cursor()

    # Disable constraints to clear applicants safely
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    cur.execute("""
        DELETE FROM chatbot WHERE user_id IN (SELECT user_id FROM users WHERE user_type = 'Applicant')
    """)
    cur.execute("""
        DELETE FROM applications WHERE applicant_id IN (SELECT applicant_id FROM applicants)
    """)
    cur.execute("""
        DELETE FROM applicant_skills WHERE applicant_id IN (SELECT applicant_id FROM applicants)
    """)
    cur.execute("""
        DELETE FROM applicants
    """)
    cur.execute("""
        DELETE FROM users WHERE user_type = 'Applicant'
    """)
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    print("Cleared previous applicant seed data.")
    
    # 1. Create default jobs if not present
    jobs_to_create = [
        {
            "name": "Java Developer",
            "dept": "Information Technology",
            "type": "Full-time",
            "loc": "Pasig City",
            "sal": "PHP50,000 - PHP70,000",
            "vacancies": 3,
            "max": 50,
            "exp": 2,
            "edu": "Bachelor's Degree",
            "desc": "Responsible for developing, maintaining, and deploying enterprise Java applications. Requires strong knowledge of Spring Boot, Hibernate, and RESTful APIs."
        },
        {
            "name": "Business Analyst",
            "dept": "Operations",
            "type": "Full-time",
            "loc": "Hybrid (Manila)",
            "sal": "PHP40,000 - PHP55,000",
            "vacancies": 2,
            "max": 30,
            "exp": 1,
            "edu": "Bachelor's Degree",
            "desc": "Bridge the gap between IT and business teams. Gather requirements, build workflows, and analyze business processes to identify areas for improvement."
        },
        {
            "name": "Project Analyst",
            "dept": "PMO",
            "type": "Full-time",
            "loc": "Onsite (Pasig)",
            "sal": "PHP35,000 - PHP45,000",
            "vacancies": 1,
            "max": 20,
            "exp": 1,
            "edu": "Bachelor's Degree",
            "desc": "Assist project managers in tracking milestones, preparing status reports, managing resource allocations, and documenting project deliverables."
        }
    ]

    job_ids = {}
    for j in jobs_to_create:
        cur.execute("SELECT job_id FROM jobs WHERE job_name = %s", (j["name"],))
        row = cur.fetchone()
        if row:
            job_ids[j["name"]] = row[0]
        else:
            cur.execute("""
                INSERT INTO jobs (job_name, max_applicants, application_status, opening_date, application_deadline)
                VALUES (%s, %s, 'Open', CURDATE(), DATE_ADD(CURDATE(), INTERVAL 30 DAY))
            """, (j["name"], j["max"]))
            job_id = db.insert_id()
            job_ids[j["name"]] = job_id
            
            cur.execute("""
                INSERT INTO job_desc (job_id, education_baseline, required_exp_years, minimum_age, location, employment_type, department, salary_range, vacancies, description)
                VALUES (%s, %s, %s, 18, %s, %s, %s, %s, %s, %s)
            """, (job_id, j["edu"], j["exp"], j["loc"], j["type"], j["dept"], j["sal"], j["vacancies"], j["desc"]))
            print(f"Created Job: {j['name']}")

    # 2. Insert master skills if missing
    skills_list = ["Java", "Spring Boot", "MySQL", "PHP", "HTML", "CSS", "JavaScript", "Python", "SQL", "Excel", "Data Analysis", "Project Management", "Agile"]
    skill_ids = {}
    for skill in skills_list:
        cur.execute("SELECT skill_id FROM skills_master WHERE skill_name = %s", (skill,))
        row = cur.fetchone()
        if row:
            skill_ids[skill] = row[0]
        else:
            cur.execute("INSERT INTO skills_master (skill_name) VALUES (%s)", (skill,))
            skill_ids[skill] = db.insert_id()

    # 3. Create Sample Applicants
    applicants_data = [
        {
            "username": "denise_dc",
            "first_name": "Denise",
            "last_name": "Dela Cruz",
            "email": "denise.delacruz@example.com",
            "contact": "09171234567",
            "dob": "1998-04-12",
            "location": "Quezon City",
            "job": "Java Developer",
            "screening": "Passed Screening",
            "shortlisted": 1,
            "interview_result": "Excellent",
            "final_status": "Scheduled",
            "final_date": "2026-07-15",
            "final_interviewer": "Mr. PL Pasig",
            "virtual_status": "Completed",
            "transcript_status": "Available",
            "interview_type": "Video",
            "applied_days_ago": 1,
            "chatbot": {
                "qualification": "Qualified",
                "score": 0.825,
                "confidence": 0.88,
                "experience": "2 years in Java Backend",
                "skills": ["Java", "Spring Boot", "HTML", "CSS", "JavaScript"],
                "assessment": [
                    {"question": "Tell me about a complex Spring Boot API you built.", "answer": "I built a real-time tracking API for a logistics firm that reduced latency by 30% using caching.", "score": 0.85},
                    {"question": "How do you handle database concurrency in MySQL?", "answer": "I use transactions and optimistic locking to prevent race conditions during updates.", "score": 0.80}
                ]
            }
        },
        {
            "username": "john_doe",
            "first_name": "John",
            "last_name": "Doe",
            "email": "johndoe@example.com",
            "contact": "09189876543",
            "dob": "1996-08-25",
            "location": "Pasig City",
            "job": "Java Developer",
            "screening": "Passed Screening",
            "shortlisted": 0,
            "interview_result": None,
            "final_status": "Pending",
            "final_date": None,
            "final_interviewer": None,
            "virtual_status": "Scheduled",
            "transcript_status": "Not Generated",
            "interview_type": "Chat",
            "applied_days_ago": 2,
            "chatbot": None
        },
        {
            "username": "jane_smith",
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "janesmith@example.com",
            "contact": "09204445555",
            "dob": "1997-11-05",
            "location": "Makati City",
            "job": "Business Analyst",
            "screening": "Passed Screening",
            "shortlisted": 1,
            "interview_result": "Excellent",
            "final_status": "Hired",
            "final_date": "2026-07-12",
            "final_interviewer": "Ms. HR Leader",
            "virtual_status": "Completed",
            "transcript_status": "Available",
            "interview_type": "Video",
            "applied_days_ago": 3,
            "chatbot": {
                "qualification": "Qualified",
                "score": 0.92,
                "confidence": 0.94,
                "experience": "1.5 years business process modeling",
                "skills": ["Excel", "SQL", "Data Analysis", "Agile"],
                "assessment": [
                    {"question": "How do you gather requirements from stakeholders?", "answer": "I conduct detailed interviews, workshops, and build process maps using BPMN diagrams.", "score": 0.95},
                    {"question": "Explain a time when you resolved conflicting requirements.", "answer": "I aligned both departments by mapping out cost vs revenue projections to drive a consensus decision.", "score": 0.89}
                ]
            }
        },
        {
            "username": "alex_jones",
            "first_name": "Alex",
            "last_name": "Jones",
            "email": "alexjones@example.com",
            "contact": "09307778888",
            "dob": "1995-02-14",
            "location": "Mandaluyong City",
            "job": "Project Analyst",
            "screening": "Failed Screening",
            "shortlisted": 0,
            "interview_result": None,
            "final_status": "Pending",
            "final_date": None,
            "final_interviewer": None,
            "virtual_status": "Pending",
            "transcript_status": "Not Generated",
            "interview_type": "Chat",
            "applied_days_ago": 5,
            "chatbot": None
        },
        {
            "username": "bob_wilson",
            "first_name": "Bob",
            "last_name": "Wilson",
            "email": "bobwilson@example.com",
            "contact": "09441112222",
            "dob": "2000-01-20",
            "location": "Taguig City",
            "job": "Business Analyst",
            "screening": "Passed Screening",
            "shortlisted": 0,
            "interview_result": "Needs Review",
            "final_status": "Rejected",
            "final_date": None,
            "final_interviewer": None,
            "virtual_status": "Completed",
            "transcript_status": "Available",
            "interview_type": "Chat",
            "applied_days_ago": 4,
            "chatbot": {
                "qualification": "Not Qualified",
                "score": 0.48,
                "confidence": 0.75,
                "experience": "Fresh graduate, no work experience",
                "skills": ["Excel"],
                "assessment": [
                    {"question": "How do you gather requirements from stakeholders?", "answer": "I just ask them what they want and write it in a document.", "score": 0.50},
                    {"question": "Explain a time when you resolved conflicting requirements.", "answer": "I haven't encountered that situation yet so I am not sure.", "score": 0.46}
                ]
            }
        }
    ]

    for app in applicants_data:
        # A. Create User
        cur.execute("""
            INSERT INTO users (username, email, password_hash, contact_num, user_type)
            VALUES (%s, %s, 'pbkdf2:sha256:260000$hashedpasswordstub', %s, 'Applicant')
        """, (app["username"], app["email"], app["contact"]))
        user_id = db.insert_id()

        # B. Create Applicant
        resume_url = f"static/uploads/resume_{app['username']}.pdf"
        cur.execute("""
            INSERT INTO applicants (user_id, first_name, last_name, date_of_birth, current_location, resume_url)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, app["first_name"], app["last_name"], app["dob"], app["location"], resume_url))
        applicant_id = db.insert_id()

        # C. Associate Skills
        if app["chatbot"]:
            for s in app["chatbot"]["skills"]:
                if s in skill_ids:
                    cur.execute("INSERT IGNORE INTO applicant_skills (applicant_id, skill_id) VALUES (%s, %s)", (applicant_id, skill_ids[s]))

        # D. Create Application
        applied_date = datetime.date.today() - datetime.timedelta(days=app["applied_days_ago"])
        cur.execute("""
            INSERT INTO applications (applicant_id, job_id, screening_status, shortlisted, interview_result, final_interview_status, final_interview_date, final_interviewer, virtual_interview_status, transcript_status, interview_type, applied_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            applicant_id, 
            job_ids[app["job"]], 
            app["screening"], 
            app["shortlisted"], 
            app["interview_result"],
            app["final_status"],
            app["final_date"],
            app["final_interviewer"],
            app["virtual_status"],
            app["transcript_status"],
            app["interview_type"],
            applied_date
        ))

        # E. Create Chatbot evaluation entry
        c_data = app["chatbot"]
        if c_data:
            cur.execute("""
                INSERT INTO chatbot (user_id, user_name, position, experience, skills, qualification_status, advice, assessment_data, confidence, average_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                app["username"],
                app["job"],
                c_data["experience"],
                json.dumps(c_data["skills"]),
                c_data["qualification"],
                "Sample AI recommendation advice.",
                json.dumps(c_data["assessment"]),
                c_data["confidence"],
                c_data["score"]
            ))

    db.commit()
    cur.close()
    db.close()
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed()
