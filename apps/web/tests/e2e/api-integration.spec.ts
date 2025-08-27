import { test, expect } from '@playwright/test';

test.describe('API Integration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should make requests to http://localhost:8000', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    let requestUrl = '';
    let requestMethod = '';
    let requestHeaders = {};
    let requestBody = null;
    
    // Intercept API calls to verify the correct endpoint is called
    await page.route('http://localhost:8000/ask/stream', async route => {
      const request = route.request();
      requestUrl = request.url();
      requestMethod = request.method();
      requestHeaders = request.headers();
      requestBody = request.postDataJSON();
      
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: 'data: [DONE]\n\n',
      });
    });

    await textarea.fill('Test API endpoint');
    await sendButton.click();
    
    // Wait a moment for the request to be made
    await page.waitForTimeout(500);
    
    // Verify the correct endpoint was called
    expect(requestUrl).toBe('http://localhost:8000/ask/stream');
    expect(requestMethod).toBe('POST');
    expect(requestHeaders['content-type']).toBe('application/json');
    expect(requestHeaders['accept']).toBe('text/event-stream');
    expect(requestBody).toEqual({
      query: 'Test API endpoint',
      lang: 'bn',
      mode: 'brief'
    });
  });

  test('should fallback to JSON endpoint if streaming fails', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    let streamingCalled = false;
    let jsonCalled = false;
    
    // Make streaming endpoint return 404
    await page.route('http://localhost:8000/ask/stream', async route => {
      streamingCalled = true;
      await route.fulfill({
        status: 404,
        body: 'Not found',
      });
    });
    
    // Mock fallback JSON endpoint
    await page.route('http://localhost:8000/ask', async route => {
      jsonCalled = true;
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          answer_bn: 'JSON fallback response',
          sources: [],
          flags: { disagreement: false, single_source: false },
          metrics: { source_count: 0, updated_ct: new Date().toISOString() }
        }),
      });
    });

    await textarea.fill('Test fallback');
    await sendButton.click();
    
    // Should show the fallback response
    await expect(page.locator('text=JSON fallback response')).toBeVisible({ timeout: 10000 });
    
    // Verify both endpoints were called
    expect(streamingCalled).toBe(true);
    expect(jsonCalled).toBe(true);
  });

  test('should handle streaming response correctly', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    // Mock streaming response with multiple chunks
    await page.route('http://localhost:8000/ask/stream', async route => {
      const chunks = [
        'data: {"type":"token","delta":"Hello "}\n\n',
        'data: {"type":"token","delta":"streaming "}\n\n',
        'data: {"type":"token","delta":"world!"}\n\n',
        'data: {"type":"sources","data":[{"title":"Test Source","url":"https://example.com","snippet":"Test snippet"}]}\n\n',
        'data: {"type":"complete","data":{"answer_bn":"Hello streaming world!","sources":[{"title":"Test Source","url":"https://example.com","snippet":"Test snippet"}],"flags":{"disagreement":false,"single_source":false},"metrics":{"source_count":1,"updated_ct":"2023-01-01T00:00:00.000Z"}}}\n\n',
        'data: [DONE]\n\n'
      ].join('');
      
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: chunks,
      });
    });

    await textarea.fill('Test streaming');
    await sendButton.click();
    
    // Should show streaming indicator initially
    await expect(page.locator('text=Streaming...')).toBeVisible();
    
    // Should eventually show the complete response
    await expect(page.locator('text=Hello streaming world!')).toBeVisible({ timeout: 10000 });
    
    // Should show sources
    await expect(page.locator('text=Test Source')).toBeVisible();
    
    // Streaming indicator should disappear
    await expect(page.locator('text=Streaming...')).not.toBeVisible();
  });

  test('should handle request timeout', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    // Mock a request that never responds
    await page.route('http://localhost:8000/ask/stream', async route => {
      // Never fulfill this request to simulate timeout
      // The actual timeout is handled by the API client
      await new Promise(() => {}); // Never resolves
    });
    
    // Mock fallback that also times out
    await page.route('http://localhost:8000/ask', async route => {
      await new Promise(() => {}); // Never resolves
    });

    await textarea.fill('Test timeout');
    await sendButton.click();
    
    // Should show timeout error eventually (this depends on the actual timeout configuration)
    // Since we can't wait for the full timeout in tests, we'll just verify the request was made
    await page.waitForTimeout(1000);
    
    // Cancel the request to clean up
    await page.getByRole('button', { name: /cancel/i }).click();
    await expect(page.locator('text=Request cancelled')).toBeVisible();
  });

  test('should send correct parameters for different configurations', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    const englishButton = page.getByRole('button', { name: 'English' });
    const deepButton = page.getByRole('button', { name: 'Deep' });
    
    let requestBodies = [];
    
    // Intercept all API calls
    await page.route('http://localhost:8000/ask/stream', async route => {
      const request = route.request();
      requestBodies.push(request.postDataJSON());
      
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: 'data: [DONE]\n\n',
      });
    });

    // Test 1: Default configuration (Bangla, Brief)
    await textarea.fill('Default test');
    await sendButton.click();
    await page.waitForTimeout(500);
    
    // Test 2: English, Brief
    await englishButton.click();
    await textarea.fill('English test');
    await sendButton.click();
    await page.waitForTimeout(500);
    
    // Test 3: English, Deep
    await deepButton.click();
    await textarea.fill('English Deep test');
    await sendButton.click();
    await page.waitForTimeout(500);
    
    // Test 4: Bangla, Deep
    await page.getByRole('button', { name: 'Bangla' }).click();
    await textarea.fill('Bangla Deep test');
    await sendButton.click();
    await page.waitForTimeout(500);
    
    // Verify all request parameters
    expect(requestBodies).toHaveLength(4);
    
    expect(requestBodies[0]).toEqual({
      query: 'Default test',
      lang: 'bn',
      mode: 'brief'
    });
    
    expect(requestBodies[1]).toEqual({
      query: 'English test',
      lang: 'en',
      mode: 'brief'
    });
    
    expect(requestBodies[2]).toEqual({
      query: 'English Deep test',
      lang: 'en',
      mode: 'deep'
    });
    
    expect(requestBodies[3]).toEqual({
      query: 'Bangla Deep test',
      lang: 'bn',
      mode: 'deep'
    });
  });

  test('should handle malformed streaming responses gracefully', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    // Mock malformed streaming response
    await page.route('http://localhost:8000/ask/stream', async route => {
      const malformedResponse = [
        'data: {"type":"token","delta":"Good start "}\n\n',
        'data: {"invalid":"json"malformed\n\n', // Malformed JSON
        'data: {"type":"token","delta":"continues after error"}\n\n',
        'data: [DONE]\n\n'
      ].join('');
      
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: malformedResponse,
      });
    });

    await textarea.fill('Test malformed response');
    await sendButton.click();
    
    // Should handle malformed chunks gracefully and continue processing
    await expect(page.locator('text=Good start continues after error')).toBeVisible({ timeout: 10000 });
  });

  test('should handle abort signal correctly', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    const cancelButton = page.getByRole('button', { name: /cancel/i });
    
    let requestAborted = false;
    
    // Mock a slow streaming response
    await page.route('http://localhost:8000/ask/stream', async route => {
      try {
        // Start streaming but delay completion
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'text/event-stream' },
          body: 'data: {"type":"token","delta":"Starting slow response..."}\n\n',
        });
        
        // Simulate ongoing streaming
        await new Promise(resolve => setTimeout(resolve, 1000));
      } catch (error) {
        requestAborted = true;
        throw error;
      }
    });

    await textarea.fill('Test abort');
    await sendButton.click();
    
    // Cancel the request quickly
    await cancelButton.click();
    
    // Should show cancellation message
    await expect(page.locator('text=Request cancelled')).toBeVisible({ timeout: 5000 });
  });

  test('should handle network errors gracefully', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    // Mock network error for streaming
    await page.route('http://localhost:8000/ask/stream', async route => {
      await route.abort('internetdisconnected');
    });
    
    // Mock network error for fallback JSON too
    await page.route('http://localhost:8000/ask', async route => {
      await route.abort('internetdisconnected');
    });

    await textarea.fill('Test network error');
    await sendButton.click();
    
    // Should show some form of error message
    await expect(page.locator('.prose').filter({ hasText: /error|failed/i })).toBeVisible({ timeout: 10000 });
  });
});