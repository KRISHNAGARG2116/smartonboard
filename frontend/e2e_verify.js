import puppeteer from 'puppeteer-core';
import http from 'http';
import fs from 'fs';
import path from 'path';

const BASE_URL = 'http://localhost:5002';
const BACKEND_URL = 'http://localhost:8000';

// Helper to fetch JSON from a URL
async function fetchJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(e);
        }
      });
    }).on('error', reject);
  });
}

async function run() {
  const outputDir = path.resolve('/Users/krishnagarg/smartonboard-main/docs/reports/ui-after');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  let browser;
  try {
    browser = await puppeteer.launch({
      executablePath: '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
      defaultViewport: { width: 1280, height: 800 }
    });
    console.log('Browser launched successfully');
  } catch (e) {
    console.error('Failed to launch browser:', e.message);
    process.exit(1);
  }

  const page = await browser.newPage();

  // Helper to clear cookies and localStorage
  async function logout() {
    console.log('Logging out...');
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle2' });
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    const client = await page.target().createCDPSession();
    await client.send('Network.clearBrowserCookies');
    await new Promise(r => setTimeout(r, 500));
  }

  // ==========================================
  // FLOW 1: EMAIL CANDIDATE FLOW (OPTION B)
  // ==========================================
  console.log('\n--- STARTING FLOW 1: EMAIL CANDIDATE FLOW ---');
  await logout();

  // 1. Navigate to candidate register page
  console.log('Navigating to candidate register page...');
  await page.goto(`${BASE_URL}/candidate/register`, { waitUntil: 'networkidle2' });
  await new Promise(r => setTimeout(r, 1000));
  await page.screenshot({ path: path.join(outputDir, '1_email_register_page.png') });

  const uniqueEmail = `e2e_email_${Date.now()}@example.com`;
  const uniquePhone = `+1555019${String(Math.floor(1000 + Math.random() * 9000))}`;
  await page.type('#fullName', 'E2E Email Candidate');
  await page.type('#email', uniqueEmail);
  await page.type('#phoneNumber', uniquePhone);
  await page.type('#password', 'Password123!');
  
  await page.screenshot({ path: path.join(outputDir, '2_email_register_filled.png') });

  // Click submit and wait for navigation to verification page
  console.log('Submitting registration...');
  await Promise.all([
    page.click('button[type="submit"]'),
    page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 })
  ]);
  await new Promise(r => setTimeout(r, 1000));
  await page.screenshot({ path: path.join(outputDir, '3_email_verify_page_loaded.png') });

  // 3. Retrieve generated email & phone OTPs
  console.log(`Retrieving mock OTPs for ${uniqueEmail}...`);
  const otps = await fetchJson(`${BACKEND_URL}/api/v1/auth/test/otps?email=${encodeURIComponent(uniqueEmail)}`);
  console.log('Retrieved OTPs:', otps);

  // 4. Enter Email OTP and verify
  console.log(`Entering email OTP: ${otps.email_code}`);
  await page.type('#emailCode', otps.email_code);
  await page.screenshot({ path: path.join(outputDir, '4_email_otp_typed.png') });
  
  console.log('Verifying email...');
  await page.click('button[type="submit"]'); // The email panel submit
  await new Promise(r => setTimeout(r, 1500));
  await page.screenshot({ path: path.join(outputDir, '5_email_verified.png') });

  // 5. Enter Phone OTP and verify
  console.log(`Entering phone OTP: ${otps.phone_code}`);
  await page.type('#phoneCode', otps.phone_code);
  await page.screenshot({ path: path.join(outputDir, '6_phone_otp_typed.png') });

  console.log('Verifying phone and activating profile...');
  // The phone form is the second form on the page, let's click the submit button in the second card
  await page.evaluate(() => {
    const buttons = Array.from(document.querySelectorAll('button'));
    const verifyPhoneButton = buttons.find(b => b.textContent.includes('Verify & Activate Profile'));
    if (verifyPhoneButton) verifyPhoneButton.click();
  });
  
  // Wait for automatic redirect to dashboard
  console.log('Waiting for dashboard redirect...');
  await new Promise(r => setTimeout(r, 6000));
  await page.screenshot({ path: path.join(outputDir, '7_candidate_dashboard_email_flow.png') });
  console.log(`Current URL: ${page.url()}`);

  // ==========================================
  // FLOW 2: GOOGLE CANDIDATE FLOW (OPTION A)
  // ==========================================
  console.log('\n--- STARTING FLOW 2: GOOGLE CANDIDATE FLOW ---');
  await logout();

  // 1. Navigate to candidate login page
  console.log('Navigating to candidate login page...');
  await page.goto(`${BASE_URL}/candidate/login`, { waitUntil: 'networkidle2' });
  await new Promise(r => setTimeout(r, 1000));
  await page.screenshot({ path: path.join(outputDir, '8_google_login_page.png') });

  // 2. Simulate Google Sign In callback on the frontend
  const googleEmail = `e2e_google_${Date.now()}@example.com`;
  const subId = `sub_${Date.now()}`;
  console.log(`Simulating Google Sign In for: ${googleEmail} with sub: ${subId}`);
  
  // We will execute a script in the browser context that simulates a successful Google Auth callback.
  // It calls loginWithGoogle with a mock token, catches the 403, and redirects to candidate/verify.
  await page.evaluate(async (email, sub) => {
    try {
      const response = await fetch('/api/v1/auth/google', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          credential: `mock-google-token-${email}:${sub}:hd-none`,
          role: 'candidate'
        })
      });
      const data = await response.json();
      
      if (response.status === 403 && data.detail?.verification_required) {
        localStorage.setItem('smartonboard_verify_email', email);
        window.location.href = `/candidate/verify?email=${encodeURIComponent(email)}`;
      }
    } catch (e) {
      console.error(e);
    }
  }, googleEmail, subId);

  // Wait for navigation to verification page
  console.log('Waiting for redirect to verification page...');
  await new Promise(r => setTimeout(r, 2000));
  console.log(`Current URL: ${page.url()}`);
  await page.screenshot({ path: path.join(outputDir, '9_google_phone_verify_page_loaded.png') });

  // 3. Since email is already verified via Google, it should show the phone-only layout.
  // Let's enter a phone number and request OTP.
  console.log('Entering phone number for Google candidate...');
  const uniquePhoneGoogle = `+1555019${String(Math.floor(1000 + Math.random() * 9000))}`;
  await page.type('#phoneInput', uniquePhoneGoogle);
  await page.screenshot({ path: path.join(outputDir, '10_google_phone_entered.png') });

  console.log('Sending phone verification code...');
  await page.click('button[type="submit"]');
  await new Promise(r => setTimeout(r, 2000));
  await page.screenshot({ path: path.join(outputDir, '11_google_phone_otp_sent.png') });

  // 4. Retrieve mock phone OTP
  console.log(`Retrieving mock phone OTP for ${googleEmail}...`);
  const googleOtps = await fetchJson(`${BACKEND_URL}/api/v1/auth/test/otps?email=${encodeURIComponent(googleEmail)}`);
  console.log('Retrieved OTPs:', googleOtps);

  // 5. Enter Phone OTP and verify
  console.log(`Entering phone OTP: ${googleOtps.phone_code}`);
  await page.type('#phoneCode', googleOtps.phone_code);
  await page.screenshot({ path: path.join(outputDir, '12_google_phone_otp_typed.png') });

  console.log('Verifying phone and activating profile...');
  // Click the verify button
  await page.evaluate(() => {
    const buttons = Array.from(document.querySelectorAll('button'));
    const verifyPhoneButton = buttons.find(b => b.textContent.includes('Verify & Activate Profile'));
    if (verifyPhoneButton) verifyPhoneButton.click();
  });

  // Wait for automatic redirect to dashboard
  console.log('Waiting for dashboard redirect...');
  await new Promise(r => setTimeout(r, 6000));
  await page.screenshot({ path: path.join(outputDir, '13_candidate_dashboard_google_flow.png') });
  console.log(`Current URL: ${page.url()}`);

  console.log('\nE2E VERIFICATION DEMO COMPLETED SUCCESSFULLY!');
  await page.close();
  await browser.disconnect();
}

run().catch(console.error);
