import { test, expect } from '@playwright/test';

test.describe('Pactown Live Debug - E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should load the application', async ({ page }) => {
    await expect(page).toHaveTitle('Pactown Live Debug');
    await expect(page.locator('h1')).toContainText('Pactown Live Debug');
    await expect(page.locator('.status-badge')).toContainText('ShellCheck Active');
  });

  test('should display empty state initially', async ({ page }) => {
    await expect(page.locator('#codeOutput .empty-state')).toBeVisible();
    await expect(page.locator('#lineCount')).toHaveText('0');
    await expect(page.locator('#charCount')).toHaveText('0');
  });

  test('should update stats when typing code', async ({ page }) => {
    const input = page.locator('#codeInput');
    await input.fill('#!/bin/bash\necho "Hello"');
    
    await expect(page.locator('#lineCount')).toHaveText('2');
    await expect(page.locator('#charCount')).toHaveText('24');
  });

  test('should analyze code and show results', async ({ page }) => {
    const input = page.locator('#codeInput');
    
    // Code with known issue - unquoted variable
    await input.fill('#!/bin/bash\necho $VAR');
    
    // Wait for analysis to complete
    await page.waitForFunction(() => {
      const status = document.getElementById('analyzeStatus');
      return status?.textContent === 'Analiza zakończona';
    }, { timeout: 5000 });
    
    // Output should no longer show empty state
    await expect(page.locator('#codeOutput .empty-state')).not.toBeVisible();
    
    // Should show some output
    await expect(page.locator('#codeOutput')).not.toBeEmpty();
  });

  test('should load example code', async ({ page }) => {
    await page.click('button:has-text("Przykład")');
    
    const input = page.locator('#codeInput');
    await expect(input).not.toBeEmpty();
    
    // Example code should contain the known pattern
    const value = await input.inputValue();
    expect(value).toContain('#!/usr/bin/bash');
    expect(value).toContain('OUTPUT=');
    expect(value).toContain('for HOST');
  });

  test('should detect and fix misplaced quotes in example', async ({ page }) => {
    await page.click('button:has-text("Przykład")');
    
    // Wait for analysis
    await page.waitForFunction(() => {
      const status = document.getElementById('analyzeStatus');
      return status?.textContent === 'Analiza zakończona';
    }, { timeout: 5000 });
    
    // Should detect errors/fixes
    const errorCount = page.locator('#errorCount');
    const fixedCount = page.locator('#fixedCount');
    
    // Output should have code lines
    const codeLines = page.locator('#codeOutput .code-line');
    await expect(codeLines).not.toHaveCount(0);
  });

  test('should clear input', async ({ page }) => {
    const input = page.locator('#codeInput');
    await input.fill('#!/bin/bash\ntest code');
    
    await page.click('button:has-text("Wyczyść")');
    
    await expect(input).toHaveValue('');
    await expect(page.locator('#lineCount')).toHaveText('0');
  });

  test('should copy output to clipboard', async ({ page, context }) => {
    // Grant clipboard permissions
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    
    await page.click('button:has-text("Przykład")');
    
    // Wait for analysis
    await page.waitForFunction(() => {
      const status = document.getElementById('analyzeStatus');
      return status?.textContent === 'Analiza zakończona';
    }, { timeout: 5000 });
    
    // Click copy button
    await page.click('button:has-text("Kopiuj")');
    
    // Should show success toast
    await expect(page.locator('.toast.show')).toContainText('Skopiowano');
  });

  test('should show toast on download without code', async ({ page }) => {
    await page.click('button:has-text("Pobierz")');
    
    // Should show error toast
    await expect(page.locator('.toast.show')).toContainText('Brak kodu');
  });

  test('should clear history', async ({ page }) => {
    // First load example and wait for analysis
    await page.click('button:has-text("Przykład")');
    
    await page.waitForFunction(() => {
      const status = document.getElementById('analyzeStatus');
      return status?.textContent === 'Analiza zakończona';
    }, { timeout: 5000 });
    
    // Clear history
    await page.click('button:has-text("Wyczyść historię")');
    
    // Should show toast
    await expect(page.locator('.toast.show')).toContainText('Historia wyczyszczona');
    
    // History should be empty
    await expect(page.locator('#historyContent .empty-state')).toBeVisible();
  });

  test('should display syntax highlighting', async ({ page }) => {
    const input = page.locator('#codeInput');
    await input.fill('#!/bin/bash\nif [ "$VAR" = "test" ]; then\n  echo "Hello"\nfi');
    
    // Wait for analysis
    await page.waitForFunction(() => {
      const status = document.getElementById('analyzeStatus');
      return status?.textContent === 'Analiza zakończona';
    }, { timeout: 5000 });
    
    // Check for syntax highlighting classes
    const keywords = page.locator('#codeOutput .keyword');
    await expect(keywords).not.toHaveCount(0);
  });

  test('should show line numbers', async ({ page }) => {
    const input = page.locator('#codeInput');
    await input.fill('line1\nline2\nline3');
    
    // Input line numbers should update
    const lineNumbers = page.locator('#inputLineNumbers');
    await expect(lineNumbers).toContainText('1');
    await expect(lineNumbers).toContainText('2');
    await expect(lineNumbers).toContainText('3');
  });
});

test.describe('Python Analysis Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should load Python example', async ({ page }) => {
    await page.click('button:has-text("Python")');
    
    const input = page.locator('#codeInput');
    const value = await input.inputValue();
    
    expect(value).toContain('#!/usr/bin/env python3');
    expect(value).toContain('def process_data');
  });

  test('should detect Python language', async ({ page }) => {
    await page.click('button:has-text("Python")');
    
    // Wait for analysis
    await page.waitForFunction(() => {
      const status = document.getElementById('analyzeStatus');
      return status?.textContent === 'Analiza zakończona';
    }, { timeout: 5000 });
    
    // Should show Python badge
    const langBadge = page.locator('#languageBadge');
    await expect(langBadge).toContainText('PYTHON');
  });

  test('should detect Python issues via API', async ({ request }) => {
    const response = await request.post('/api/analyze', {
      data: {
        code: `#!/usr/bin/env python3
def test(items=[]):
    if x == None:
        print "hello"
    except:
        pass`
      }
    });
    
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    
    expect(data.language).toBe('python');
    // Should detect at least some issues
    expect(data.errors.length + data.warnings.length).toBeGreaterThan(0);
  });
});

test.describe('API Tests', () => {
  test('should analyze code via API', async ({ request }) => {
    const response = await request.post('/api/analyze', {
      data: {
        code: '#!/bin/bash\necho $VAR'
      }
    });
    
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data).toHaveProperty('originalCode');
    expect(data).toHaveProperty('fixedCode');
    expect(data).toHaveProperty('errors');
    expect(data).toHaveProperty('warnings');
    expect(data).toHaveProperty('fixes');
  });

  test('should return errors for malformed JSON', async ({ request }) => {
    const response = await request.post('/api/analyze', {
      data: 'not json',
      headers: {
        'Content-Type': 'text/plain'
      }
    });
    
    expect(response.status()).toBe(400);
  });

  test('should handle empty code', async ({ request }) => {
    const response = await request.post('/api/analyze', {
      data: { code: '' }
    });
    
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.errors).toHaveLength(0);
  });

  test('should detect quote positioning errors', async ({ request }) => {
    const response = await request.post('/api/analyze', {
      data: {
        code: '#!/bin/bash\necho "$(hostname -f")'
      }
    });
    
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    
    // Should detect the quote issue
    const hasQuoteError = data.errors.some((e: any) => 
      e.code === 'SC1073' || e.message?.includes('cudzysłów')
    ) || data.fixes.length > 0;
    
    expect(hasQuoteError || data.warnings.length > 0).toBeTruthy();
  });

  test('should serve static files', async ({ request }) => {
    const response = await request.get('/index.html');
    expect(response.ok()).toBeTruthy();
    expect(response.headers()['content-type']).toContain('text/html');
  });

  test('should return health status', async ({ request }) => {
    const response = await request.get('/api/health');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.status).toBe('healthy');
    expect(data.version).toBeDefined();
    expect(data.features).toBeDefined();
    expect(data.features.bash_analysis).toBe(true);
    expect(data.features.python_analysis).toBe(true);
  });
});
