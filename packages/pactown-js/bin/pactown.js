#!/usr/bin/env node
/**
 * Pactown Code Analyzer - Command Line Interface
 */

import { parseArgs } from 'util';
import { existsSync, writeFileSync, mkdirSync } from 'fs';
import { dirname, extname, basename, join } from 'path';
import { analyzeFile } from '../src/analyzer.js';

const options = {
    output: { type: 'string', short: 'o' },
    language: { type: 'string', short: 'l' },
    'log-file': { type: 'string' },
    verbose: { type: 'boolean', short: 'v', default: false },
    json: { type: 'boolean', default: false },
    'no-fix': { type: 'boolean', default: false },
    help: { type: 'boolean', short: 'h', default: false },
};

function printHelp() {
    console.log(`
Pactown Code Analyzer - Multi-language code analysis and auto-fix

Usage: pactown <input> [options]

Options:
  -o, --output <file>     Output file for fixed code
  -l, --language <lang>   Force language (bash, python, php, javascript, nodejs)
  --log-file <file>       Write analysis log to JSON file
  -v, --verbose           Verbose output
  --json                  Output results as JSON
  --no-fix                Only analyze, don't write fixed file
  -h, --help              Show this help

Examples:
  pactown script.sh -o fixed.sh
  pactown code.py --log-file analysis.json
  pactown app.js -l nodejs --verbose
`);
}

function log(message, level = 'info') {
    const timestamp = new Date().toISOString().split('T')[1].split('.')[0];
    const prefix = {
        info: '📋',
        error: '❌',
        warning: '⚠️',
        success: '✅',
    }[level] || '•';
    console.log(`${timestamp} ${prefix} ${message}`);
}

async function main() {
    let args;
    try {
        args = parseArgs({ options, allowPositionals: true });
    } catch (e) {
        console.error(`Error: ${e.message}`);
        printHelp();
        process.exit(1);
    }

    const { values, positionals } = args;

    if (values.help || positionals.length === 0) {
        printHelp();
        process.exit(0);
    }

    const inputPath = positionals[0];

    if (!existsSync(inputPath)) {
        log(`Input file not found: ${inputPath}`, 'error');
        process.exit(1);
    }

    let outputPath = values.output;
    if (!outputPath && !values['no-fix']) {
        const ext = extname(inputPath);
        const base = basename(inputPath, ext);
        const dir = dirname(inputPath);
        outputPath = join(dir, `${base}_fixed${ext}`);
    }

    log(`Analyzing: ${inputPath}`, 'info');
    if (values.language) {
        log(`Language: ${values.language}`, 'info');
    }

    try {
        const result = analyzeFile(
            inputPath,
            values['no-fix'] ? null : outputPath,
            values.language
        );

        log(`Language detected: ${result.language}`, 'success');
        log(`Errors: ${result.errors.length}`, result.errors.length > 0 ? 'error' : 'info');
        log(`Warnings: ${result.warnings.length}`, result.warnings.length > 0 ? 'warning' : 'info');
        log(`Fixes applied: ${result.fixes.length}`, 'success');

        if (values.verbose) {
            for (const error of result.errors) {
                log(`  Line ${error.line}: [${error.code}] ${error.message}`, 'error');
            }
            for (const warning of result.warnings) {
                log(`  Line ${warning.line}: [${warning.code}] ${warning.message}`, 'warning');
            }
            for (const fix of result.fixes) {
                log(`  Line ${fix.line}: ${fix.message}`, 'info');
                console.log(`    Before: ${fix.before}`);
                console.log(`    After:  ${fix.after}`);
            }
        }

        if (outputPath && !values['no-fix']) {
            log(`Fixed code written to: ${outputPath}`, 'success');
        }

        if (values['log-file']) {
            const logData = {
                timestamp: result.timestamp,
                inputFile: inputPath,
                outputFile: outputPath,
                language: result.language,
                errorsCount: result.errors.length,
                warningsCount: result.warnings.length,
                fixesCount: result.fixes.length,
                errors: result.errors,
                warnings: result.warnings,
                fixes: result.fixes,
            };

            mkdirSync(dirname(values['log-file']), { recursive: true });
            writeFileSync(values['log-file'], JSON.stringify(logData, null, 2), 'utf8');
            log(`Log written to: ${values['log-file']}`, 'success');
        }

        if (values.json) {
            console.log(JSON.stringify(result, null, 2));
        }

        process.exit(result.errors.length > 0 ? 1 : 0);

    } catch (e) {
        log(`Analysis failed: ${e.message}`, 'error');
        if (values.verbose) {
            console.error(e.stack);
        }
        process.exit(1);
    }
}

main();
