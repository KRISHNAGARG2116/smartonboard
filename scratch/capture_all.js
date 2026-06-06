const fs = require('fs');
const path = require('path');

const RECRUITER_EMAIL = 'recruiter_visual@oryzo.ai';
const CANDIDATE_EMAIL = 'candidate_visual@oryzo.ai';
const PASSWORD = 'super-secure-password-123';

async function getTokens() {
  const tokens = { recruiter: null, candidate: null };

  // Recruiter Login/Register
  try {
    const res = await fetch('http://localhost:5001/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: RECRUITER_EMAIL, password: PASSWORD })
    });
    if (res.ok) {
      const data = await res.json();
      tokens.recruiter = data.access_token;
      console.log('Recruiter logged in successfully.');
    } else {
      // Try registering
      const reg = await fetch('http://localhost:5001/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_name: 'Oryzo AI Recruiter Corp',
          email: RECRUITER_EMAIL,
          password: PASSWORD,
          full_name: 'Oryzo Recruiter'
        })
      });
      if (reg.ok) {
        const data = await reg.json();
        tokens.recruiter = data.access_token;
        console.log('Recruiter registered successfully.');
      } else {
        console.error('Failed to log in or register recruiter:', await reg.text());
      }
    }
  } catch (err) {
    console.error('Recruiter auth error:', err);
  }

  // Candidate Login/Register
  try {
    const res = await fetch('http://localhost:5001/api/v1/auth/login/candidate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: CANDIDATE_EMAIL, password: PASSWORD })
    });
    if (res.ok) {
      const data = await res.json();
      tokens.candidate = data.access_token;
      console.log('Candidate logged in successfully.');
    } else {
      // Try registering
      const reg = await fetch('http://localhost:5001/api/v1/auth/register/candidate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: CANDIDATE_EMAIL,
          password: PASSWORD,
          full_name: 'Oryzo Candidate'
        })
      });
      if (reg.ok) {
        const data = await reg.json();
        tokens.candidate = data.access_token;
        console.log('Candidate registered successfully.');
      } else {
        console.error('Failed to log in or register candidate:', await reg.text());
      }
    }
  } catch (err) {
    console.error('Candidate auth error:', err);
  }

  return tokens;
}

async function main() {
  const mode = process.argv[2]; // 'before' or 'after'
  if (mode !== 'before' && mode !== 'after') {
    console.error('Usage: node capture_all.js <before|after>');
    process.exit(1);
  }

  const outputDir = path.join(__dirname, '..', 'docs', 'reports', `ui-${mode}`);
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  const tokens = await getTokens();

  const pages = [
    { name: 'landing', url: 'http://localhost:5001/', auth: null },
    { name: 'login', url: mode === 'before' ? 'http://localhost:5001/login' : 'http://localhost:5001/recruiter/login', auth: null },
    { name: 'register', url: mode === 'before' ? 'http://localhost:5001/register' : 'http://localhost:5001/recruiter/register', auth: null },
    { name: 'recruiter-dashboard', url: mode === 'before' ? 'http://localhost:5001/dashboard' : 'http://localhost:5001/recruiter/dashboard', auth: 'recruiter' },
    { name: 'candidate-dashboard', url: 'http://localhost:5001/candidate/dashboard', auth: 'candidate' },
    { name: 'candidate-directory', url: mode === 'before' ? 'http://localhost:5001/candidates' : 'http://localhost:5001/recruiter/candidates', auth: 'recruiter' },
    { name: 'pipeline-board', url: mode === 'before' ? 'http://localhost:5001/pipeline' : 'http://localhost:5001/recruiter/pipeline', auth: 'recruiter' },
    { name: 'resume-library', url: 'http://localhost:5001/candidate/resumes', auth: 'candidate' },
    { name: 'job-feed', url: 'http://localhost:5001/candidate/jobs', auth: 'candidate' },
    { name: 'candidate-applications', url: 'http://localhost:5001/candidate/applications', auth: 'candidate' },
    { name: 'candidate-interviews', url: 'http://localhost:5001/candidate/interviews', auth: 'candidate' },
    { name: 'candidate-profile', url: 'http://localhost:5001/candidate/profile', auth: 'candidate' },
  ];

  try {
    const res = await fetch('http://localhost:9222/json');
    const targets = await res.json();
    const pageTarget = targets.find(t => t.type === 'page');

    if (!pageTarget) {
      throw new Error('No active page target found. Ensure Brave is running.');
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
      console.log(`Processing: ${page.name} ...`);

      // 1. Go to target page
      await sendCommand('Page.navigate', { url: page.url });
      await new Promise(r => setTimeout(r, 1000));

      // 2. Set token in localStorage
      const tokenToSet = page.auth ? tokens[page.auth] : null;
      if (tokenToSet) {
        await sendCommand('Runtime.evaluate', {
          expression: `localStorage.setItem('smartonboard_token', '${tokenToSet}');`
        });
      } else {
        await sendCommand('Runtime.evaluate', {
          expression: `localStorage.removeItem('smartonboard_token');`
        });
      }

      // 3. Reload page to apply changes
      await sendCommand('Page.navigate', { url: page.url });
      
      // Wait for page to fully render
      await new Promise(r => setTimeout(r, 4500));

      // 4. Capture screenshot
      const result = await sendCommand('Page.captureScreenshot', { format: 'png' });
      const buffer = Buffer.from(result.data, 'base64');
      const filename = path.join(outputDir, `${page.name}.png`);
      fs.writeFileSync(filename, buffer);
      console.log(`Saved screenshot to: ${filename}`);
    }

    ws.close();
    console.log(`All screenshots for '${mode}' captured successfully.`);
  } catch (error) {
    console.error('Error during batch capture:', error);
  }
}

main();
