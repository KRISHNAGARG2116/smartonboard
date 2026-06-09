import os

files_to_update = [
    '/Users/krishnagarg/smartonboard-main/frontend/src/components/AppLayout.tsx',
    '/Users/krishnagarg/smartonboard-main/frontend/src/components/CandidateLayout.tsx',
    '/Users/krishnagarg/smartonboard-main/frontend/src/pages/candidate/CandidateDashboard.tsx',
    '/Users/krishnagarg/smartonboard-main/frontend/src/pages/recruiter/RecruiterDashboard.tsx',
    '/Users/krishnagarg/smartonboard-main/frontend/src/pages/CandidateProfilePage.tsx',
    '/Users/krishnagarg/smartonboard-main/frontend/src/pages/CandidateInterviews.tsx',
    '/Users/krishnagarg/smartonboard-main/frontend/src/pages/CandidateApplications.tsx',
    '/Users/krishnagarg/smartonboard-main/frontend/src/pages/CandidateJobFeed.tsx',
    '/Users/krishnagarg/smartonboard-main/frontend/src/pages/AnalyticsDashboard.tsx',
    '/Users/krishnagarg/smartonboard-main/frontend/src/pages/recruiter/RecruiterSettings.tsx',
    '/Users/krishnagarg/smartonboard-main/frontend/src/pages/PipelineBoard.tsx'
]

replacements = {
    # Buttons - remove hardcoded and replace with token
    "borderRadius: '36px'": "borderRadius: 'var(--radius-buttons)'",
    "borderRadius: '22.5px'": "borderRadius: 'var(--radius-buttons)'",
    'borderRadius: "36px"': 'borderRadius: "var(--radius-buttons)"',
    'borderRadius: "22.5px"': 'borderRadius: "var(--radius-buttons)"',
    
    # Cards - remove custom 12px/8px radii and align to 24px token
    "borderRadius: '12px'": "borderRadius: 'var(--radius-cards)'",
    "borderRadius: '8px'": "borderRadius: 'var(--radius-cards)'",
    'borderRadius: "12px"': 'borderRadius: "var(--radius-cards)"',
    'borderRadius: "8px"': 'borderRadius: "var(--radius-cards)"',
    
    # Remove boxShadow overrides that disable cards shadows
    ", boxShadow: 'none'": "",
    ",boxShadow: 'none'": "",
    "boxShadow: 'none',": "",
    'boxShadow: "none",': "",
    
    # Clean up logo mark custom styling
    "borderRadius: '0px',\n              background: 'var(--accent)'": "borderRadius: '6px',\n              background: 'var(--color-rust)'",
    "borderRadius: '0px',\n                background: 'var(--accent)'": "borderRadius: '6px',\n                background: 'var(--color-rust)'",
    "borderRadius: '0px',\n              background: 'var(--color-rust)'": "borderRadius: '6px',\n              background: 'var(--color-rust)'"
}

print("Running design reconstruction pass...")

for filepath in files_to_update:
    if not os.path.exists(filepath):
        print(f"Skipping non-existent: {filepath}")
        continue
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        modified = content
        replaced_count = 0
        for target, replacement in replacements.items():
            if target in modified:
                count = modified.count(target)
                modified = modified.replace(target, replacement)
                replaced_count += count
                
        if replaced_count > 0:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(modified)
            print(f"Updated {filepath} ({replaced_count} replacements)")
        else:
            print(f"No changes made for {filepath}")
    except Exception as e:
        print(f"Error updating {filepath}: {e}")

print("Sweep completed.")
