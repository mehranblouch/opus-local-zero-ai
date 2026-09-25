const fs = require('fs');
const path = require('path');

const stepFile = path.resolve('C:/Users/AYAT LAPTOP POINT/.gemini/antigravity/brain/187cb06c-3418-4799-a806-50ffe4a7cd7a/.system_generated/steps/141/content.md');
const targetFile = path.resolve(__dirname, 'skills/opusclip/scripts/opusclip');

try {
  if (fs.existsSync(stepFile)) {
    const content = fs.readFileSync(stepFile, 'utf8');
    const jsonStart = content.indexOf('{"sha":');
    if (jsonStart !== -1) {
      const jsonStr = content.substring(jsonStart).trim();
      const data = JSON.parse(jsonStr);
      const buf = Buffer.from(data.content, 'base64');
      fs.mkdirSync(path.dirname(targetFile), { recursive: true });
      fs.writeFileSync(targetFile, buf);
      console.log('Successfully written ' + buf.length + ' bytes to ' + targetFile);
    } else {
      console.error('Could not find json in step file');
    }
  } else {
    console.error('Step file not found: ' + stepFile);
  }
} catch (e) {
  console.error(e);
}
