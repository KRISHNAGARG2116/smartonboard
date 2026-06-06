import requests
import sys

BASE_URL = "http://localhost:8000/api"

print("Starting API Audit Flow...")

# Helper to print responses
def check(res, expected_status, name):
    if res.status_code == expected_status:
        print(f"✅ {name}: Status {res.status_code} as expected.")
        return True
    else:
        print(f"❌ {name}: Unexpected Status {res.status_code} (Expected {expected_status})")
        print(f"   Response: {res.text}")
        return False

# 1. Recruiter registration with public email
print("\n--- Auditing Recruiter Registration ---")
email_public = "recruiter@gmail.com"
payload_public = {
    "email": email_public,
    "password": "Password123!",
    "full_name": "Test Recruiter",
    "company_name": "Test Corp"
}
res = requests.post(f"{BASE_URL}/v1/auth/register", json=payload_public)
check(res, 400, "Block public mail hosts")

# Recruiter registration with corporate email but invalid DNS/MX
email_invalid_dns = "recruiter@nonexistent-domain-xyz-12345.com"
payload_invalid_dns = {
    "email": email_invalid_dns,
    "password": "Password123!",
    "full_name": "Test Recruiter",
    "company_name": "Test Corp"
}
res = requests.post(f"{BASE_URL}/v1/auth/register", json=payload_invalid_dns)
check(res, 400, "Block invalid DNS/MX domain")

# Recruiter registration with valid email (using a real domain, e.g. google.com which has MX records)
# Wait, google.com is corporate for google but let's check if google.com is in PUBLIC_MAIL_HOSTS. Yes, googlemail.com/gmail.com are there, but not google.com.
email_valid = "recruiter@google.com"
payload_valid = {
    "email": email_valid,
    "password": "Password123!",
    "full_name": "Google Recruiter",
    "company_name": "Google Inc"
}
res = requests.post(f"{BASE_URL}/v1/auth/register", json=payload_valid)
recruiter_token = None
if res.status_code == 201:
    print("✅ Recruiter registration successful.")
    recruiter_token = res.json()["access_token"]
elif res.status_code == 409:
    print("ℹ️ Recruiter already registered. Logging in...")
    # Login
    res_login = requests.post(f"{BASE_URL}/v1/auth/login", json={
        "email": email_valid,
        "password": "Password123!"
    })
    if check(res_login, 200, "Recruiter login"):
        recruiter_token = res_login.json()["access_token"]
else:
    check(res, 201, "Recruiter registration")

# 2. Candidate Registration and Login
print("\n--- Auditing Candidate Flow ---")
candidate_email = "candidate_audit@test.com"
payload_candidate = {
    "email": candidate_email,
    "password": "Password123!",
    "full_name": "Audit Candidate"
}
res = requests.post(f"{BASE_URL}/v1/auth/register/candidate", json=payload_candidate)
candidate_token = None
if res.status_code == 201:
    print("✅ Candidate registration successful.")
    candidate_token = res.json()["access_token"]
elif res.status_code == 409:
    print("ℹ️ Candidate already registered. Logging in...")
    res_login = requests.post(f"{BASE_URL}/v1/auth/login/candidate", json={
        "email": candidate_email,
        "password": "Password123!"
    })
    if check(res_login, 200, "Candidate login"):
        candidate_token = res_login.json()["access_token"]
else:
    check(res, 201, "Candidate registration")

if not candidate_token:
    print("FATAL: Could not get candidate token.")
    sys.exit(1)

headers = {"Authorization": f"Bearer {candidate_token}"}

# Check candidate profile me
res = requests.get(f"{BASE_URL}/v1/auth/candidate/me", headers=headers)
if check(res, 200, "Get candidate me"):
    me_data = res.json()
    print("   Email verified status:", me_data["profile"]["email_verified"])
    print("   Phone verified status:", me_data["profile"]["phone_verified"])

# 3. Email Verification Flow
print("\n--- Auditing Email Verification ---")
res = requests.post(f"{BASE_URL}/v1/auth/candidate/email/send-otp", json={"email": candidate_email})
check(res, 200, "Send email verification OTP")
# Since it is a test provider or stub, the code is printed in the logs or saved in DB. Let's see if we can find it or verify if it works.
# Wait, let's look at the database to see what code was generated. But since we do not change code, let's check if the verify endpoint enforces correct OTP.
res = requests.post(f"{BASE_URL}/v1/auth/candidate/email/verify-otp", json={
    "email": candidate_email,
    "code": "000000" # incorrect code
})
check(res, 400, "Verify email OTP - incorrect code rejected")

# 4. Route Isolation checks
print("\n--- Auditing Route Isolation ---")
# Candidate trying to access recruiter me
res = requests.get(f"{BASE_URL}/v1/auth/me", headers=headers)
check(res, 401, "Candidate access to recruiter /me (Should be 401)")

# Recruiter trying to access candidate me
if recruiter_token:
    recruiter_headers = {"Authorization": f"Bearer {recruiter_token}"}
    res = requests.get(f"{BASE_URL}/v1/auth/candidate/me", headers=recruiter_headers)
    check(res, 403, "Recruiter access to candidate /me (Should be 403)")

# 5. Verification Enforcement checks
print("\n--- Auditing Verification Enforcement ---")
# Candidate listing jobs feed
res = requests.get(f"{BASE_URL}/v1/jobs/feed", headers=headers)
check(res, 200, "Unverified candidate views jobs feed")

# Candidate listing resumes
res = requests.get(f"{BASE_URL}/v1/auth/candidate/resumes", headers=headers)
check(res, 200, "Unverified candidate views resumes")

print("\nAudit completed.")
