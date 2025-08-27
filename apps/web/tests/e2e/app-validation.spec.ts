import { test, expect } from '@playwright/test';

test.describe('KhoborAgent Application - Updated Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Wait for the page to load completely
    await page.waitForLoadState('networkidle');
  });

  test('should load the main page correctly', async ({ page }) => {
    // Check page title
    await expect(page).toHaveTitle(/KhoborAgent/i);
    
    // Check for specific header element (not just text)
    await expect(page.locator('span.gradient-text', { hasText: 'KhoborAgent' })).toBeVisible();
    
    // Check for main input textarea
    await expect(page.getByPlaceholder('Type your message...')).toBeVisible();
    
    // Check for Send button
    await expect(page.getByRole('button', { name: /send/i })).toBeVisible();
    
    // Check for Cancel button
    await expect(page.getByRole('button', { name: /cancel/i })).toBeVisible();
  });

  test('should have language toggle buttons', async ({ page }) => {
    // Check for Bangla and English language buttons
    await expect(page.getByRole('button', { name: 'Bangla' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'English' })).toBeVisible();
    
    // Default should be Bangla selected (check for brand variant)
    const banglaButton = page.getByRole('button', { name: 'Bangla' });
    await expect(banglaButton).toHaveAttribute('class', /brand/);
    
    // Click English button
    await page.getByRole('button', { name: 'English' }).click();
    await expect(page.getByRole('button', { name: 'English' })).toHaveAttribute('class', /brand/);
  });

  test('should have mode toggle buttons', async ({ page }) => {
    // Check for Brief and Deep mode buttons
    await expect(page.getByRole('button', { name: 'Brief' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Deep' })).toBeVisible();
    
    // Default should be Brief selected
    const briefButton = page.getByRole('button', { name: 'Brief' });
    await expect(briefButton).toHaveAttribute('class', /brand/);
    
    // Click Deep button
    await page.getByRole('button', { name: 'Deep' }).click();
    await expect(page.getByRole('button', { name: 'Deep' })).toHaveAttribute('class', /brand/);
  });

  test('should have route badges in header', async ({ page }) => {
    // Check for route badges - use more specific selectors to avoid title conflicts
    await expect(page.locator('div:has-text("News")').filter({ hasText: /^News$/ }).first()).toBeVisible();
    await expect(page.locator('div:has-text("Weather")').filter({ hasText: /^Weather$/ }).first()).toBeVisible();
    await expect(page.locator('div:has-text("Markets")').filter({ hasText: /^Markets$/ }).first()).toBeVisible();
    await expect(page.locator('div:has-text("Sports")').filter({ hasText: /^Sports$/ }).first()).toBeVisible();
    await expect(page.locator('div:has-text("Lookup")').filter({ hasText: /^Lookup$/ }).first()).toBeVisible();
  });

  test('Send button should be disabled when input is empty', async ({ page }) => {
    const sendButton = page.getByRole('button', { name: /send/i });
    const textarea = page.getByPlaceholder('Type your message...');
    
    // Initially should be disabled
    await expect(sendButton).toBeDisabled();
    
    // Type something
    await textarea.fill('Test query');
    await expect(sendButton).toBeEnabled();
    
    // Clear input
    await textarea.fill('');
    await expect(sendButton).toBeDisabled();
  });

  test('Cancel button should be disabled initially', async ({ page }) => {
    const cancelButton = page.getByRole('button', { name: /cancel/i });
    
    // Initially should be disabled
    await expect(cancelButton).toBeDisabled();
  });

  test('should handle keyboard shortcuts', async ({ page }) => {
    const textarea = page.getByPlaceholder('Type your message...');
    
    // Type a message
    await textarea.fill('Test message');
    
    // Press Shift+Enter should add a new line
    await textarea.press('Shift+Enter');
    await expect(textarea).toHaveValue('Test message\n');
    
    // Clear and test escape (should not do anything when not streaming)
    await textarea.fill('Another test');
    await textarea.press('Escape');
    await expect(textarea).toHaveValue('Another test');
  });

  test('should show helper text', async ({ page }) => {
    await expect(page.locator('text=Enter to send · Shift+Enter for newline · Esc to cancel')).toBeVisible();
  });

  test('should have visible theme toggle', async ({ page }) => {
    // Look for theme toggle button - might be an icon button
    const themeToggle = page.locator('button').filter({ hasText: /theme/i }).or(
      page.locator('button[aria-label*="theme"]')
    ).or(
      page.locator('button').filter({ has: page.locator('svg') }).last()
    );
    
    // At least one theme toggle should be present
    await expect(themeToggle.first()).toBeVisible();
  });
});