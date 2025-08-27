import { test, expect } from '@playwright/test';

test.describe('KhoborAgent Application', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Wait for the page to load completely
    await page.waitForLoadState('networkidle');
  });

  test('should load the main page correctly', async ({ page }) => {
    // Check if the main elements are present
    await expect(page).toHaveTitle(/KhoborAgent/i);
    
    // Check for header elements
    await expect(page.locator('text=KhoborAgent')).toBeVisible();
    
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
    
    // Default should be Bangla selected
    const banglaButton = page.getByRole('button', { name: 'Bangla' });
    await expect(banglaButton).toHaveClass(/brand/);
    
    // Click English button
    await page.getByRole('button', { name: 'English' }).click();
    await expect(page.getByRole('button', { name: 'English' })).toHaveClass(/brand/);
  });

  test('should have mode toggle buttons', async ({ page }) => {
    // Check for Brief and Deep mode buttons
    await expect(page.getByRole('button', { name: 'Brief' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Deep' })).toBeVisible();
    
    // Default should be Brief selected
    const briefButton = page.getByRole('button', { name: 'Brief' });
    await expect(briefButton).toHaveClass(/brand/);
    
    // Click Deep button
    await page.getByRole('button', { name: 'Deep' }).click();
    await expect(page.getByRole('button', { name: 'Deep' })).toHaveClass(/brand/);
  });

  test('should have theme toggle button in header', async ({ page }) => {
    // Look for theme toggle button
    const themeToggle = page.locator('button[aria-label="Toggle theme"]');
    await expect(themeToggle).toBeVisible();
    
    // Click theme toggle
    await themeToggle.click();
    // The theme should change (we can verify by checking for theme classes)
  });

  test('should have route badges in header', async ({ page }) => {
    // Check for route badges
    await expect(page.locator('text=News')).toBeVisible();
    await expect(page.locator('text=Weather')).toBeVisible();
    await expect(page.locator('text=Markets')).toBeVisible();
    await expect(page.locator('text=Sports')).toBeVisible();
    await expect(page.locator('text=Lookup')).toBeVisible();
    
    // News should be active by default
    const newsBadge = page.locator('[class*="brand"]', { hasText: 'News' });
    await expect(newsBadge).toBeVisible();
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
});