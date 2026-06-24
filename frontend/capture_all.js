import puppeteer from 'puppeteer-core';
import http from 'http';
import fs from 'fs';
import path from 'path';

const BASE_URL = 'http://localhost:5002';
const BACKEND_URL = 'http://localhost:8000';
const OUTPUT_DIR = path.resolve('/Users/krishnagarg/smartonboard-main/docs/reports/ui-after');

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
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
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
    console.log('Logging out / clearing storage...');
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle2' });
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    const client = await page.target().createCDPSession();
    await client.send('Network.clearBrowserCookies');
    await new Promise(r => setTimeout(r, 1000));
  }

  try {
    // ==========================================
    // 1. CANDIDATE LOGIN PAGE
    // ==========================================
    console.log('\n--- Capturing Candidate Login ---');
    await logout();
    await page.goto(`${BASE_URL}/candidate/login`, { waitUntil: 'networkidle2' });
    await new Promise(r => setTimeout(r, 1500));
    await page.screenshot({ path: path.join(OUTPUT_DIR, 'candidate_login.png') });
    console.log('Captured candidate_login.png');

    // ==========================================
    // 2. CANDIDATE REGISTER PAGE
    // ==========================================
    console.log('\n--- Capturing Candidate Register ---');
    await page.goto(`${BASE_URL}/candidate/register`, { waitUntil: 'networkidle2' });
    await new Promise(r => setTimeout(r, 1500));
    await page.screenshot({ path: path.join(OUTPUT_DIR, 'candidate_register.png') });
    console.log('Captured candidate_register.png');

    // Fill in Candidate details to trigger verification
    const candEmail = `cand_steep_reset_${Date.now()}@example.com`;
    const candPhone = `+1555019${String(Math.floor(1000 + Math.random() * 9000))}`;
    await page.type('#fullName', 'Steep Candidate');
    await page.type('#email', candEmail);
    await page.type('#phoneNumber', candPhone);
    await page.type('#password', 'Password123!');
    
    // Submit registration
    console.log('Submitting candidate registration...');
    await Promise.all([
      page.click('button[type="submit"]'),
      page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 })
    ]);
    await new Promise(r => setTimeout(r, 1500));

    // ==========================================
    // 3. CANDIDATE VERIFICATION PAGE
    // ==========================================
    console.log('\n--- Capturing Candidate Verification ---');
    await page.screenshot({ path: path.join(OUTPUT_DIR, 'candidate_verification.png') });
    console.log('Captured candidate_verification.png');

    // Fetch and fill OTPs to proceed to Candidate Dashboard
    console.log(`Fetching OTPs for ${candEmail}...`);
    const candOtps = await fetchJson(`${BACKEND_URL}/api/v1/auth/test/otps?email=${encodeURIComponent(candEmail)}`);
    console.log('OTPs received:', candOtps);

    console.log(`Entering email OTP: ${candOtps.email_code}`);
    await page.type('#emailCode', candOtps.email_code);
    await page.click('button[type="submit"]');
    await new Promise(r => setTimeout(r, 1500));

    console.log(`Entering phone OTP: ${candOtps.phone_code}`);
    await page.type('#phoneCode', candOtps.phone_code);
    
    // Click verify phone and activate
    await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const verifyPhoneButton = buttons.find(b => b.textContent.includes('Verify & Activate Profile'));
      if (verifyPhoneButton) verifyPhoneButton.click();
    });

    console.log('Waiting for Candidate Dashboard redirect...');
    await new Promise(r => setTimeout(r, 6000));

    // ==========================================
    // 4. CANDIDATE DASHBOARD
    // ==========================================
    console.log('\n--- Capturing Candidate Dashboard ---');
    await page.screenshot({ path: path.join(OUTPUT_DIR, 'candidate_dashboard.png') });
    console.log('Captured candidate_dashboard.png');

    // ==========================================
    // 5. RECRUITER LOGIN PAGE
    // ==========================================
    console.log('\n--- Capturing Recruiter Login ---');
    await logout();
    await page.goto(`${BASE_URL}/recruiter/login`, { waitUntil: 'networkidle2' });
    await new Promise(r => setTimeout(r, 1500));
    await page.screenshot({ path: path.join(OUTPUT_DIR, 'recruiter_login.png') });
    console.log('Captured recruiter_login.png');

    // ==========================================
    // 6. GOOGLE RECRUITER REGISTRATION (FOR SETUP WIZARD)
    // ==========================================
    console.log('\n--- Simulating Google Recruiter Sign In for Setup Wizard ---');
    const recEmail = `recruiter_google_${Date.now()}@acme.com`;
    const subId = `sub_rec_${Date.now()}`;
    
    // Trigger Google Auth callback in browser context to bypass company_id
    await page.evaluate(async (email, sub) => {
      try {
        const response = await fetch('/api/v1/auth/google', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            credential: `mock-google-token-${email}:${sub}:hd-none`,
            role: 'recruiter'
          })
        });
        const data = await response.json();
        
        // Save token to localStorage and redirect to setup-company
        if (data.access_token) {
          localStorage.setItem('smartonboard_token', data.access_token);
          window.location.href = '/recruiter/setup-company';
        }
      } catch (e) {
        console.error('Google Auth simulation failed:', e);
      }
    }, recEmail, subId);

    console.log('Waiting for Company Setup Wizard page...');
    await new Promise(r => setTimeout(r, 3000));
    console.log('Current URL:', page.url());

    // ==========================================
    // 7. RECRUITER SETUP COMPANY PAGE
    // ==========================================
    console.log('\n--- Capturing Recruiter Setup Company ---');
    await page.screenshot({ path: path.join(OUTPUT_DIR, 'recruiter_setup_company.png') });
    console.log('Captured recruiter_setup_company.png');

    // Complete the company setup wizard
    console.log('Filling in Company Setup Wizard...');
    await page.type('#company-name', 'Acme Systems Corp');
    await page.type('#company-website', 'https://acmesystems.com');
    await page.type('#company-industry', 'Information Technology');
    
    console.log('Submitting Company Setup Wizard...');
    await Promise.all([
      page.click('button[type="submit"]'),
      page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 })
    ]);
    await new Promise(r => setTimeout(r, 3000)); // wait for dashboard to load

    // ==========================================
    // 8. RECRUITER DASHBOARD
    // ==========================================
    console.log('\n--- Capturing Recruiter Dashboard ---');
    await page.screenshot({ path: path.join(OUTPUT_DIR, 'recruiter_dashboard.png') });
    console.log('Captured recruiter_dashboard.png');

    // ==========================================
    // 9. RECRUITER PIPELINE BOARD
    // ==========================================
    console.log('\n--- Capturing Recruiter Pipeline Board ---');
    await page.goto(`${BASE_URL}/recruiter/pipeline`, { waitUntil: 'networkidle2' });
    await new Promise(r => setTimeout(r, 2500));
    await page.screenshot({ path: path.join(OUTPUT_DIR, 'pipeline_board.png') });
    console.log('Captured pipeline_board.png');

    console.log('\nALL DAYLIGHT RESET SCREENSHOTS CAPTURED SUCCESSFULLY!');
  } catch (err) {
    console.error('Error during capture:', err);
  } finally {
    await page.close();
    await browser.disconnect();
  }
}

run().catch(console.error);
