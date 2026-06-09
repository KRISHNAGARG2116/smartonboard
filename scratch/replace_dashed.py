import os

files_to_update = [
    '/Users/krishnagarg/smartonboard-main/frontend/src/pages/candidate/CandidateDashboard.tsx',
    '/Users/krishnagarg/smartonboard-main/frontend/src/pages/recruiter/RecruiterDashboard.tsx',
    '/Users/krishnagarg/smartonboard-main/frontend/src/pages/AnalyticsDashboard.tsx',
    '/Users/krishnagarg/smartonboard-main/frontend/src/pages/CandidateApplications.tsx',
    '/Users/krishnagarg/smartonboard-main/frontend/src/pages/CandidateInterviews.tsx',
    '/Users/krishnagarg/smartonboard-main/frontend/src/pages/CandidateJobFeed.tsx',
    '/Users/krishnagarg/smartonboard-main/frontend/src/pages/CandidateProfilePage.tsx',
    '/Users/krishnagarg/smartonboard-main/frontend/src/pages/recruiter/RecruiterJobs.tsx',
    '/Users/krishnagarg/smartonboard-main/frontend/src/pages/recruiter/RecruiterSettings.tsx',
    '/Users/krishnagarg/smartonboard-main/frontend/src/pages/recruiter/RecruiterInterviews.tsx',
    '/Users/krishnagarg/smartonboard-main/frontend/src/components/AppLayout.tsx',
    '/Users/krishnagarg/smartonboard-main/frontend/src/components/CandidateLayout.tsx',
    '/Users/krishnagarg/smartonboard-main/frontend/src/pages/PipelineBoard.tsx'
]

print("Replacing dashed borders with solid borders...")

replacements = {
    "border: '1px dashed var(--color-cork-shadow)'": "border: '1px solid var(--border)'",
    "border: '1.5px dashed var(--color-cork-shadow)'": "border: '1px solid var(--border)'",
    "border: '1.5px dashed var(--color-burnt-sienna)'": "border: '1px solid var(--color-burnt-sienna)'",
    'border: "1px dashed var(--color-cork-shadow)"': 'border: "1px solid var(--border)"',
    "border: '1px dashed var(--border)'": "border: '1px solid var(--border)'",
    "borderTop: '1px dashed var(--color-cork-shadow)'": "borderTop: '1px solid var(--border)'",
    "borderBottom: '1px dashed var(--color-cork-shadow)'": "borderBottom: '1px solid var(--border)'",
    "borderBottom: '1px dashed var(--color-cork-shadow)',": "borderBottom: '1px solid var(--border)',",
    "border: '1px dashed var(--color-cork-shadow)'": "border: '1px solid var(--border)'",
    'border: "1px dashed var(--color-cork-shadow)"': 'border: "1px solid var(--border)"',
    "borderTop: '1px dashed var(--border)'": "borderTop: '1px solid var(--border)'",
    "borderBottom: '1px dashed var(--border)'": "borderBottom: '1px solid var(--border)'"
}

for filepath in files_to_update:
    if not os.path.exists(filepath):
        print(f"Skipping non-existent path: {filepath}")
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
            print(f"No replacements needed for {filepath}")
    except Exception as e:
        print(f"Error updating {filepath}: {e}")

print("Replacement complete.")
