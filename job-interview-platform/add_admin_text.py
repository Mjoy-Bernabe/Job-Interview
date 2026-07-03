import os

files = ['templates/admin_dashboard.html', 'templates/admin_recruitment.html', 'templates/admin_analytics.html']

old_logo = '''<div class="logo-area" style="padding: 0; text-align: center;">
            <img src="{{ url_for('static', filename='logo.svg') }}" alt="H2 Logo" style="width: 100%; display: block; margin: 0 auto;">
        </div>'''

new_logo = '''<div class="logo-area" style="padding: 0; text-align: center;">
            <img src="{{ url_for('static', filename='logo.svg') }}" alt="H2 Logo" style="width: 100%; display: block; margin: 0 auto;">
            <div style="font-family: 'Poppins', sans-serif; font-size: 13px; font-weight: 600; color: #B3241B; letter-spacing: 4px; text-transform: uppercase; margin-top: 5px; margin-bottom: 25px;">Administration</div>
        </div>'''

for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    content = content.replace(old_logo, new_logo)

    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)

print('Done!')
