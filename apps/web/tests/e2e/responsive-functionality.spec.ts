import { test, expect } from '@playwright/test';

test.describe('Responsive Design and Cross-Device Tests', () => {
  
  test('should work correctly on desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1200, height: 800 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // All main elements should be visible on desktop
    await expect(page.locator('span.gradient-text', { hasText: 'KhoborAgent' })).toBeVisible();
    await expect(page.getByPlaceholder('Type your message...')).toBeVisible();
    await expect(page.getByRole('button', { name: /send/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /cancel/i })).toBeVisible();
    
    // Language and mode buttons should be visible
    await expect(page.getByRole('button', { name: 'Bangla' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'English' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Brief' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Deep' })).toBeVisible();
    
    // Route badges should be visible
    await expect(page.locator('div:has-text("News")').first()).toBeVisible();
    await expect(page.locator('div:has-text("Weather")').first()).toBeVisible();
  });

  test('should work correctly on tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // All main elements should still be accessible on tablet
    await expect(page.locator('span.gradient-text', { hasText: 'KhoborAgent' })).toBeVisible();
    await expect(page.getByPlaceholder('Type your message...')).toBeVisible();
    await expect(page.getByRole('button', { name: /send/i })).toBeVisible();
    
    // Language and mode toggles should be visible
    await expect(page.getByRole('button', { name: 'Bangla' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Brief' })).toBeVisible();
    
    // Test functionality on tablet
    const textarea = page.getByPlaceholder('Type your message...');
    await textarea.fill('Tablet test');
    await expect(page.getByRole('button', { name: /send/i })).toBeEnabled();
  });

  test('should work correctly on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Header should be visible on mobile
    await expect(page.locator('span.gradient-text', { hasText: 'KhoborAgent' })).toBeVisible();
    
    // Main input area should be responsive
    await expect(page.getByPlaceholder('Type your message...')).toBeVisible();
    
    // Buttons should be accessible on mobile
    await expect(page.getByRole('button', { name: /send/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /cancel/i })).toBeVisible();
    
    // Language toggles should work on mobile
    await expect(page.getByRole('button', { name: 'Bangla' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'English' })).toBeVisible();
    
    // Test interaction on mobile
    const englishButton = page.getByRole('button', { name: 'English' });
    await englishButton.click();
    await expect(englishButton).toHaveAttribute('class', /brand/);
  });

  test('should handle message display responsively', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    // Mock API response
    await page.route('http://localhost:8000/ask/stream', async route => {
      const response = `data: {"type":"complete","data":{"answer_bn":"This is a longer response to test mobile layout and word wrapping behavior. The text should wrap correctly on mobile devices and be readable.","sources":[{"title":"Mobile Test Source","url":"https://example.com","snippet":"This snippet should wrap correctly on mobile"}],"flags":{"disagreement":false,"single_source":false},"metrics":{"source_count":1,"updated_ct":"2023-01-01T00:00:00.000Z"},"followups":["Follow up 1","Follow up 2","Follow up 3"]}}\n\ndata: [DONE]\n\n`;
      
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: response,
      });
    });

    await textarea.fill('Mobile layout test message that is quite long to test wrapping');
    await sendButton.click();
    
    // Wait for messages to appear
    await expect(page.locator('text=Mobile layout test message that is quite long to test wrapping')).toBeVisible();
    await expect(page.getByText('This is a longer response to test mobile layout', { exact: false })).toBeVisible();
    
    // Action buttons should be visible and functional on mobile
    await expect(page.getByRole('button', { name: 'Deep Dive' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Timeline' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'English' })).toBeVisible();
    
    // Followup buttons should be accessible
    await expect(page.locator('button:has-text("Follow up 1")')).toBeVisible();
  });

  test('should maintain functionality across screen size changes', async ({ page }) => {
    const sizes = [
      { width: 1920, height: 1080, name: 'Desktop Large' },
      { width: 768, height: 1024, name: 'Tablet' },
      { width: 375, height: 667, name: 'Mobile' },
    ];

    for (const size of sizes) {
      await page.setViewportSize(size);
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      
      // Basic functionality should work at all sizes
      await expect(page.getByPlaceholder('Type your message...')).toBeVisible();
      await expect(page.getByRole('button', { name: /send/i })).toBeVisible();
      
      // Language toggle should work
      const englishButton = page.getByRole('button', { name: 'English' });
      const banglaButton = page.getByRole('button', { name: 'Bangla' });
      await expect(englishButton).toBeVisible();
      await expect(banglaButton).toBeVisible();
      
      await englishButton.click();
      await expect(englishButton).toHaveAttribute('class', /brand/);
      
      // Mode toggle should work
      const deepButton = page.getByRole('button', { name: 'Deep' });
      const briefButton = page.getByRole('button', { name: 'Brief' });
      await expect(deepButton).toBeVisible();
      await expect(briefButton).toBeVisible();
      
      await deepButton.click();
      await expect(deepButton).toHaveAttribute('class', /brand/);
      
      // Reset for next iteration
      await banglaButton.click();
      await briefButton.click();
    }
  });

  test('should handle textarea resizing appropriately', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const textarea = page.getByPlaceholder('Type your message...');
    
    // Test with multi-line content
    const longText = 'Line 1\nLine 2\nLine 3\nThis is a very long line that should wrap properly on mobile devices and show appropriate textarea behavior.';
    
    await textarea.fill(longText);
    await expect(textarea).toHaveValue(longText);
    
    // Test Shift+Enter for new line
    await textarea.fill('First line');
    await textarea.press('Shift+Enter');
    await textarea.type('Second line');
    await expect(textarea).toHaveValue('First line\nSecond line');
  });

  test('should handle keyboard shortcuts on all devices', async ({ page }) => {
    const sizes = [
      { width: 1200, height: 800 },
      { width: 768, height: 1024 },
      { width: 375, height: 667 },
    ];

    for (const size of sizes) {
      await page.setViewportSize(size);
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      
      const textarea = page.getByPlaceholder('Type your message...');
      
      // Test Shift+Enter for new line
      await textarea.fill('Test');
      await textarea.press('Shift+Enter');
      await textarea.type('New line');
      await expect(textarea).toHaveValue('Test\nNew line');
      
      // Clear for next test
      await textarea.fill('');
    }
  });

  test('should work correctly in different orientations', async ({ page, browserName }) => {
    // Test portrait mode
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    await expect(page.getByPlaceholder('Type your message...')).toBeVisible();
    await expect(page.getByRole('button', { name: /send/i })).toBeVisible();
    
    // Test landscape mode (rotated)
    await page.setViewportSize({ width: 667, height: 375 });
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    // Should still be functional in landscape
    await expect(page.getByPlaceholder('Type your message...')).toBeVisible();
    await expect(page.getByRole('button', { name: /send/i })).toBeVisible();
    
    // Test basic functionality in landscape
    const textarea = page.getByPlaceholder('Type your message...');
    await textarea.fill('Landscape test');
    await expect(page.getByRole('button', { name: /send/i })).toBeEnabled();
  });
});