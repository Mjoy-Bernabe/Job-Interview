import os

files = ['templates/admin_dashboard.html', 'templates/admin_recruitment.html', 'templates/admin_analytics.html']

old_logo = '''<div class="logo-area" style="padding: 30px 20px; text-align: center;">
            <img src="{{ url_for('static', filename='logo.svg') }}" alt="H2 Logo" style="width: 100%; max-width: 200px; display: block; margin: 0 auto;">
        </div>'''

new_logo = '''<div class="logo-area" style="padding: 0; text-align: center;">
            <img src="{{ url_for('static', filename='logo.svg') }}" alt="H2 Logo" style="width: 100%; display: block; margin: 0 auto;">
        </div>'''

for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    content = content.replace(old_logo, new_logo)

    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)

print('Done!')
