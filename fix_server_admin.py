with open('server/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('if user.username == "Midnight":', 'if user.username.lower() == "midnight":')

with open('server/main.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated admin check')
