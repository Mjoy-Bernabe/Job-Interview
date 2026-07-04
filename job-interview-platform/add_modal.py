import os
import re

file_path = 'templates/admin_dashboard.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

css_to_add = '''
        /* Modal Styles */
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background-color: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
        .modal-content {
            background-color: #f4f4f4;
            width: 1266px;
            max-width: 95vw;
            height: 1171px;
            max-height: 95vh;
            border-radius: 12px;
            position: relative;
            padding: 60px;
            overflow-y: auto;
            color: black;
            font-family: 'Inter', sans-serif;
            display: flex;
            flex-direction: column;
        }
        .close-btn {
            position: absolute;
            top: 40px;
            right: 40px;
            background: none;
            border: none;
            cursor: pointer;
        }
        .close-btn img {
            width: 40px;
            height: 40px;
        }
        .modal-title {
            font-family: 'Poppins', sans-serif;
            font-size: 56px;
            font-weight: 700;
            margin-bottom: 10px;
        }
        .modal-subtitle {
            font-family: 'Poppins', sans-serif;
            font-size: 28px;
            color: #B3241B;
            font-weight: 600;
            margin-bottom: 50px;
        }
        .modal-cards-row {
            display: flex;
            gap: 10px;
            margin-bottom: 60px;
        }
        .modal-card {
            flex: 1;
            background: white;
            border-radius: 12px;
            padding: 40px 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }
        .modal-card-title {
            font-family: 'Poppins', sans-serif;
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 40px;
        }
        .modal-card-status {
            font-family: 'Poppins', sans-serif;
            font-size: 40px;
            font-weight: 700;
            letter-spacing: 2px;
            margin-bottom: 40px;
        }
        .modal-card-status.eligible { color: #1256D4; }
        .modal-card-status.qualified { color: #08C425; }
        .modal-card-desc {
            font-size: 16px;
            line-height: 1.6;
        }
        .btn-resume {
            background-color: #B3241B;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-family: 'Poppins', sans-serif;
            font-size: 24px;
            font-weight: 600;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            box-shadow: 0 8px 4px rgba(0,0,0,0.15);
            cursor: pointer;
            width: 100%;
        }
        .btn-resume img { width: 32px; height: 32px; }
        
        .qa-section {
            margin-top: auto;
            display: flex;
            flex-direction: column;
            gap: 20px;
            width: calc(100% - 280px);
        }
        .qa-title {
            font-family: 'Poppins', sans-serif;
            font-size: 28px;
            color: #B3241B;
            font-weight: 600;
        }
        .qa-content {
            background: white;
            padding: 30px;
            border-radius: 8px;
            font-size: 16px;
            line-height: 1.6;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }
        .recorded-text {
            color: #B3241B;
            font-size: 14px;
            font-weight: 700;
            display: block;
            margin-top: 20px;
        }
        
        .modal-actions {
            display: flex;
            flex-direction: column;
            gap: 10px;
            position: absolute;
            bottom: 60px;
            right: 60px;
        }
        .btn-action {
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-family: 'Poppins', sans-serif;
            font-size: 28px;
            font-weight: 600;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            box-shadow: 0 8px 4px rgba(0,0,0,0.15);
            cursor: pointer;
            width: 220px;
        }
        .btn-action.accept { background-color: #B3241B; }
        .btn-action.reject { background-color: #825F5C; }
        .btn-action img { width: 32px; height: 32px; }
    </style>
'''

html_to_add = '''
        <!-- Applicant Modal -->
        <div id="applicantModal" class="modal-overlay" style="display: none;">
            <div class="modal-content">
                <button class="close-btn" onclick="closeModal()">
                    <img src="{{ url_for('static', filename='Close Window.svg') }}" alt="Close">
                </button>
                
                <h1 class="modal-title">Maryjoy Bernabe</h1>
                <h3 class="modal-subtitle">Applying as: Software Engineer</h3>

                <div class="modal-cards-row">
                    <div style="flex: 1; display: flex; flex-direction: column; gap: 20px;">
                        <div class="modal-card" style="height: 100%;">
                            <div class="modal-card-title">Pre-screening Outcome</div>
                            <div class="modal-card-status eligible">ELIGIBLE</div>
                            <div class="modal-card-desc">
                                <strong>Experience:</strong> 4 yrs<br>
                                <strong>Skills:</strong> Javascript, Laravel, Python, SQL
                            </div>
                        </div>
                        <button class="btn-resume">
                            View Resume <img src="{{ url_for('static', filename='Resume.svg') }}" alt="Resume">
                        </button>
                    </div>
                    
                    <div class="modal-card">
                        <div class="modal-card-title">ANN Interview Evaluation</div>
                        <div class="modal-card-status qualified">QUALIFIED</div>
                        <div class="modal-card-desc">
                            <strong>Average Score:</strong> 78% confidence level
                        </div>
                    </div>
                </div>

                <div class="qa-section">
                    <h2 class="qa-title">Detailed Interview Q&A</h2>
                    <div class="qa-content">
                        <strong>Q1: Tell me about yourself.</strong><br>
                        <em>"Good day! My name is Mary Joy Bernabe. I am a computer science student who is passionate about technology, problem-solving, and software development. I have experience creating web and mobile applications using different programming languages and tools such as Python, Flask, PHP, MySQL, HTML, CSS, and JavaScript. I am hardworking, willing to learn, and can adapt quickly to new environments. I also enjoy working with a team and improving my skills through projects and research. One of the projects I worked on is a job interview platform simulation that uses artificial intelligence concepts for applicant evaluation. I am seeking an opportunity where I can apply my knowledge, gain professional experience, and continue growing in the field of technology."</em><br>
                        <span class="recorded-text">Recorded</span>
                    </div>
                </div>

                <div class="modal-actions">
                    <button class="btn-action accept">
                        Accept <img src="{{ url_for('static', filename='Checkmark.svg') }}" alt="Accept">
                    </button>
                    <button class="btn-action reject">
                        Reject <img src="{{ url_for('static', filename='Cancel.svg') }}" alt="Reject">
                    </button>
                </div>
            </div>
        </div>
    </main>
'''

js_to_add = '''
        function openModal() {
            document.getElementById('applicantModal').style.display = 'flex';
        }
        function closeModal() {
            document.getElementById('applicantModal').style.display = 'none';
        }

        function switchTab(tab) {
'''

content = content.replace('    </style>', css_to_add)
content = content.replace('    </main>', html_to_add)
content = content.replace('        function switchTab(tab) {', js_to_add)

# Add onclick to list items
content = content.replace('<div class="va-list-item">', '<div class="va-list-item" onclick="openModal()">')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Modal added!")
