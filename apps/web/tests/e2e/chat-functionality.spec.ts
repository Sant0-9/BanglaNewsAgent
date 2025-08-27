import { test, expect } from '@playwright/test';

test.describe('Chat Functionality', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should send a message and handle API request', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    // Mock the API response to avoid actual network calls
    await page.route('http://localhost:8000/ask/stream', async route => {
      // Simulate a streaming response
      const response = `data: {"type":"token","delta":"Hello "}\n\ndata: {"type":"token","delta":"World!"}\n\ndata: {"type":"complete","data":{"answer_bn":"Hello World!","sources":[],"flags":{"disagreement":false,"single_source":false},"metrics":{"source_count":0,"updated_ct":"2023-01-01T00:00:00.000Z"}}}\n\ndata: [DONE]\n\n`;
      
      await route.fulfill({
        status: 200,
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
        },
        body: response,
      });
    });

    // Type a message and send
    await textarea.fill('What is the weather today?');
    await sendButton.click();
    
    // Check that the message appears in the chat
    await expect(page.locator('text=What is the weather today?')).toBeVisible();
    
    // Input should be cleared after sending
    await expect(textarea).toHaveValue('');
    
    // Should show streaming indicator initially
    await expect(page.locator('text=Streaming...')).toBeVisible({ timeout: 5000 });
    
    // Eventually should show the response
    await expect(page.locator('text=Hello World!')).toBeVisible({ timeout: 10000 });
  });

  test('should handle API error gracefully', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    // Mock API error
    await page.route('http://localhost:8000/ask/stream', async route => {
      await route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Server error' }),
      });
    });
    
    // Fallback to regular JSON endpoint
    await page.route('http://localhost:8000/ask', async route => {
      await route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Server error' }),
      });
    });

    await textarea.fill('Test error handling');
    await sendButton.click();
    
    // Should show error message
    await expect(page.locator('text=Server error')).toBeVisible({ timeout: 10000 });
  });

  test('should handle request cancellation', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    const cancelButton = page.getByRole('button', { name: /cancel/i });
    
    // Mock a slow API response
    await page.route('http://localhost:8000/ask/stream', async route => {
      // Delay the response
      await new Promise(resolve => setTimeout(resolve, 2000));
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: 'data: {"type":"token","delta":"Slow response"}\n\n',
      });
    });

    await textarea.fill('Slow request');
    await sendButton.click();
    
    // Cancel button should become enabled
    await expect(cancelButton).toBeEnabled({ timeout: 1000 });
    
    // Cancel the request
    await cancelButton.click();
    
    // Should show cancellation message
    await expect(page.locator('text=Request cancelled')).toBeVisible({ timeout: 5000 });
    
    // Cancel button should be disabled again
    await expect(cancelButton).toBeDisabled();
  });

  test('should prevent multiple simultaneous requests', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    // Mock a slow API response
    await page.route('http://localhost:8000/ask/stream', async route => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: 'data: [DONE]\n\n',
      });
    });

    // Send first request
    await textarea.fill('First request');
    await sendButton.click();
    
    // Send button should be disabled while request is pending
    await expect(sendButton).toBeDisabled();
    
    // Input should also be disabled
    await expect(textarea).toBeDisabled();
    
    // Wait for request to complete
    await expect(sendButton).toBeEnabled({ timeout: 3000 });
    await expect(textarea).toBeEnabled();
  });

  test('should handle Enter key to send message', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    
    // Mock API response
    await page.route('http://localhost:8000/ask/stream', async route => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: 'data: [DONE]\n\n',
      });
    });

    await textarea.fill('Test Enter key');
    await textarea.press('Enter');
    
    // Should send the message
    await expect(page.locator('text=Test Enter key')).toBeVisible();
  });

  test('should handle Shift+Enter for new line', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    
    await textarea.fill('Line 1');
    await textarea.press('Shift+Enter');
    await textarea.type('Line 2');
    
    // Should contain newline
    await expect(textarea).toHaveValue('Line 1\nLine 2');
  });

  test('should switch between languages', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    const englishButton = page.getByRole('button', { name: 'English' });
    
    let apiCallsMade = [];
    
    // Intercept API calls to check language parameter
    await page.route('http://localhost:8000/ask/stream', async route => {
      const request = route.request();
      const postData = request.postDataJSON();
      apiCallsMade.push(postData);
      
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: 'data: [DONE]\n\n',
      });
    });

    // Default should be Bangla
    await textarea.fill('Test message');
    await sendButton.click();
    
    // Wait a moment for the request
    await page.waitForTimeout(500);
    
    // Switch to English
    await englishButton.click();
    await textarea.fill('English message');
    await sendButton.click();
    
    // Wait a moment for the request
    await page.waitForTimeout(500);
    
    // Check that API was called with correct language parameters
    expect(apiCallsMade).toHaveLength(2);
    expect(apiCallsMade[0].lang).toBe('bn');
    expect(apiCallsMade[1].lang).toBe('en');
  });

  test('should switch between modes', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    const deepButton = page.getByRole('button', { name: 'Deep' });
    
    let apiCallsMade = [];
    
    // Intercept API calls to check mode parameter
    await page.route('http://localhost:8000/ask/stream', async route => {
      const request = route.request();
      const postData = request.postDataJSON();
      apiCallsMade.push(postData);
      
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: 'data: [DONE]\n\n',
      });
    });

    // Default should be Brief
    await textarea.fill('Test message');
    await sendButton.click();
    
    // Wait a moment for the request
    await page.waitForTimeout(500);
    
    // Switch to Deep
    await deepButton.click();
    await textarea.fill('Deep message');
    await sendButton.click();
    
    // Wait a moment for the request
    await page.waitForTimeout(500);
    
    // Check that API was called with correct mode parameters
    expect(apiCallsMade).toHaveLength(2);
    expect(apiCallsMade[0].mode).toBe('brief');
    expect(apiCallsMade[1].mode).toBe('deep');
  });
});