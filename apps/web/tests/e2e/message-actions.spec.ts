import { test, expect } from '@playwright/test';

test.describe('Message Actions', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should show action buttons on assistant messages', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    // Mock API response with a complete message
    await page.route('http://localhost:8000/ask/stream', async route => {
      const response = `data: {"type":"complete","data":{"answer_bn":"This is a test response","sources":[{"title":"Test Source","url":"https://example.com","snippet":"Test snippet"}],"flags":{"disagreement":false,"single_source":false},"metrics":{"source_count":1,"updated_ct":"2023-01-01T00:00:00.000Z"},"followups":["Follow up 1","Follow up 2"]}}\n\ndata: [DONE]\n\n`;
      
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: response,
      });
    });

    // Send a message
    await textarea.fill('Test message for actions');
    await sendButton.click();
    
    // Wait for the response to complete
    await expect(page.locator('text=This is a test response')).toBeVisible({ timeout: 10000 });
    
    // Check for action buttons
    await expect(page.getByRole('button', { name: 'Deep Dive' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Timeline' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'English' })).toBeVisible();
    
    // Check for followup buttons
    await expect(page.locator('button:has-text("Follow up 1")')).toBeVisible();
    await expect(page.locator('button:has-text("Follow up 2")')).toBeVisible();
  });

  test('should not show action buttons while streaming', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    // Mock a slow streaming response
    let resolveRoute;
    const routePromise = new Promise(resolve => { resolveRoute = resolve; });
    
    await page.route('http://localhost:8000/ask/stream', async route => {
      // Send initial token but don't complete immediately
      const response = `data: {"type":"token","delta":"Streaming "}\n\n`;
      
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: response,
      });
      
      resolveRoute();
    });

    await textarea.fill('Test streaming');
    await sendButton.click();
    
    // Wait for streaming to start
    await routePromise;
    await expect(page.locator('text=Streaming...')).toBeVisible();
    
    // Action buttons should not be visible while streaming
    await expect(page.getByRole('button', { name: 'Deep Dive' })).not.toBeVisible();
    await expect(page.getByRole('button', { name: 'Timeline' })).not.toBeVisible();
    await expect(page.getByRole('button', { name: 'English' })).not.toBeVisible();
  });

  test('should handle Deep Dive action', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    let apiCallCount = 0;
    
    // Mock API responses
    await page.route('http://localhost:8000/ask/stream', async route => {
      apiCallCount++;
      const request = route.request();
      const postData = request.postDataJSON();
      
      const response = `data: {"type":"complete","data":{"answer_bn":"Response ${apiCallCount}","sources":[],"flags":{"disagreement":false,"single_source":false},"metrics":{"source_count":0,"updated_ct":"2023-01-01T00:00:00.000Z"}}}\n\ndata: [DONE]\n\n`;
      
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: response,
      });
    });

    // Send initial message
    await textarea.fill('Test deep dive');
    await sendButton.click();
    
    // Wait for response
    await expect(page.locator('text=Response 1')).toBeVisible();
    
    // Click Deep Dive button
    await page.getByRole('button', { name: 'Deep Dive' }).click();
    
    // Should send another request in deep mode
    await expect(page.locator('text=Response 2')).toBeVisible();
    
    // Verify that two API calls were made
    expect(apiCallCount).toBe(2);
  });

  test('should handle Timeline action', async ({ page }) => {
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
    await textarea.fill('Timeline test');
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

  test('should handle Timeline action with error (Coming soon toast)', async ({ page }) => {
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
    
    // Mock timeline API error
    await page.route('http://localhost:8000/timeline*', async route => {
      await route.fulfill({
        status: 404,
        body: 'Not found',
      });
    });

    // Send message
    await textarea.fill('Timeline error test');
    await sendButton.click();
    
    // Wait for response
    await expect(page.locator('text=Timeline test response')).toBeVisible();
    
    // Click Timeline button
    await page.getByRole('button', { name: 'Timeline' }).click();
    
    // Should show "Coming soon" toast
    await expect(page.locator('text=Coming soon')).toBeVisible({ timeout: 5000 });
  });

  test('should handle English action with existing answer_en', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    // Mock API response with English answer
    await page.route('http://localhost:8000/ask/stream', async route => {
      const response = `data: {"type":"complete","data":{"answer_bn":"বাংলা উত্তর","answer_en":"English answer","sources":[],"flags":{"disagreement":false,"single_source":false},"metrics":{"source_count":0,"updated_ct":"2023-01-01T00:00:00.000Z"}}}\n\ndata: [DONE]\n\n`;
      
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: response,
      });
    });

    // Send message
    await textarea.fill('English test');
    await sendButton.click();
    
    // Wait for response
    await expect(page.locator('text=বাংলা উত্তর')).toBeVisible();
    
    // Click English button
    await page.getByRole('button', { name: 'English' }).click();
    
    // Should open English dialog with existing answer
    await expect(page.locator('text=English Answer')).toBeVisible();
    await expect(page.locator('text=English answer')).toBeVisible();
  });

  test('should handle English action without existing answer_en', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    let apiCallCount = 0;
    
    // Mock API responses
    await page.route('http://localhost:8000/ask/stream', async route => {
      apiCallCount++;
      const request = route.request();
      const postData = request.postDataJSON();
      
      let response;
      if (postData.lang === 'bn') {
        response = `data: {"type":"complete","data":{"answer_bn":"বাংলা উত্তর","sources":[],"flags":{"disagreement":false,"single_source":false},"metrics":{"source_count":0,"updated_ct":"2023-01-01T00:00:00.000Z"}}}\n\ndata: [DONE]\n\n`;
      } else {
        response = `data: {"type":"complete","data":{"answer_bn":"English response","sources":[],"flags":{"disagreement":false,"single_source":false},"metrics":{"source_count":0,"updated_ct":"2023-01-01T00:00:00.000Z"}}}\n\ndata: [DONE]\n\n`;
      }
      
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: response,
      });
    });

    // Send message
    await textarea.fill('English without existing test');
    await sendButton.click();
    
    // Wait for response
    await expect(page.locator('text=বাংলা উত্তর')).toBeVisible();
    
    // Click English button
    await page.getByRole('button', { name: 'English' }).click();
    
    // Should create a new message in English
    await expect(page.locator('text=English without existing test (English)')).toBeVisible();
    await expect(page.locator('text=English response')).toBeVisible();
    
    expect(apiCallCount).toBe(2);
  });

  test('should handle followup questions', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    let apiCallCount = 0;
    
    // Mock API responses
    await page.route('http://localhost:8000/ask/stream', async route => {
      apiCallCount++;
      const request = route.request();
      const postData = request.postDataJSON();
      
      let response;
      if (apiCallCount === 1) {
        response = `data: {"type":"complete","data":{"answer_bn":"Original response","sources":[],"flags":{"disagreement":false,"single_source":false},"metrics":{"source_count":0,"updated_ct":"2023-01-01T00:00:00.000Z"},"followups":["Follow up question 1","Follow up question 2"]}}\n\ndata: [DONE]\n\n`;
      } else {
        response = `data: {"type":"complete","data":{"answer_bn":"Followup response","sources":[],"flags":{"disagreement":false,"single_source":false},"metrics":{"source_count":0,"updated_ct":"2023-01-01T00:00:00.000Z"}}}\n\ndata: [DONE]\n\n`;
      }
      
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: response,
      });
    });

    // Send initial message
    await textarea.fill('Original question');
    await sendButton.click();
    
    // Wait for response with followups
    await expect(page.locator('text=Original response')).toBeVisible();
    await expect(page.locator('button:has-text("Follow up question 1")')).toBeVisible();
    
    // Click on followup
    await page.locator('button:has-text("Follow up question 1")').click();
    
    // Should send the followup question
    await expect(page.locator('text=Follow up question 1')).toBeVisible();
    await expect(page.locator('text=Followup response')).toBeVisible();
    
    expect(apiCallCount).toBe(2);
  });

  test('should handle sources toggle', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    // Mock API response with sources
    await page.route('http://localhost:8000/ask/stream', async route => {
      const response = `data: {"type":"complete","data":{"answer_bn":"Response with sources","sources":[{"title":"Source 1","url":"https://example1.com","snippet":"Snippet 1"},{"title":"Source 2","url":"https://example2.com","snippet":"Snippet 2"}],"flags":{"disagreement":false,"single_source":false},"metrics":{"source_count":2,"updated_ct":"2023-01-01T00:00:00.000Z"}}}\n\ndata: [DONE]\n\n`;
      
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: response,
      });
    });

    // Send message
    await textarea.fill('Sources test');
    await sendButton.click();
    
    // Wait for response
    await expect(page.locator('text=Response with sources')).toBeVisible();
    
    // Sources should be visible by default
    await expect(page.locator('text=Sources')).toBeVisible();
    await expect(page.locator('text=Source 1')).toBeVisible();
    await expect(page.locator('text=Source 2')).toBeVisible();
    
    // Click Hide button
    await page.locator('button:has-text("Hide")').click();
    
    // Sources should be hidden
    await expect(page.locator('text=Source 1')).not.toBeVisible();
    await expect(page.locator('text=Source 2')).not.toBeVisible();
    
    // Click Show button
    await page.locator('button:has-text("Show")').click();
    
    // Sources should be visible again
    await expect(page.locator('text=Source 1')).toBeVisible();
    await expect(page.locator('text=Source 2')).toBeVisible();
  });
});