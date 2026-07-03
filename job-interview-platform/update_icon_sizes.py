import os

files = ['templates/admin_dashboard.html', 'templates/admin_recruitment.html', 'templates/admin_analytics.html']

for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Replace the inline style sizing for all 5 SVG icons
    content = content.replace('style="width: 24px; height: 24px;"', 'style="width: 2em; height: 2em;"')

    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
print('Done!')
