import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# Make sure output directory exists
os.makedirs("static/uploads", exist_ok=True)

def create_resume_pdf(filename, name, email, phone, role, skills, experience_text, edu_text):
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor='#B2271B',
        alignment=TA_CENTER,
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor='#475569',
        alignment=TA_CENTER,
        spaceAfter=15
    )

    section_style = ParagraphStyle(
        'DocSection',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor='#1E3E62',
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor='#1f2937',
        spaceAfter=8
    )

    bold_body_style = ParagraphStyle(
        'DocBodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    story = []
    
    # Header
    story.append(Paragraph(name, title_style))
    story.append(Paragraph(f"Email: {email}  |  Phone: {phone}  |  Address: Metro Manila, Philippines", subtitle_style))
    story.append(Spacer(1, 10))
    
    # Target Role
    story.append(Paragraph("POSITION APPLIED FOR", section_style))
    story.append(Paragraph(role, bold_body_style))
    story.append(Spacer(1, 8))
    
    # Skills Section
    story.append(Paragraph("TECHNICAL & PROFESSIONAL SKILLS", section_style))
    story.append(Paragraph(", ".join(skills), body_style))
    story.append(Spacer(1, 8))
    
    # Experience Section
    story.append(Paragraph("PROFESSIONAL EXPERIENCE", section_style))
    for exp in experience_text:
        story.append(Paragraph(f"<b>{exp['job_title']}</b> — {exp['company']}", bold_body_style))
        story.append(Paragraph(f"<i>{exp['years']}</i>", body_style))
        story.append(Paragraph(exp['description'], body_style))
        story.append(Spacer(1, 4))
    story.append(Spacer(1, 8))
    
    # Education Section
    story.append(Paragraph("EDUCATION", section_style))
    story.append(Paragraph(edu_text, body_style))
    
    doc.build(story)
    print(f"Generated PDF: {filename}")

# Generate resumes for all 5 sample candidates
candidates = [
    {
        "filename": "static/uploads/resume_denise_dc.pdf",
        "name": "Denise Dela Cruz",
        "email": "denise.delacruz@example.com",
        "phone": "09171234567",
        "role": "Java Developer",
        "skills": ["Java", "Spring Boot", "MySQL", "Hibernate", "HTML", "CSS", "JavaScript", "REST APIs"],
        "experience": [
            {
                "job_title": "Junior Java Developer",
                "company": "Tech Solutions Inc.",
                "years": "2024 - Present",
                "description": "Responsible for developing, maintaining, and deploying enterprise Java backend APIs using Spring Boot, Hibernate, and MySQL."
            }
        ],
        "edu": "Bachelor of Science in Computer Science, University of Santo Tomas (2024)"
    },
    {
        "filename": "static/uploads/resume_john_doe.pdf",
        "name": "John Doe",
        "email": "johndoe@example.com",
        "phone": "09189876543",
        "role": "Java Developer",
        "skills": ["Java", "MySQL", "PHP", "HTML", "CSS", "JavaScript", "Apache Web Server"],
        "experience": [
            {
                "job_title": "Full-Stack Developer",
                "company": "Web Development Hub",
                "years": "2021 - 2024",
                "description": "Built PHP-based web portals, handled MySQL database queries, and implemented front-end templates."
            }
        ],
        "edu": "Bachelor of Science in Information Technology, Quezon City University (2021)"
    },
    {
        "filename": "static/uploads/resume_jane_smith.pdf",
        "name": "Jane Smith",
        "email": "janesmith@example.com",
        "phone": "09204445555",
        "role": "Business Analyst",
        "skills": ["Excel", "SQL", "Data Analysis", "BPMN Process Modeling", "Agile Methodologies", "Jira"],
        "experience": [
            {
                "job_title": "Associate Systems Analyst",
                "company": "Global Financial Services",
                "years": "2023 - 2025",
                "description": "Analyzed operational process flows, drafted user stories and business requirements documents (BRDs), and acted as a liaison between tech and product teams."
            }
        ],
        "edu": "Bachelor of Science in Business Administration major in MIS, Ateneo de Manila University (2023)"
    },
    {
        "filename": "static/uploads/resume_alex_jones.pdf",
        "name": "Alex Jones",
        "email": "alexjones@example.com",
        "phone": "09307778888",
        "role": "Project Analyst",
        "skills": ["Project Management", "MS Project", "Trello", "Documentation", "Communication"],
        "experience": [
            {
                "job_title": "Administrative Assistant",
                "company": "Pioneer Logistics Corp",
                "years": "2022 - 2024",
                "description": "Managed office schedules, prepared presentation decks, and organized document archives."
            }
        ],
        "edu": "Bachelor of Arts in Communication, Far Eastern University (2022)"
    },
    {
        "filename": "static/uploads/resume_bob_wilson.pdf",
        "name": "Bob Wilson",
        "email": "bobwilson@example.com",
        "phone": "09441112222",
        "role": "Business Analyst",
        "skills": ["MS Excel", "PowerPoint", "Basic Accounting"],
        "experience": [
            {
                "job_title": "Intern",
                "company": "SME Accounting Services",
                "years": "Summer 2023",
                "description": "Assisted with monthly data entry and filing paper invoices."
            }
        ],
        "edu": "Bachelor of Science in Business Administration, Pamantasan ng Lungsod ng Maynila (2024)"
    }
]

for c in candidates:
    create_resume_pdf(
        c["filename"],
        c["name"],
        c["email"],
        c["phone"],
        c["role"],
        c["skills"],
        c["experience"],
        c["edu"]
    )

print("All resumes created successfully.")
