const fs = require('fs');
const path = require('path');

async function main() {
  const urlArg = process.argv[2];
  const outputPath = process.argv[3];

  if (!urlArg || !outputPath) {
    console.error('Usage: node take_screenshot.js <url> <output_path>');
    process.exit(1);
  }

  try {
    // 1. Get targets list from local browser
    const res = await fetch('http://localhost:9222/json');
    const targets = await res.json();
    const pageTarget = targets.find(t => t.type === 'page');

    if (!pageTarget) {
      throw new Error('No active browser page target found.');
    }

    const wsUrl = pageTarget.webSocketDebuggerUrl;
    console.log(`Connecting to page target: ${wsUrl}`);

    // 2. Connect via WebSocket
    const ws = new WebSocket(wsUrl);

    await new Promise((resolve, reject) => {
      ws.onopen = resolve;
      ws.onerror = reject;
    });

    console.log('Connected. Navigating to:', urlArg);

    // Helper to send CDP command
    let msgId = 1;
    function sendCommand(method, params = {}) {
      return new Promise((resolve, reject) => {
        const id = msgId++;
        const onMessage = (event) => {
          const msg = JSON.parse(event.data);
          if (msg.id === id) {
            ws.removeEventListener('message', onMessage);
            if (msg.error) {
              reject(msg.error);
            } else {
              resolve(msg.result);
            }
          }
        };
        ws.addEventListener('message', onMessage);
        ws.send(JSON.stringify({ id, method, params }));
      });
    }

    // Enable Page domain
    await sendCommand('Page.enable');

    // Navigate to page
    await sendCommand('Page.navigate', { url: urlArg });

    // Wait 4 seconds for page to load and render
    console.log('Waiting for render...');
    await new Promise(r => setTimeout(r, 4000));

    // Capture screenshot
    console.log('Capturing screenshot...');
    const result = await sendCommand('Page.captureScreenshot', { format: 'png' });
    const buffer = Buffer.from(result.data, 'base64');

    // Ensure output directory exists
    const dir = path.dirname(outputPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    fs.writeFileSync(outputPath, buffer);
    console.log(`Screenshot saved successfully to: ${outputPath}`);

    ws.close();
  } catch (error) {
    console.error('Screenshot capture failed:', error);
    process.exit(1);
  }
}

main();
