const fs = require('fs');
const path = require('path');

const timestamp = Date.now();
const RECRUITER_EMAIL = `rec_google_${timestamp}@oryzo.ai`;
const MOCK_CREDENTIAL = `mock-google-token-${RECRUITER_EMAIL}:sub-rec-${timestamp}:None`;

async function getRecruiterToken() {
  try {
    const res = await fetch('http://localhost:5001/api/v1/auth/google', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        credential: MOCK_CREDENTIAL,
        role: 'recruiter'
      })
    });
    if (res.ok) {
      const data = await res.json();
      console.log('Recruiter Google Login successful, token acquired.');
      return data.access_token;
    } else {
      console.error('Failed to login recruiter via Google:', await res.text());
      return null;
    }
  } catch (err) {
    console.error('Error getting recruiter token:', err);
    return null;
  }
}

async function main() {
  const outputDir = path.join(__dirname, '..', 'docs', 'reports', 'ui-after');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  const recruiterToken = await getRecruiterToken();

  const pages = [
    { name: 'landing', url: 'http://localhost:5001/', token: null },
    { name: 'recruiter_login', url: 'http://localhost:5001/recruiter/login', token: null },
    { name: 'recruiter_register', url: 'http://localhost:5001/recruiter/register', token: null },
    { name: 'candidate_login', url: 'http://localhost:5001/candidate/login', token: null },
    { name: 'candidate_register', url: 'http://localhost:5001/candidate/register', token: null },
    { name: 'recruiter_setup_company', url: 'http://localhost:5001/recruiter/setup-company', token: recruiterToken }
  ];

  try {
    const res = await fetch('http://localhost:9222/json');
    const targets = await res.json();
    const pageTarget = targets.find(t => t.type === 'page');

    if (!pageTarget) {
      throw new Error('No active page target found on Brave browser. Ensure Brave is running.');
    }

    const wsUrl = pageTarget.webSocketDebuggerUrl;
    const ws = new WebSocket(wsUrl);

    await new Promise((resolve, reject) => {
      ws.onopen = resolve;
      ws.onerror = reject;
    });

    let msgId = 1;
    function sendCommand(method, params = {}) {
      return new Promise((resolve, reject) => {
        const id = msgId++;
        const onMessage = (event) => {
          const msg = JSON.parse(event.data);
          if (msg.id === id) {
            ws.removeEventListener('message', onMessage);
            if (msg.error) reject(msg.error);
            else resolve(msg.result);
          }
        };
        ws.addEventListener('message', onMessage);
        ws.send(JSON.stringify({ id, method, params }));
      });
    }

    await sendCommand('Page.enable');
    await sendCommand('Runtime.enable');

    for (const page of pages) {
      console.log(`Processing screenshot for page: ${page.name} ...`);

      // 1. Navigate to target url
      await sendCommand('Page.navigate', { url: page.url });
      await new Promise(r => setTimeout(r, 1000));

      // 2. Inject or clear token
      if (page.token) {
        await sendCommand('Runtime.evaluate', {
          expression: `localStorage.setItem('smartonboard_token', '${page.token}');`
        });
      } else {
        await sendCommand('Runtime.evaluate', {
          expression: `localStorage.removeItem('smartonboard_token');`
        });
      }

      // 3. Reload to load authenticated or unauthenticated state
      await sendCommand('Page.navigate', { url: page.url });
      
      // Wait for rendering
      await new Promise(r => setTimeout(r, 4500));

      // 4. Capture screenshot
      const result = await sendCommand('Page.captureScreenshot', { format: 'png' });
      const buffer = Buffer.from(result.data, 'base64');
      const filename = path.join(outputDir, `${page.name}.png`);
      fs.writeFileSync(filename, buffer);
      console.log(`Saved ${page.name}.png`);
    }

    ws.close();
    console.log('Finished capturing all UI screenshots successfully.');
  } catch (err) {
    console.error('Error during execution:', err);
  }
}

main();
