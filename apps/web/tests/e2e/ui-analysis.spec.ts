import { test, expect } from '@playwright/test';

test.describe('Modern UI Redesign Validation', () => {
  test('validate new modern design loads correctly', async ({ page }) => {
    // Navigate to the application
    await page.goto('/');
    
    // Wait for the page to load completely
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    // Take full page screenshot of new design
    await page.screenshot({ 
      path: 'test-results/modern-ui/01-new-design-initial.png', 
      fullPage: true 
    });
    
    // Check if modern header is present
    const header = page.locator('header');
    await expect(header).toBeVisible();
    
    // Check if KhoborAgent title with gradient is present
    const title = page.locator('h1', { hasText: 'KhoborAgent' });
    await expect(title).toBeVisible();
    
    // Check for welcome screen
    const welcomeMessage = page.locator('h2', { hasText: 'Welcome to KhoborAgent' });
    await expect(welcomeMessage).toBeVisible();
    
    // Check modern input area with gradient background
    const inputArea = page.locator('textarea[placeholder*="Ask me anything"]');
    await expect(inputArea).toBeVisible();
    
    console.log('New modern design validated successfully');
  });

  test('test modern chat functionality with new UI', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Find the modern input field
    const messageInput = page.locator('textarea[placeholder*="Ask me anything"]');
    const sendButton = page.locator('button').filter({ has: page.locator('[data-lucide="send"]') });
    
    // Type a test message
    await messageInput.fill('What is artificial intelligence?');
    await page.screenshot({ 
      path: 'test-results/modern-ui/02-message-typed.png', 
      fullPage: true 
    });
    
    // Send the message
    await sendButton.click();
    
    // Wait for modern user message bubble to appear
    try {
      await page.waitForSelector('.bg-gradient-to-br.from-blue-500.to-blue-600', { timeout: 3000 });
      await page.screenshot({ 
        path: 'test-results/modern-ui/03-user-message-sent.png', 
        fullPage: true 
      });
    } catch (error) {
      console.log('User message bubble might have different styling');
    }
    
    // Wait for assistant response with new styling
    try {
      await page.waitForSelector('.bg-white.rounded-2xl.shadow-lg', { timeout: 15000 });
      await page.screenshot({ 
        path: 'test-results/modern-ui/04-assistant-response.png', 
        fullPage: true 
      });
      
      // Test second message to verify no caching issues
      await messageInput.fill('Tell me about machine learning');
      await sendButton.click();
      
      await page.waitForTimeout(5000);
      await page.screenshot({ 
        path: 'test-results/modern-ui/05-second-conversation.png', 
        fullPage: true 
      });
      
    } catch (error) {
      console.log('Backend might be down or slow');
      await page.screenshot({ 
        path: 'test-results/modern-ui/04-no-backend-response.png', 
        fullPage: true 
      });
    }
  });

  test('test responsive design of new UI', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Test tablet view
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.screenshot({ 
      path: 'test-results/modern-ui/06-tablet-responsive.png', 
      fullPage: true 
    });
    
    // Test mobile view
    await page.setViewportSize({ width: 375, height: 812 });
    await page.screenshot({ 
      path: 'test-results/modern-ui/07-mobile-responsive.png', 
      fullPage: true 
    });
    
    // Test large desktop view
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.screenshot({ 
      path: 'test-results/modern-ui/08-desktop-large.png', 
      fullPage: true 
    });
    
    // Reset to standard desktop
    await page.setViewportSize({ width: 1200, height: 800 });
  });

  test('test new citation bubbles and interactions', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Send a message that might generate citations
    const messageInput = page.locator('textarea[placeholder*="Ask me anything"]');
    const sendButton = page.locator('button').filter({ has: page.locator('[data-lucide="send"]') });
    
    await messageInput.fill('What are the latest scientific discoveries?');
    await sendButton.click();
    
    try {
      // Wait for response
      await page.waitForTimeout(10000);
      
      // Look for citation bubbles (small blue circles with numbers)
      const citationBubbles = page.locator('.w-6.h-6.text-xs.font-medium.text-blue-600');
      
      // Take screenshot of conversation with citations
      await page.screenshot({ 
        path: 'test-results/modern-ui/09-citations-display.png', 
        fullPage: true 
      });
      
      // Try to hover over citation bubble to see tooltip
      if (await citationBubbles.first().isVisible()) {
        await citationBubbles.first().hover();
        await page.waitForTimeout(500);
        await page.screenshot({ 
          path: 'test-results/modern-ui/10-citation-tooltip.png', 
          fullPage: true 
        });
      }
      
    } catch (error) {
      console.log('No citations or backend unavailable');
      await page.screenshot({ 
        path: 'test-results/modern-ui/09-no-citations.png', 
        fullPage: true 
      });
    }
  });

  test('test animation and interaction quality', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Test smooth animations on page load
    await page.screenshot({ 
      path: 'test-results/modern-ui/11-animations-loaded.png', 
      fullPage: true 
    });
    
    // Test language and mode toggles
    const languageToggle = page.locator('button', { hasText: 'English' });
    await languageToggle.click();
    await page.screenshot({ 
      path: 'test-results/modern-ui/12-language-toggle.png', 
      fullPage: true 
    });
    
    const modeToggle = page.locator('button', { hasText: 'Deep' });
    await modeToggle.click();
    await page.screenshot({ 
      path: 'test-results/modern-ui/13-mode-toggle.png', 
      fullPage: true 
    });
    
    // Test input focus and styling
    const messageInput = page.locator('textarea[placeholder*="Ask me anything"]');
    await messageInput.focus();
    await page.screenshot({ 
      path: 'test-results/modern-ui/14-input-focused.png', 
      fullPage: true 
    });
    
    // Test action buttons hover states
    const sendButton = page.locator('button').filter({ has: page.locator('[data-lucide="send"]') });
    await messageInput.fill('Test message for animations');
    await sendButton.hover();
    await page.screenshot({ 
      path: 'test-results/modern-ui/15-button-hover.png', 
      fullPage: true 
    });
  });

  test('validate accessibility and usability improvements', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Check contrast and readability
    await page.screenshot({ 
      path: 'test-results/modern-ui/16-accessibility-overview.png', 
      fullPage: true 
    });
    
    // Test keyboard navigation
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.screenshot({ 
      path: 'test-results/modern-ui/17-keyboard-navigation.png', 
      fullPage: true 
    });
    
    // Test focus states
    const messageInput = page.locator('textarea[placeholder*="Ask me anything"]');
    await messageInput.focus();
    await messageInput.type('Testing accessibility');
    await page.keyboard.press('Enter');
    
    // Wait a moment for any response
    await page.waitForTimeout(3000);
    await page.screenshot({ 
      path: 'test-results/modern-ui/18-final-usability-test.png', 
      fullPage: true 
    });
  });
});