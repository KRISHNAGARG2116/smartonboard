const fs = require('fs');
const path = require('path');

const filePath = '/Users/krishnagarg/.gemini/antigravity/brain/8bcf48ae-851c-42f2-99c1-290ecb6de981/.system_generated/steps/3995/content.md';
if (!fs.existsSync(filePath)) {
  console.error("Content file not found");
  process.exit(1);
}

const html = fs.readFileSync(filePath, 'utf8');

// Try to find __NEXT_DATA__
const nextDataMatch = html.match(/<script id="__NEXT_DATA__" type="application\/json">([\s\S]*?)<\/script>/);
if (nextDataMatch) {
  console.log("Found __NEXT_DATA__!");
  try {
    const json = JSON.parse(nextDataMatch[1]);
    fs.writeFileSync(path.join(__dirname, 'next_data.json'), JSON.stringify(json, null, 2));
    console.log("Saved __NEXT_DATA__ to next_data.json");
  } catch (e) {
    console.error("Failed to parse __NEXT_DATA__:", e.message);
  }
} else {
  console.log("No __NEXT_DATA__ found");
}

// Try to find any other large JSON objects or script contents
const selfNextFMatch = html.match(/self\.__next_f\.push\(\[1,"([\s\S]*?)"\]\)/g);
if (selfNextFMatch) {
  console.log(`Found self.__next_f.push matches: ${selfNextFMatch.length}`);
  // Let's extract all the text strings from self.__next_f
  let allStrings = [];
  html.replace(/self\.__next_f\.push\(\[1,"([\s\S]*?)"\]\)/g, (match, p1) => {
    // Unescape unicode and escape sequences
    try {
      const decoded = JSON.parse(`"${p1}"`);
      allStrings.push(decoded);
    } catch (e) {
      allStrings.push(p1);
    }
    return match;
  });
  fs.writeFileSync(path.join(__dirname, 'next_f_strings.txt'), allStrings.join('\n'));
  console.log("Saved self.__next_f.push strings to next_f_strings.txt");
}
