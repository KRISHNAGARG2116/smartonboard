import os
import re

HEX_REGEX = re.compile(r'#[0-9a-fA-F]{3,8}\b')

exclude_dirs = {'node_modules', 'dist', 'build', '.git'}

print("Starting scan for hardcoded hex colors...")
found_any = False

for root, dirs, files in os.walk('/Users/krishnagarg/smartonboard-main/frontend'):
    dirs[:] = [d for d in dirs if d not in exclude_dirs]
    for file in files:
        if file.endswith(('.tsx', '.ts', '.css')) and not file.endswith(('variables.css', 'theme.css')):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                matches = HEX_REGEX.findall(content)
                if matches:
                    print(f"File: {path}")
                    for match in set(matches):
                        print(f"  - {match}")
                    found_any = True
            except Exception as e:
                print(f"Error reading {path}: {e}")

if not found_any:
    print("No hardcoded hex colors found in the scanned files.")
else:
    print("Scan complete.")
