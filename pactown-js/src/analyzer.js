/**
 * Pactown Code Analyzer - Core Analysis Engine
 * Analyzes code files for common issues across multiple languages.
 */

import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { dirname, extname, basename, join } from 'path';

/**
 * Detect programming language from code and filename
 */
export function detectLanguage(code, filename = null) {
    if (filename) {
        const ext = extname(filename).toLowerCase();
        const extMap = {
            '.py': 'python',
            '.sh': 'bash',
            '.bash': 'bash',
            '.php': 'php',
            '.js': 'javascript',
            '.mjs': 'javascript',
            '.cjs': 'nodejs',
        };
        if (extMap[ext]) return extMap[ext];
    }

    const lines = code.trim().split('\n');
    const firstLine = lines[0] || '';

    if (firstLine.startsWith('#!')) {
        if (firstLine.toLowerCase().includes('python')) return 'python';
        if (firstLine.includes('bash') || firstLine.includes('sh')) return 'bash';
        if (firstLine.includes('node')) return 'nodejs';
    }

    if (code.includes('<?php') || code.includes('<?=')) return 'php';

    const pythonPatterns = [/^def\s+\w+\s*\(/, /^class\s+\w+/, /^import\s+\w+/, /^from\s+\w+\s+import/];
    for (const pattern of pythonPatterns) {
        if (lines.some(line => pattern.test(line))) return 'python';
    }

    const nodejsPatterns = [/\brequire\s*\(['"]/, /\bmodule\.exports\b/, /\bprocess\.(env|argv)\b/];
    for (const pattern of nodejsPatterns) {
        if (lines.some(line => pattern.test(line))) return 'nodejs';
    }

    const jsPatterns = [/\bconst\s+\w+\s*=/, /\blet\s+\w+\s*=/, /\bvar\s+\w+\s*=/, /=>\s*{/];
    for (const pattern of jsPatterns) {
        if (lines.some(line => pattern.test(line))) return 'javascript';
    }

    const bashPatterns = [/^\s*for\s+\w+\s+in\s+/, /^\s*if\s+\[\s+/, /\$\{?\w+\}?/];
    for (const pattern of bashPatterns) {
        if (lines.some(line => pattern.test(line))) return 'bash';
    }

    return 'bash';
}

/**
 * Analyze Bash code
 */
function analyzeBash(code) {
    const errors = [];
    const warnings = [];
    const fixes = [];
    const lines = code.split('\n');

    lines.forEach((line, i) => {
        const lineNum = i + 1;
        const stripped = line.trim();

        // Misplaced quotes in command substitution
        if (/"\$\([^)]*"\)/.test(line)) {
            errors.push({ line: lineNum, column: 1, code: 'SC1073', message: 'Cudzysłów zamykający jest w złym miejscu' });
            const fixed = line.replace(/("\$\([^)]*)(")(\))/, '$1$3$2');
            if (fixed !== line) {
                fixes.push({ line: lineNum, message: 'Poprawiono pozycję cudzysłowu', before: line.trim(), after: fixed.trim() });
            }
        }

        // cd without error handling
        if (/^\s*cd\s+[^&|;]+$/.test(line) && !line.includes('||')) {
            warnings.push({ line: lineNum, column: 1, code: 'SC2164', message: 'Użyj cd ... || exit' });
        }

        // read without -r
        if (/\bread\s+(?!.*-r)/.test(line) && !stripped.startsWith('#')) {
            warnings.push({ line: lineNum, column: 1, code: 'SC2162', message: 'Użyj read -r' });
        }
    });

    return { errors, warnings, fixes };
}

/**
 * Analyze Python code
 */
function analyzePython(code) {
    const errors = [];
    const warnings = [];
    const fixes = [];
    const lines = code.split('\n');

    lines.forEach((line, i) => {
        const lineNum = i + 1;
        const stripped = line.trim();

        // print without parentheses
        if (/^print\s+[^(]/.test(stripped)) {
            errors.push({ line: lineNum, column: 1, code: 'PY001', message: 'Użyj print() z nawiasami (Python 3)' });
            const fixed = line.replace(/^(\s*)print\s+(.+)$/, '$1print($2)');
            if (fixed !== line) {
                fixes.push({ line: lineNum, message: 'Dodano nawiasy do print()', before: line.trim(), after: fixed.trim() });
            }
        }

        // bare except
        if (/^\s*except\s*:/.test(stripped)) {
            warnings.push({ line: lineNum, column: 1, code: 'PY002', message: 'Unikaj pustego except:' });
        }

        // mutable default arguments
        if (/def\s+\w+\s*\([^)]*=\s*(\[\]|\{\})/.test(line)) {
            warnings.push({ line: lineNum, column: 1, code: 'PY003', message: 'Mutable default argument' });
        }

        // == None
        if (/==\s*None|!=\s*None/.test(line)) {
            warnings.push({ line: lineNum, column: 1, code: 'PY004', message: 'Użyj "is None" zamiast == None' });
        }
    });

    return { errors, warnings, fixes };
}

/**
 * Analyze PHP code
 */
function analyzePHP(code) {
    const errors = [];
    const warnings = [];
    const fixes = [];
    const lines = code.split('\n');

    lines.forEach((line, i) => {
        const lineNum = i + 1;
        const stripped = line.trim();

        // == instead of ===
        if (/[^=!<>]==[^=]/.test(line)) {
            warnings.push({ line: lineNum, column: 1, code: 'PHP002', message: 'Użyj === zamiast ==' });
        }

        // deprecated mysql_* functions
        if (/\bmysql_\w+\s*\(/.test(line)) {
            errors.push({ line: lineNum, column: 1, code: 'PHP003', message: 'Funkcje mysql_* są przestarzałe' });
        }

        // extract() usage
        if (/\bextract\s*\(/.test(line)) {
            warnings.push({ line: lineNum, column: 1, code: 'PHP004', message: 'extract() może być niebezpieczne' });
        }

        // error suppression @
        if (/@\w+/.test(line) && !stripped.startsWith('//')) {
            warnings.push({ line: lineNum, column: 1, code: 'PHP005', message: 'Operator @ tłumi błędy' });
        }

        // short open tag
        if (line.includes('<?=') || (stripped.startsWith('<?') && !stripped.startsWith('<?php'))) {
            warnings.push({ line: lineNum, column: 1, code: 'PHP006', message: 'Używaj pełnego tagu <?php' });
        }
    });

    return { errors, warnings, fixes };
}

/**
 * Analyze JavaScript/Node.js code
 */
function analyzeJavaScript(code) {
    const errors = [];
    const warnings = [];
    const fixes = [];
    const lines = code.split('\n');

    lines.forEach((line, i) => {
        const lineNum = i + 1;

        // var usage
        if (/\bvar\s+\w+/.test(line)) {
            warnings.push({ line: lineNum, column: 1, code: 'JS001', message: 'Użyj let lub const zamiast var' });
            const fixed = line.replace(/\bvar\b/, 'let');
            if (fixed !== line) {
                fixes.push({ line: lineNum, message: 'Zamieniono var na let', before: line.trim(), after: fixed.trim() });
            }
        }

        // == instead of ===
        if (/[^=!<>]==[^=]/.test(line)) {
            warnings.push({ line: lineNum, column: 1, code: 'JS002', message: 'Użyj === zamiast ==' });
        }

        // console.log
        if (/\bconsole\.(log|debug|info)\s*\(/.test(line)) {
            warnings.push({ line: lineNum, column: 1, code: 'JS003', message: 'console.log - usuń przed produkcją' });
        }

        // eval
        if (/\beval\s*\(/.test(line)) {
            errors.push({ line: lineNum, column: 1, code: 'JS004', message: 'eval() jest niebezpieczne' });
        }

        // require
        if (/\brequire\s*\(['"]/.test(line)) {
            warnings.push({ line: lineNum, column: 1, code: 'NODE001', message: 'Rozważ ES modules zamiast require()' });
        }

        // sync fs operations
        if (/\b(readFileSync|writeFileSync)\b/.test(line)) {
            warnings.push({ line: lineNum, column: 1, code: 'NODE002', message: 'Synchroniczne I/O blokuje event loop' });
        }
    });

    return { errors, warnings, fixes };
}

/**
 * Apply fixes to code
 */
function applyFixes(code, fixes, language) {
    let lines = code.split('\n');
    const commentChar = ['python', 'bash'].includes(language) ? '#' : '//';

    // Apply text fixes
    for (const fix of fixes) {
        const lineNum = fix.line - 1;
        if (lineNum >= 0 && lineNum < lines.length) {
            if (lines[lineNum].includes(fix.before)) {
                lines[lineNum] = lines[lineNum].replace(fix.before, fix.after);
            }
        }
    }

    // Add comments
    const sortedFixes = [...fixes].sort((a, b) => b.line - a.line);
    for (const fix of sortedFixes) {
        const lineNum = fix.line - 1;
        if (lineNum >= 0 && lineNum < lines.length) {
            const comment = `  ${commentChar} ✅ NAPRAWIONO: ${fix.message}`;
            if (!lines[lineNum].includes(comment)) {
                lines[lineNum] = lines[lineNum].trimEnd() + comment;
            }
        }
    }

    return lines.join('\n');
}

/**
 * Analyze code
 */
export function analyzeCode(code, language = null, filename = null) {
    const lang = language || detectLanguage(code, filename);

    const analyzers = {
        bash: analyzeBash,
        python: analyzePython,
        php: analyzePHP,
        javascript: analyzeJavaScript,
        nodejs: analyzeJavaScript,
    };

    const analyzer = analyzers[lang] || analyzeBash;
    const { errors, warnings, fixes } = analyzer(code);

    const fixedCode = applyFixes(code, fixes, lang);

    return {
        originalCode: code,
        fixedCode,
        language: lang,
        errors,
        warnings,
        fixes,
        timestamp: new Date().toISOString(),
    };
}

/**
 * Analyze a file
 */
export function analyzeFile(inputPath, outputPath = null, language = null) {
    const code = readFileSync(inputPath, 'utf8');
    const result = analyzeCode(code, language, inputPath);

    if (outputPath) {
        mkdirSync(dirname(outputPath), { recursive: true });
        writeFileSync(outputPath, result.fixedCode, 'utf8');
    }

    return result;
}

export default { analyzeCode, analyzeFile, detectLanguage };
