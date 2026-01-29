#!/usr/bin/env python3
"""
Comprehensive test suite for pactfix-py
Tests 100+ error types across 24 different technologies/DSLs
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pactfix.analyzer import analyze_code, detect_language, add_fix_comments, SUPPORTED_LANGUAGES


@dataclass
class TestResult:
    """Result of a single test case."""
    __test__ = False
    language: str
    file_path: str
    errors_found: int
    warnings_found: int
    fixes_applied: int
    expected_min_issues: int
    passed: bool
    details: List[str] = field(default_factory=list)


@dataclass
class TestSuiteResult:
    """Result of the entire test suite."""
    __test__ = False
    total_tests: int
    passed_tests: int
    failed_tests: int
    total_errors: int
    total_warnings: int
    total_fixes: int
    languages_tested: List[str]
    results: List[TestResult]
    timestamp: str
    duration_seconds: float


# Expected minimum issues per fixture file
EXPECTED_ISSUES = {
    'typescript': 10,
    'go': 10,
    'rust': 10,
    'java': 10,
    'csharp': 10,
    'ruby': 10,
    'makefile': 5,
    'yaml': 5,
    'json': 3,
    'toml': 3,
    'ini': 3,
    'apache': 8,
    'systemd': 8,
    'html': 10,
    'css': 10,
    'bash': 5,
    'python': 5,
    'php': 5,
    'javascript': 5,
    'dockerfile': 5,
    'docker-compose': 5,
    'sql': 5,
    'terraform': 5,
    'kubernetes': 5,
    'nginx': 3,
    'github-actions': 5,
    'ansible': 5,
    'helm': 4,
    'gitlab-ci': 4,
    'jenkinsfile': 4,
}

# Fixture file mappings
FIXTURE_FILES = {
    'typescript': 'typescript/errors.ts',
    'go': 'go/errors.go',
    'rust': 'rust/errors.rs',
    'java': 'java/Errors.java',
    'csharp': 'csharp/Errors.cs',
    'ruby': 'ruby/errors.rb',
    'makefile': 'makefile/Makefile',
    'yaml': 'yaml/errors.yaml',
    'json': 'json/errors.json',
    'toml': 'toml/errors.toml',
    'ini': 'ini/errors.ini',
    'apache': 'apache/httpd.conf',
    'systemd': 'systemd/app.service',
    'html': 'html/errors.html',
    'css': 'css/errors.css',
    'bash': 'bash/errors.sh',
    'python': 'python/errors.py',
    'php': 'php/errors.php',
    'javascript': 'javascript/errors.js',
    'dockerfile': 'dockerfile/Dockerfile',
    'docker-compose': 'docker-compose/docker-compose.yml',
    'sql': 'sql/errors.sql',
    'terraform': 'terraform/errors.tf',
    'kubernetes': 'kubernetes/deployment.yaml',
    'nginx': 'nginx/nginx.conf',
    'github-actions': 'github-actions/workflow.yml',
    'ansible': 'ansible/playbook.yml',
    'helm': 'helm/values.yaml',
    'gitlab-ci': 'gitlab-ci/.gitlab-ci.yml',
    'jenkinsfile': 'jenkinsfile/Jenkinsfile',
}


def get_fixtures_dir() -> Path:
    """Get the fixtures directory path."""
    return Path(__file__).parent / 'fixtures'


def run_language_check(language: str, fixture_file: str, expected_min: int) -> TestResult:
    """Test a single language fixture."""
    fixtures_dir = get_fixtures_dir()
    file_path = fixtures_dir / fixture_file
    
    if not file_path.exists():
        return TestResult(
            language=language,
            file_path=str(file_path),
            errors_found=0,
            warnings_found=0,
            fixes_applied=0,
            expected_min_issues=expected_min,
            passed=False,
            details=[f"Fixture file not found: {file_path}"]
        )
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
    except Exception as e:
        return TestResult(
            language=language,
            file_path=str(file_path),
            errors_found=0,
            warnings_found=0,
            fixes_applied=0,
            expected_min_issues=expected_min,
            passed=False,
            details=[f"Error reading file: {e}"]
        )
    
    # Analyze the code
    result = analyze_code(code, str(file_path), language)
    
    # Check language detection
    detected = detect_language(code, str(file_path))
    
    total_issues = len(result.errors) + len(result.warnings)
    passed = total_issues >= expected_min
    
    details = []
    if detected != language and detected != 'bash':  # bash is default fallback
        details.append(f"Language detection: expected '{language}', got '{detected}'")
    
    for err in result.errors[:5]:  # Show first 5 errors
        details.append(f"ERROR [{err.code}] L{err.line}: {err.message}")
    
    for warn in result.warnings[:5]:  # Show first 5 warnings
        details.append(f"WARN [{warn.code}] L{warn.line}: {warn.message}")
    
    for fix in result.fixes[:5]:  # Show first 5 fixes
        details.append(f"FIX L{fix.line}: {fix.description}")
    
    if total_issues < expected_min:
        details.append(f"Expected at least {expected_min} issues, found {total_issues}")
    
    return TestResult(
        language=language,
        file_path=str(file_path),
        errors_found=len(result.errors),
        warnings_found=len(result.warnings),
        fixes_applied=len(result.fixes),
        expected_min_issues=expected_min,
        passed=passed,
        details=details
    )


def run_fix_comments_check(language: str, fixture_file: str) -> bool:
    """Test that fix comments are properly added."""
    if language == 'json':
        return True

    fixtures_dir = get_fixtures_dir()
    file_path = fixtures_dir / fixture_file
    
    if not file_path.exists():
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
    except Exception:
        return False
    
    result = analyze_code(code, str(file_path), language)
    
    if not result.fixes:
        return True  # No fixes to test
    
    fixed_with_comments = add_fix_comments(result)
    
    # Check that pactfix comments were added
    return 'pactfix:' in fixed_with_comments


@pytest.mark.parametrize(
    "language,fixture_file,expected_min",
    [
        (language, fixture_file, EXPECTED_ISSUES.get(language, 3))
        for language, fixture_file in FIXTURE_FILES.items()
    ],
)
def test_language(language: str, fixture_file: str, expected_min: int) -> None:
    result = run_language_check(language, fixture_file, expected_min)
    assert result.passed, "\n".join(result.details) if result.details else "Language check failed"


@pytest.mark.parametrize(
    "language,fixture_file",
    [(language, fixture_file) for language, fixture_file in FIXTURE_FILES.items()],
)
def test_fix_comments(language: str, fixture_file: str) -> None:
    assert run_fix_comments_check(language, fixture_file)


def run_all_tests(verbose: bool = True) -> TestSuiteResult:
    """Run all tests and return results."""
    start_time = datetime.now()
    results: List[TestResult] = []
    languages_tested = []
    
    print("=" * 70)
    print("PACTFIX-PY COMPREHENSIVE TEST SUITE")
    print(f"Testing {len(FIXTURE_FILES)} languages/technologies")
    print("=" * 70)
    print()
    
    for language, fixture_file in FIXTURE_FILES.items():
        expected_min = EXPECTED_ISSUES.get(language, 3)
        
        if verbose:
            print(f"Testing {language}...", end=" ")
        
        result = run_language_check(language, fixture_file, expected_min)
        results.append(result)
        languages_tested.append(language)
        
        if verbose:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"{status} ({result.errors_found}E/{result.warnings_found}W/{result.fixes_applied}F)")
            
            if not result.passed or verbose:
                for detail in result.details[:3]:
                    print(f"    {detail}")
    
    # Calculate totals
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    total_errors = sum(r.errors_found for r in results)
    total_warnings = sum(r.warnings_found for r in results)
    total_fixes = sum(r.fixes_applied for r in results)
    
    suite_result = TestSuiteResult(
        total_tests=len(results),
        passed_tests=passed,
        failed_tests=failed,
        total_errors=total_errors,
        total_warnings=total_warnings,
        total_fixes=total_fixes,
        languages_tested=languages_tested,
        results=results,
        timestamp=datetime.now().isoformat(),
        duration_seconds=duration
    )
    
    # Print summary
    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Total tests:     {suite_result.total_tests}")
    print(f"Passed:          {suite_result.passed_tests} ✅")
    print(f"Failed:          {suite_result.failed_tests} ❌")
    print(f"Total errors:    {suite_result.total_errors}")
    print(f"Total warnings:  {suite_result.total_warnings}")
    print(f"Total fixes:     {suite_result.total_fixes}")
    print(f"Duration:        {suite_result.duration_seconds:.2f}s")
    print("=" * 70)
    
    return suite_result


def save_report(result: TestSuiteResult, output_path: str = None):
    """Save test report to JSON file."""
    if output_path is None:
        output_path = Path(__file__).parent / 'test_report.json'
    
    report = {
        'summary': {
            'total_tests': result.total_tests,
            'passed_tests': result.passed_tests,
            'failed_tests': result.failed_tests,
            'total_errors': result.total_errors,
            'total_warnings': result.total_warnings,
            'total_fixes': result.total_fixes,
            'languages_tested': result.languages_tested,
            'timestamp': result.timestamp,
            'duration_seconds': result.duration_seconds,
        },
        'results': [
            {
                'language': r.language,
                'file_path': r.file_path,
                'errors_found': r.errors_found,
                'warnings_found': r.warnings_found,
                'fixes_applied': r.fixes_applied,
                'expected_min_issues': r.expected_min_issues,
                'passed': r.passed,
                'details': r.details,
            }
            for r in result.results
        ]
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\nReport saved to: {output_path}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run pactfix-py comprehensive tests')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-q', '--quiet', action='store_true', help='Quiet output')
    parser.add_argument('--save-report', action='store_true', help='Save report to JSON')
    parser.add_argument('--language', help='Test specific language only')
    
    args = parser.parse_args()
    
    verbose = not args.quiet
    
    if args.language:
        if args.language not in FIXTURE_FILES:
            print(f"Unknown language: {args.language}")
            print(f"Available: {', '.join(FIXTURE_FILES.keys())}")
            return 1
        
        fixture_file = FIXTURE_FILES[args.language]
        expected_min = EXPECTED_ISSUES.get(args.language, 3)
        result = run_language_check(args.language, fixture_file, expected_min)
        
        print(f"\n{args.language}: {'PASS' if result.passed else 'FAIL'}")
        print(f"  Errors:   {result.errors_found}")
        print(f"  Warnings: {result.warnings_found}")
        print(f"  Fixes:    {result.fixes_applied}")
        print(f"\nDetails:")
        for detail in result.details:
            print(f"  {detail}")
        
        return 0 if result.passed else 1
    
    result = run_all_tests(verbose=verbose)
    
    if args.save_report:
        save_report(result)
    
    return 0 if result.failed_tests == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
