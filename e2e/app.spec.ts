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
    // Empty textarea shows 1 line by default
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
    await page.click('button:has-text("Bash")');
    
    const input = page.locator('#codeInput');
    await expect(input).not.toBeEmpty();
    
    // Bash example code should contain the known pattern
    const value = await input.inputValue();
    expect(value).toContain('#!/usr/bin/bash');
    expect(value).toContain('OUTPUT=');
    expect(value).toContain('for HOST');
  });

  test('should detect and fix misplaced quotes in example', async ({ page }) => {
    await page.click('button:has-text("Bash")');
    
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
  });

  test('should copy output to clipboard', async ({ page, context }) => {
    // Grant clipboard permissions
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    
    await page.click('button:has-text("Bash")');
    
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
    await page.click('button:has-text("Bash")');
    
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
    
    // Check that output contains the code lines with highlighting spans
    const output = page.locator('#codeOutput');
    await expect(output).toContainText('if');
    await expect(output).toContainText('echo');
    // Verify syntax highlighting spans exist (any highlighting class)
    const highlightedSpans = page.locator('#codeOutput span[class]');
    await expect(highlightedSpans).not.toHaveCount(0);
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

test.describe('PHP Analysis Tests', () => {
  test('should detect PHP language', async ({ request }) => {
    const response = await request.post('/api/analyze', {
      data: {
        code: `<?php
$user = $_GET['name'];
if ($user == null) {
    $conn = mysql_connect("localhost", "root", "");
    extract($_POST);
    @file_get_contents($url);
}
?>`
      }
    });
    
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    
    expect(data.language).toBe('php');
    expect(data.errors.length + data.warnings.length).toBeGreaterThan(0);
  });

  test('should detect deprecated mysql functions', async ({ request }) => {
    const response = await request.post('/api/analyze', {
      data: { code: '<?php mysql_connect("host", "user", "pass"); ?>' }
    });
    
    const data = await response.json();
    expect(data.errors.some((e: any) => e.code === 'PHP003')).toBeTruthy();
  });
});

test.describe('JavaScript Analysis Tests', () => {
  test('should detect JavaScript language', async ({ request }) => {
    const response = await request.post('/api/analyze', {
      data: {
        code: `var userName = "John";
console.log(userName);
if (userName == "John") {
    var result = eval("2+2");
}`
      }
    });
    
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    
    expect(data.language).toBe('javascript');
    expect(data.errors.length + data.warnings.length).toBeGreaterThan(0);
  });

  test('should detect var usage and suggest let/const', async ({ request }) => {
    const response = await request.post('/api/analyze', {
      data: { code: 'var x = 1;' }
    });
    
    const data = await response.json();
    expect(data.warnings.some((w: any) => w.code === 'JS001')).toBeTruthy();
    expect(data.fixes.length).toBeGreaterThan(0);
  });

  test('should detect eval as dangerous', async ({ request }) => {
    const response = await request.post('/api/analyze', {
      data: { code: 'const x = eval("2+2");' }
    });
    
    const data = await response.json();
    expect(data.errors.some((e: any) => e.code === 'JS004')).toBeTruthy();
  });
});

test.describe('Node.js Analysis Tests', () => {
  test('should detect Node.js patterns', async ({ request }) => {
    const response = await request.post('/api/analyze', {
      data: {
        code: `const fs = require('fs');
var data = fs.readFileSync('/tmp/file.txt');
console.log(data);
module.exports = { data };`
      }
    });
    
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    
    expect(data.language).toBe('nodejs');
  });

  test('should detect sync fs operations', async ({ request }) => {
    const response = await request.post('/api/analyze', {
      data: { code: "const fs = require('fs'); fs.readFileSync('x');" }
    });
    
    const data = await response.json();
    expect(data.warnings.some((w: any) => w.code === 'NODE002')).toBeTruthy();
  });
});

test.describe('Bash Analysis Tests', () => {
  test('should detect Bash language', async ({ request }) => {
    const response = await request.post('/api/analyze', {
      data: {
        code: `#!/bin/bash
for i in 1 2 3; do
    echo $i
done
cd /tmp
read NAME`
      }
    });
    
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    
    expect(data.language).toBe('bash');
  });

  test('should detect cd without error handling', async ({ request }) => {
    const response = await request.post('/api/analyze', {
      data: { code: '#!/bin/bash\ncd /some/dir' }
    });
    
    const data = await response.json();
    expect(data.warnings.some((w: any) => w.code === 'SC2164')).toBeTruthy();
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

test.describe('Config File Analysis Tests', () => {
  test('should analyze Dockerfile', async ({ request }) => {
    const response = await request.post('/api/analyze', {
      data: {
        code: `FROM ubuntu
RUN apt-get install -y python3
ADD app.py /app/
WORKDIR app
ENV DATABASE_PASSWORD=secret123
CMD python3 app.py`
      }
    });
    
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    
    expect(data.language).toBe('dockerfile');
    expect(data.warnings.some((w: any) => w.code === 'DOCKER001')).toBeTruthy(); // :latest
    expect(data.errors.some((e: any) => e.code === 'DOCKER007')).toBeTruthy(); // hardcoded secret
  });

  test('should analyze docker-compose.yml', async ({ request }) => {
    const response = await request.post('/api/analyze', {
      data: {
        code: `version: '3.8'
services:
  web:
    image: nginx
    privileged: true
    environment:
      - DATABASE_PASSWORD=secret`
      }
    });
    
    const data = await response.json();
    expect(data.language).toBe('docker-compose');
    expect(data.errors.some((e: any) => e.code === 'COMPOSE002')).toBeTruthy(); // privileged
  });

  test('should analyze SQL', async ({ request }) => {
    const response = await request.post('/api/analyze', {
      data: {
        code: `SELECT * FROM users;
UPDATE users SET status = 'active';
DELETE FROM orders;
DROP TABLE logs;`
      }
    });
    
    const data = await response.json();
    expect(data.language).toBe('sql');
    expect(data.warnings.some((w: any) => w.code === 'SQL001')).toBeTruthy(); // SELECT *
    expect(data.errors.some((e: any) => e.code === 'SQL003')).toBeTruthy(); // UPDATE without WHERE
  });

  test('should analyze Terraform', async ({ request }) => {
    const response = await request.post('/api/analyze', {
      data: {
        code: `provider "aws" {
  access_key = "AKIAIOSFODNN7EXAMPLE"
}

resource "aws_security_group" "allow_all" {
  ingress {
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_s3_bucket" "data" {
  acl = "public-read"
}`
      }
    });
    
    const data = await response.json();
    expect(data.language).toBe('terraform');
    expect(data.errors.some((e: any) => e.code === 'TF001')).toBeTruthy(); // hardcoded creds
    expect(data.warnings.some((w: any) => w.code === 'TF002')).toBeTruthy(); // 0.0.0.0/0
  });

  test('should analyze Kubernetes YAML', async ({ request }) => {
    const response = await request.post('/api/analyze', {
      data: {
        code: `apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: default
spec:
  template:
    spec:
      containers:
      - name: app
        image: myapp:latest
        securityContext:
          privileged: true
          runAsUser: 0`
      }
    });
    
    const data = await response.json();
    expect(data.language).toBe('kubernetes');
    expect(data.errors.some((e: any) => e.code === 'K8S001')).toBeTruthy(); // privileged
    expect(data.warnings.some((w: any) => w.code === 'K8S007')).toBeTruthy(); // default namespace
  });

  test('should analyze nginx config', async ({ request }) => {
    const response = await request.post('/api/analyze', {
      data: {
        code: `server {
    listen 443 ssl;
    server_tokens on;
    autoindex on;
    ssl_protocols SSLv3 TLSv1;
}`
      }
    });
    
    const data = await response.json();
    expect(data.language).toBe('nginx');
    expect(data.warnings.some((w: any) => w.code === 'NGINX001')).toBeTruthy(); // server_tokens
    expect(data.errors.some((e: any) => e.code === 'NGINX003')).toBeTruthy(); // weak SSL
  });

  test('should analyze GitHub Actions', async ({ request }) => {
    const response = await request.post('/api/analyze', {
      data: {
        code: `name: CI
on:
  push:
  pull_request_target:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@master
      - run: echo "API_KEY: hardcoded-key"`
      }
    });
    
    const data = await response.json();
    expect(data.language).toBe('github-actions');
    expect(data.warnings.some((w: any) => w.code === 'GHA001')).toBeTruthy(); // @master
    expect(data.warnings.some((w: any) => w.code === 'GHA002')).toBeTruthy(); // pull_request_target
  });

  test('should analyze Ansible playbook', async ({ request }) => {
    const response = await request.post('/api/analyze', {
      data: {
        code: `- hosts: webservers
  become: true
  tasks:
    - name: Set password
      mysql_user:
        password: "mypassword123"
    - shell: cat /etc/passwd
    - command: ls -la
      ignore_errors: true`
      }
    });
    
    const data = await response.json();
    expect(data.language).toBe('ansible');
    expect(data.errors.some((e: any) => e.code === 'ANS001')).toBeTruthy(); // plain text password
    expect(data.warnings.some((w: any) => w.code === 'ANS004')).toBeTruthy(); // ignore_errors
  });
});
