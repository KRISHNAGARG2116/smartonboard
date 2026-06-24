import os
import sys
from PIL import Image

output_dir = "/Users/krishnagarg/smartonboard-main/docs/reports/ui-after"
files = [
    "candidate_login.png",
    "candidate_register.png",
    "candidate_verification.png",
    "candidate_dashboard.png",
    "recruiter_login.png",
    "recruiter_setup_company.png",
    "recruiter_dashboard.png",
    "pipeline_board.png"
]

print("=== SCREENSHOT COLOR ANALYSIS ===")
for filename in files:
    filepath = os.path.join(output_dir, filename)
    if not os.path.exists(filepath):
        print(f"{filename}: NOT FOUND")
        continue
    try:
        with Image.open(filepath) as img:
            img_rgb = img.convert('RGB')
            pixels = list(img_rgb.getdata())
            # Calculate average brightness (0-255)
            brightnesses = [0.299 * r + 0.587 * g + 0.114 * b for (r, g, b) in pixels]
            avg_brightness = sum(brightnesses) / len(brightnesses)
            
            # Count dark vs light pixels (threshold = 127)
            dark_pixels = sum(1 for b in brightnesses if b < 127)
            light_pixels = len(brightnesses) - dark_pixels
            dark_pct = (dark_pixels / len(brightnesses)) * 100
            
            theme = "DARK" if dark_pct > 50 else "LIGHT"
            print(f"{filename}: Avg Brightness = {avg_brightness:.2f}, Dark Pixels = {dark_pct:.1f}%, Detected Theme = {theme}")
    except Exception as e:
        print(f"{filename}: ERROR - {e}")
