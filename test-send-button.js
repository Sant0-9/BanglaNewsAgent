// Simple test to check send button functionality
const { chromium } = require('playwright');

async function testSendButton() {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  console.log('Navigating to localhost:3001...');
  await page.goto('http://localhost:3001', { waitUntil: 'networkidle' });
  
  // Check initial button state
  console.log('Checking initial send button state...');
  const sendButton = page.locator('button:has-text("Send")');
  const initialDisabled = await sendButton.isDisabled();
  console.log(`Send button initially disabled: ${initialDisabled}`);
  
  // Type some text
  console.log('Typing text into textarea...');
  const textarea = page.locator('textarea');
  await textarea.fill('Test message');
  
  // Check if button is enabled after typing
  await page.waitForTimeout(100); // Small delay for state update
  const afterTypingDisabled = await sendButton.isDisabled();
  console.log(`Send button disabled after typing: ${afterTypingDisabled}`);
  
  // Try clicking the send button
  if (!afterTypingDisabled) {
    console.log('Attempting to click send button...');
    await sendButton.click();
    
    // Wait for any response
    await page.waitForTimeout(2000);
    
    // Check if there are any messages displayed
    const messages = page.locator('[class*="space-y-4"] > div');
    const messageCount = await messages.count();
    console.log(`Messages found after clicking send: ${messageCount}`);
    
    if (messageCount > 0) {
      const messageText = await messages.first().textContent();
      console.log(`First message content: "${messageText?.substring(0, 100)}..."`);
    }
  } else {
    console.log('Button is still disabled after typing - this indicates an issue!');
  }
  
  await browser.close();
}

testSendButton().catch(console.error);