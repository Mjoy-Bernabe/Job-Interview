import os
import re

files = ['templates/admin_dashboard.html', 'templates/admin_recruitment.html', 'templates/admin_analytics.html']

logo_replacement = '''        <div class="logo-area" style="padding: 30px 20px; text-align: center;">
            <img src="{{ url_for('static', filename='logo.svg') }}" alt="H2 Logo" style="width: 100%; max-width: 200px; display: block; margin: 0 auto;">
        </div>'''

for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Replace Logo
    content = re.sub(r'<div class="logo-area">.*?</div>\s*</div>', logo_replacement, content, flags=re.DOTALL)
    
    # Replace icons
    content = content.replace("<i class='bx bxs-grid-alt'></i>", "<img src=\"{{ url_for('static', filename='Dashboard Layout.svg') }}\" alt=\"Dashboard\" style=\"width: 24px; height: 24px;\">")
    content = content.replace("<i class='bx bx-user-pin'></i>", "<img src=\"{{ url_for('static', filename='Client Management.svg') }}\" alt=\"Recruitment\" style=\"width: 24px; height: 24px;\">")
    content = content.replace("<i class='bx bx-line-chart'></i>", "<img src=\"{{ url_for('static', filename='Graph.svg') }}\" alt=\"Analytics\" style=\"width: 24px; height: 24px;\">")
    content = content.replace("<i class='bx bx-cog'></i>", "<img src=\"{{ url_for('static', filename='Automation.svg') }}\" alt=\"Settings\" style=\"width: 24px; height: 24px;\">")
    content = content.replace("<i class='bx bx-user-circle'></i>", "<img src=\"{{ url_for('static', filename='Profile.svg') }}\" alt=\"Profile\" style=\"width: 24px; height: 24px;\">")

    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
print('Done!')
