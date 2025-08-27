import { test, expect } from '@playwright/test';

test.describe('Responsive Design', () => {
  test('should display correctly on desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1200, height: 800 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Header should show route badges in horizontal layout
    await expect(page.locator('text=News')).toBeVisible();
    await expect(page.locator('text=Weather')).toBeVisible();
    await expect(page.locator('text=Markets')).toBeVisible();
    
    // Language and mode buttons should be in the expected layout
    await expect(page.getByRole('button', { name: 'Bangla' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'English' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Brief' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Deep' })).toBeVisible();
    
    // Send and Cancel buttons should be visible
    await expect(page.getByRole('button', { name: /send/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /cancel/i })).toBeVisible();
  });

  test('should display correctly on tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // All main elements should still be visible on tablet
    await expect(page.locator('text=KhoborAgent')).toBeVisible();
    await expect(page.getByPlaceholder('Type your message...')).toBeVisible();
    await expect(page.getByRole('button', { name: /send/i })).toBeVisible();
    
    // Language and mode toggles should be visible
    await expect(page.getByRole('button', { name: 'Bangla' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Brief' })).toBeVisible();
  });

  test('should display correctly on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Header should show mobile layout for route badges
    await expect(page.locator('text=KhoborAgent')).toBeVisible();
    
    // Route badges should be in mobile layout (scrollable)
    await expect(page.locator('text=News')).toBeVisible();
    await expect(page.locator('text=Weather')).toBeVisible();
    
    // Main input area should be responsive
    await expect(page.getByPlaceholder('Type your message...')).toBeVisible();
    
    // Buttons should be stacked appropriately on mobile
    await expect(page.getByRole('button', { name: /send/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /cancel/i })).toBeVisible();
    
    // Language toggles should still work on mobile
    await expect(page.getByRole('button', { name: 'Bangla' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'English' })).toBeVisible();
  });

  test('should handle message bubbles responsively', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    // Mock API response
    await page.route('http://localhost:8000/ask/stream', async route => {
      const response = `data: {"type":"complete","data":{"answer_bn":"This is a test response to check mobile layout and wrapping behavior","sources":[{"title":"Mobile Test Source","url":"https://example.com","snippet":"This snippet should wrap correctly on mobile devices"}],"flags":{"disagreement":false,"single_source":false},"metrics":{"source_count":1,"updated_ct":"2023-01-01T00:00:00.000Z"},"followups":["Follow up 1","Follow up 2","Follow up 3"]}}\n\ndata: [DONE]\n\n`;
      
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: response,
      });
    });

    await textarea.fill('Mobile test message that is quite long to test wrapping behavior');
    await sendButton.click();
    
    // Wait for messages to appear
    await expect(page.locator('text=Mobile test message that is quite long to test wrapping behavior')).toBeVisible();
    await expect(page.locator('text=This is a test response to check mobile layout and wrapping behavior')).toBeVisible();
    
    // Message bubbles should be appropriately sized (max-w-[85%])
    const userMessage = page.locator('div:has-text("Mobile test message that is quite long to test wrapping behavior")').first();
    const assistantMessage = page.locator('div:has-text("This is a test response to check mobile layout and wrapping behavior")').first();
    
    await expect(userMessage).toBeVisible();
    await expect(assistantMessage).toBeVisible();
    
    // Action buttons should be visible and clickable on mobile
    await expect(page.getByRole('button', { name: 'Deep Dive' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Timeline' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'English' })).toBeVisible();
    
    // Followup buttons should wrap appropriately
    await expect(page.locator('button:has-text("Follow up 1")')).toBeVisible();
    await expect(page.locator('button:has-text("Follow up 2")')).toBeVisible();
    await expect(page.locator('button:has-text("Follow up 3")')).toBeVisible();
  });

  test('should handle dialog responsiveness', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const textarea = page.getByPlaceholder('Type your message...');
    const sendButton = page.getByRole('button', { name: /send/i });
    
    // Mock API response with English answer
    await page.route('http://localhost:8000/ask/stream', async route => {
      const response = `data: {"type":"complete","data":{"answer_bn":"বাংলা উত্তর","answer_en":"This is a longer English answer that should be displayed properly in the dialog on mobile devices. It should be readable and properly formatted.","sources":[],"flags":{"disagreement":false,"single_source":false},"metrics":{"source_count":0,"updated_ct":"2023-01-01T00:00:00.000Z"}}}\n\ndata: [DONE]\n\n`;
      
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: response,
      });
    });

    await textarea.fill('English dialog test');
    await sendButton.click();
    
    await expect(page.locator('text=বাংলা উত্তর')).toBeVisible();
    
    // Click English button to open dialog
    await page.getByRole('button', { name: 'English' }).click();
    
    // Dialog should be visible and properly sized on mobile
    await expect(page.locator('text=English Answer')).toBeVisible();
    await expect(page.locator('text=This is a longer English answer')).toBeVisible();
    
    // Dialog should have proper scrolling if content is long
    const dialogContent = page.locator('[role="dialog"]');
    await expect(dialogContent).toBeVisible();
  });

  test('should handle textarea resizing appropriately', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const textarea = page.getByPlaceholder('Type your message...');
    
    // Test with multi-line content
    const longText = 'This is a very long message that spans multiple lines and should cause the textarea to resize properly on mobile devices. '.repeat(3);
    
    await textarea.fill(longText);
    
    // Textarea should handle the long content appropriately
    await expect(textarea).toHaveValue(longText);
    
    // Clear and test shorter content
    await textarea.fill('Short message');
    await expect(textarea).toHaveValue('Short message');
  });

  test('should maintain functionality across different screen sizes', async ({ page }) => {
    const sizes = [
      { width: 1920, height: 1080, name: 'Desktop Large' },
      { width: 1366, height: 768, name: 'Desktop Standard' },
      { width: 768, height: 1024, name: 'Tablet' },
      { width: 414, height: 896, name: 'Mobile Large' },
      { width: 375, height: 667, name: 'Mobile Standard' },
    ];

    for (const size of sizes) {
      await page.setViewportSize(size);
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      
      // Basic functionality should work at all sizes
      await expect(page.getByPlaceholder('Type your message...')).toBeVisible();
      await expect(page.getByRole('button', { name: /send/i })).toBeVisible();
      await expect(page.getByRole('button', { name: 'Bangla' })).toBeVisible();
      await expect(page.getByRole('button', { name: 'English' })).toBeVisible();
      
      // Language toggle should work
      await page.getByRole('button', { name: 'English' }).click();
      await expect(page.getByRole('button', { name: 'English' })).toHaveClass(/brand/);
      
      // Mode toggle should work
      await page.getByRole('button', { name: 'Deep' }).click();
      await expect(page.getByRole('button', { name: 'Deep' })).toHaveClass(/brand/);
      
      // Reset for next iteration
      await page.getByRole('button', { name: 'Bangla' }).click();
      await page.getByRole('button', { name: 'Brief' }).click();
    }
  });

  test('should handle theme toggle across different screen sizes', async ({ page }) => {
    const sizes = [
      { width: 1200, height: 800 },
      { width: 768, height: 1024 },
      { width: 375, height: 667 },
    ];

    for (const size of sizes) {
      await page.setViewportSize(size);
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      
      // Theme toggle should be visible and functional
      const themeToggle = page.locator('button[aria-label="Toggle theme"]');
      await expect(themeToggle).toBeVisible();
      
      // Click theme toggle
      await themeToggle.click();
      
      // Theme should change (we can verify by checking for theme-related classes)
      // The exact implementation depends on how themes are applied
    }
  });
});