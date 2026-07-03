import os

files = ['templates/admin_dashboard.html', 'templates/admin_recruitment.html', 'templates/admin_analytics.html']

for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Replace link
    content = content.replace(
        'https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&family=Outfit:wght@400;600;700&family=Poppins:wght@300;400;500;600&display=swap',
        'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@300;400;500;600;700&display=swap'
    )
    
    # Replace Outfit with Poppins
    content = content.replace("'Outfit', sans-serif", "'Poppins', sans-serif")
    
    # Replace Courier Prime with Inter
    content = content.replace("'Courier Prime', monospace", "'Inter', sans-serif")
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
