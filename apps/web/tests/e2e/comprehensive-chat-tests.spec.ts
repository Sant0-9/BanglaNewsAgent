import { test, expect } from '@playwright/test';

test.describe('Comprehensive Chat Functionality Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should send message and handle streaming API response', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    // Mock the streaming API response
    await page.route('http://localhost:8000/ask/stream', async route => {
      const response = `data: {"type":"token","delta":"This is "}\n\ndata: {"type":"token","delta":"a test "}\n\ndata: {"type":"token","delta":"response from the API"}\n\ndata: {"type":"complete","data":{"answer_bn":"This is a test response from the API","sources":[{"title":"Test Source","url":"https://example.com","snippet":"Test snippet"}],"flags":{"disagreement":false,"single_source":false},"metrics":{"source_count":1,"updated_ct":"2023-01-01T00:00:00.000Z"},"followups":["What else can you tell me?","How does this work?"]}}\n\ndata: [DONE]\n\n`;
      
      await route.fulfill({
        status: 200,
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
        },
        body: response,
      });
    });

    // Type and send message
    await textarea.fill('Tell me about something interesting');
    await sendButton.click();
    
    // Check that user message appears
    await expect(page.locator('text=Tell me about something interesting')).toBeVisible();
    
    // Input should be cleared
    await expect(textarea).toHaveValue('');
    
    // Should eventually show the complete response
    await expect(page.locator('text=This is a test response from the API')).toBeVisible({ timeout: 10000 });
  });

  test('should test Deep Dive action button', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    let callCount = 0;
    
    // Mock API responses
    await page.route('http://localhost:8000/ask/stream', async route => {
      callCount++;
      const request = route.request();
      const postData = request.postDataJSON();
      
      let response;
      if (postData.mode === 'deep') {
        response = `data: {"type":"complete","data":{"answer_bn":"Deep dive response about the topic","sources":[],"flags":{"disagreement":false,"single_source":false},"metrics":{"source_count":0,"updated_ct":"2023-01-01T00:00:00.000Z"}}}\n\ndata: [DONE]\n\n`;
      } else {
        response = `data: {"type":"complete","data":{"answer_bn":"Brief response","sources":[],"flags":{"disagreement":false,"single_source":false},"metrics":{"source_count":0,"updated_ct":"2023-01-01T00:00:00.000Z"}}}\n\ndata: [DONE]\n\n`;
      }
      
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: response,
      });
    });

    // Send initial message
    await textarea.fill('Tell me about AI');
    await sendButton.click();
    
    // Wait for response
    await expect(page.locator('text=Brief response')).toBeVisible();
    
    // Click Deep Dive button
    await page.getByRole('button', { name: 'Deep Dive' }).click();
    
    // Should send another request and get deep response
    await expect(page.locator('text=Deep dive response about the topic')).toBeVisible();
    
    expect(callCount).toBe(2);
  });

  test('should test Timeline action button', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    // Mock main API response
    await page.route('http://localhost:8000/ask/stream', async route => {
      const response = `data: {"type":"complete","data":{"answer_bn":"Timeline test response","sources":[],"flags":{"disagreement":false,"single_source":false},"metrics":{"source_count":0,"updated_ct":"2023-01-01T00:00:00.000Z"}}}\n\ndata: [DONE]\n\n`;
      
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: response,
      });
    });
    
    // Mock timeline API response
    await page.route('http://localhost:8000/timeline*', async route => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items: [
            {
              date: '2023-12-01',
              count: 3,
              titles: ['Event 1', 'Event 2', 'Event 3']
            },
            {
              date: '2023-12-02',
              count: 2,
              titles: ['Event 4', 'Event 5']
            }
          ]
        }),
      });
    });

    // Send message
    await textarea.fill('Timeline test query');
    await sendButton.click();
    
    // Wait for response
    await expect(page.locator('text=Timeline test response')).toBeVisible();
    
    // Click Timeline button
    await page.getByRole('button', { name: 'Timeline' }).click();
    
    // Should open timeline dialog
    await expect(page.locator('text=Timeline (7 days)')).toBeVisible();
    
    // Should show timeline items
    await expect(page.locator('text=2023-12-01')).toBeVisible();
    await expect(page.locator('text=3 items')).toBeVisible();
    await expect(page.locator('text=Event 1')).toBeVisible();
  });

  test('should test English action button', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    // Mock API response with English answer
    await page.route('http://localhost:8000/ask/stream', async route => {
      const response = `data: {"type":"complete","data":{"answer_bn":"বাংলা উত্তর এখানে","answer_en":"English answer here","sources":[],"flags":{"disagreement":false,"single_source":false},"metrics":{"source_count":0,"updated_ct":"2023-01-01T00:00:00.000Z"}}}\n\ndata: [DONE]\n\n`;
      
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: response,
      });
    });

    // Send message
    await textarea.fill('English test query');
    await sendButton.click();
    
    // Wait for Bangla response
    await expect(page.locator('text=বাংলা উত্তর এখানে')).toBeVisible();
    
    // Click English button
    await page.getByRole('button', { name: 'English' }).click();
    
    // Should open English dialog
    await expect(page.locator('text=English Answer')).toBeVisible();
    await expect(page.locator('text=English answer here')).toBeVisible();
  });

  test('should test language toggle functionality', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    const englishButton = page.getByRole('button', { name: 'English' });
    
    let apiCalls = [];
    
    // Intercept API calls to check language parameter
    await page.route('http://localhost:8000/ask/stream', async route => {
      const request = route.request();
      const postData = request.postDataJSON();
      apiCalls.push(postData);
      
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: 'data: [DONE]\n\n',
      });
    });

    // Default should be Bangla
    await textarea.fill('Test message');
    await sendButton.click();
    await page.waitForTimeout(500);
    
    // Switch to English
    await englishButton.click();
    await textarea.fill('English message');
    await sendButton.click();
    await page.waitForTimeout(500);
    
    // Check that API was called with correct language parameters
    expect(apiCalls).toHaveLength(2);
    expect(apiCalls[0].lang).toBe('bn');
    expect(apiCalls[1].lang).toBe('en');
  });

  test('should test mode toggle functionality', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    const deepButton = page.getByRole('button', { name: 'Deep' });
    
    let apiCalls = [];
    
    // Intercept API calls to check mode parameter
    await page.route('http://localhost:8000/ask/stream', async route => {
      const request = route.request();
      const postData = request.postDataJSON();
      apiCalls.push(postData);
      
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: 'data: [DONE]\n\n',
      });
    });

    // Default should be Brief
    await textarea.fill('Test message');
    await sendButton.click();
    await page.waitForTimeout(500);
    
    // Switch to Deep
    await deepButton.click();
    await textarea.fill('Deep message');
    await sendButton.click();
    await page.waitForTimeout(500);
    
    // Check that API was called with correct mode parameters
    expect(apiCalls).toHaveLength(2);
    expect(apiCalls[0].mode).toBe('brief');
    expect(apiCalls[1].mode).toBe('deep');
  });

  test('should handle request cancellation with Cancel button', async ({ page }) => {
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

    await textarea.fill('Slow request test');
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

  test('should handle API errors gracefully', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    // Mock API error
    await page.route('http://localhost:8000/ask/stream', async route => {
      await route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Server error occurred' }),
      });
    });

    await textarea.fill('Test error handling');
    await sendButton.click();
    
    // Should show error message
    await expect(page.locator('text=Server error occurred')).toBeVisible({ timeout: 10000 });
  });

  test('should verify API endpoints and request format', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    let requestDetails = {};
    
    // Intercept API calls to verify the correct endpoint is called
    await page.route('http://localhost:8000/ask/stream', async route => {
      const request = route.request();
      requestDetails = {
        url: request.url(),
        method: request.method(),
        headers: request.headers(),
        body: request.postDataJSON(),
      };
      
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: 'data: [DONE]\n\n',
      });
    });

    await textarea.fill('Test API endpoint verification');
    await sendButton.click();
    
    // Wait for request to complete
    await page.waitForTimeout(500);
    
    // Verify the correct endpoint was called with proper format
    expect(requestDetails.url).toBe('http://localhost:8000/ask/stream');
    expect(requestDetails.method).toBe('POST');
    expect(requestDetails.headers['content-type']).toBe('application/json');
    expect(requestDetails.headers['accept']).toBe('text/event-stream');
    expect(requestDetails.body).toEqual({
      query: 'Test API endpoint verification',
      lang: 'bn',
      mode: 'brief'
    });
  });

  test('should handle console errors', async ({ page }) => {
    const consoleLogs = [];
    const consoleErrors = [];
    
    // Listen for console messages
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      } else {
        consoleLogs.push(msg.text());
      }
    });

    // Navigate and interact with the page
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    // Mock API response
    await page.route('http://localhost:8000/ask/stream', async route => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: 'data: [DONE]\n\n',
      });
    });

    await textarea.fill('Console error test');
    await sendButton.click();
    
    // Wait for interactions to complete
    await page.waitForTimeout(2000);
    
    // Check for unexpected console errors
    const criticalErrors = consoleErrors.filter(error => 
      !error.includes('favicon') && // Ignore favicon errors
      !error.includes('DevTools') && // Ignore DevTools warnings
      !error.includes('extension') // Ignore extension-related errors
    );
    
    expect(criticalErrors).toEqual([]);
  });
});