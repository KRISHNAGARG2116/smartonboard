import os
import re

src_dir = '/Users/krishnagarg/smartonboard-main/frontend/src'

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # 1. Replace background: 'var(--color-dark-cork)', color: 'var(--text)' with white text
    # Match double and single quote variations, arbitrary spacing
    content = re.sub(
        r"background:\s*['\"]var\(--color-dark-cork\)['\"],\s*color:\s*['\"]var\(--text\)['\"]",
        "background: 'var(--color-dark-cork)', color: 'var(--color-pure-white)'",
        content
    )
    content = re.sub(
        r"backgroundColor:\s*['\"]var\(--color-dark-cork\)['\"],\s*color:\s*['\"]var\(--text\)['\"]",
        "backgroundColor: 'var(--color-dark-cork)', color: 'var(--color-pure-white)'",
        content
    )

    # 2. Replace undefined var(--color-studio-black) modal/card background with var(--surface)
    content = content.replace("var(--color-studio-black)", "var(--surface)")

    # 3. Replace border: '1px solid var(--color-warm-cream)' with var(--border) in modals using var(--surface)
    # This prevents white borders on white cards in light mode
    content = content.replace("border: '1px solid var(--color-warm-cream)'", "border: '1px solid var(--border)'")
    content = content.replace('border: "1px solid var(--color-warm-cream)"', 'border: "1px solid var(--border)"')

    # 4. Fix RecruiterDashboard.tsx specific issues
    if 'RecruiterDashboard.tsx' in filepath:
        # Selection row color change
        content = content.replace(
            "background: selectedAppForAi?.id === app.id ? 'var(--color-dark-cork)' : 'transparent'",
            "background: selectedAppForAi?.id === app.id ? 'var(--accent-subtle)' : 'transparent'"
        )
        # Fix AI Copilot Command Hub Card background from transparent to var(--surface)
        content = content.replace(
            "border: '1px solid var(--color-burnt-sienna)', background: 'transparent'",
            "border: '1px solid var(--color-burnt-sienna)', background: 'var(--surface)'"
        )
        # Fix AI Copilot Command Hub Header color from warm-cream (white) to var(--text)
        content = content.replace(
            "color: 'var(--color-warm-cream)'",
            "color: 'var(--text)'"
        )
        # Fix AI Candidate Summary box background from black (var(--color-dark-cork)) to cool sky wash
        content = content.replace(
            "background: 'var(--color-dark-cork)', fontSize: '13px'",
            "background: 'var(--color-sky-wash)', fontSize: '13px'"
        )
        # Fix skill chips border and text colors
        content = content.replace(
            "borderColor: 'var(--color-forest-grid)', color: 'var(--color-warm-cream)'",
            "borderColor: 'var(--border)', color: 'var(--text-secondary)'"
        )

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed visibility bugs in: {filepath}")

# Walk through src directory
for root, dirs, files in os.walk(src_dir):
    for file in files:
        if file.endswith(('.tsx', '.ts', '.css', '.js')):
            fix_file(os.path.join(root, file))

print("Visibility correction complete!")
