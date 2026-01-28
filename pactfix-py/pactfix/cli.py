"""Pactfix CLI - Command line interface for code analysis."""

import argparse
import json
import sys
import os
from pathlib import Path
from datetime import datetime

from .analyzer import analyze_code, detect_language, SUPPORTED_LANGUAGES, add_fix_comments
from .sandbox import Sandbox, detect_project_language, create_all_dockerfiles, LANGUAGE_DOCKERFILES


def main():
    parser = argparse.ArgumentParser(
        prog='pactfix',
        description='Multi-language code and config file analyzer and fixer'
    )
    
    parser.add_argument('input', nargs='?', help='Input file to analyze')
    parser.add_argument('-o', '--output', help='Output file for fixed code')
    parser.add_argument('-l', '--language', choices=SUPPORTED_LANGUAGES, help='Force language detection')
    parser.add_argument('--comment', action='store_true', help='Insert comment above each applied fix line')
    parser.add_argument('--log-file', help='Output JSON log file')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--batch', help='Process all files in directory')
    parser.add_argument('--fix-all', action='store_true', help='Fix all files in examples/')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--version', action='version', version='pactfix 1.0.0')
    
    # New options for project scanning and sandbox
    parser.add_argument('--path', help='Project path to scan and fix all files')
    parser.add_argument('--sandbox', action='store_true', help='Run fixes in Docker sandbox')
    parser.add_argument('--sandbox-only', action='store_true', help='Only setup sandbox without fixing')
    parser.add_argument('--test', action='store_true', help='Run tests in sandbox after fixing')
    parser.add_argument('--init-dockerfiles', help='Create Dockerfiles for all languages in specified directory')
    
    args = parser.parse_args()
    
    # Initialize Dockerfiles for all languages
    if args.init_dockerfiles:
        return init_dockerfiles(args.init_dockerfiles)
    
    # Project-wide scanning with --path
    if args.path:
        return process_project(args.path, args.comment, args.sandbox, args.test, args.verbose)
    
    # Sandbox-only mode
    if args.sandbox_only:
        input_path = args.input or '.'
        return setup_sandbox_only(input_path, args.verbose)
    
    if args.fix_all:
        return fix_all_examples(args.verbose, args.comment)
    
    if args.batch:
        return process_batch(args.batch, args.verbose)
    
    if args.input == '-':
        return process_stdin(args.output, args.language, args.comment, args.log_file, args.verbose, args.json)

    if not args.input:
        if not sys.stdin.isatty():
            return process_stdin(args.output, args.language, args.comment, args.log_file, args.verbose, args.json)
        parser.print_help()
        return 1
    
    return process_file(args.input, args.output, args.language, args.comment, args.log_file, args.verbose, args.json)


def process_file(input_path: str, output_path: str = None, language: str = None,
                 comment: bool = False, log_file: str = None, verbose: bool = False,
                 as_json: bool = False) -> int:
    """Process a single file."""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            code = f.read()
    except FileNotFoundError:
        print(f"❌ Plik nie istnieje: {input_path}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Błąd odczytu: {e}", file=sys.stderr)
        return 1
    
    result = analyze_code(code, input_path, language)
    if comment:
        result.fixed_code = add_fix_comments(result)
    
    if as_json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return 0
    
    timestamp = datetime.now().strftime('%H:%M:%S')
    
    if verbose:
        print(f"{timestamp} 📋 Analyzing: {input_path}")
        print(f"{timestamp} ✅ Language detected: {result.language}")
        print(f"{timestamp} ❌ Errors: {len(result.errors)}")
        print(f"{timestamp} ⚠️  Warnings: {len(result.warnings)}")
        print(f"{timestamp} ✅ Fixes applied: {len(result.fixes)}")
        
        for err in result.errors:
            print(f"{timestamp} ❌   Line {err.line}: [{err.code}] {err.message}")
        
        for warn in result.warnings:
            print(f"{timestamp} ⚠️    Line {warn.line}: [{warn.code}] {warn.message}")
        
        for fix in result.fixes:
            print(f"{timestamp} 📋   Line {fix.line}: {fix.description}")
            print(f"    Before: {fix.before}")
            print(f"    After:  {fix.after}")
    else:
        status = "✅" if len(result.errors) == 0 else "❌"
        print(f"{status} {input_path}: {len(result.errors)} errors, {len(result.warnings)} warnings, {len(result.fixes)} fixes [{result.language}]")
    
    if output_path:
        try:
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result.fixed_code)
            if verbose:
                print(f"{timestamp} ✅ Fixed code written to: {output_path}")
        except Exception as e:
            print(f"❌ Błąd zapisu: {e}", file=sys.stderr)
            return 1
    
    if log_file:
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'input_file': input_path,
            'output_file': output_path,
            'result': result.to_dict()
        }
        try:
            os.makedirs(os.path.dirname(log_file) or '.', exist_ok=True)
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
            if verbose:
                print(f"{timestamp} ✅ Log written to: {log_file}")
        except Exception as e:
            print(f"❌ Błąd zapisu logu: {e}", file=sys.stderr)
    
    return 0 if len(result.errors) == 0 else 1


def process_stdin(output_path: str = None, language: str = None, comment: bool = False,
                  log_file: str = None, verbose: bool = False, as_json: bool = False) -> int:
    """Process code from stdin."""
    try:
        code = sys.stdin.read()
    except Exception as e:
        print(f"❌ Błąd odczytu stdin: {e}", file=sys.stderr)
        return 1

    filename_hint = output_path or '<stdin>'
    result = analyze_code(code, filename_hint, language)
    if comment:
        result.fixed_code = add_fix_comments(result)

    if as_json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return 0

    timestamp = datetime.now().strftime('%H:%M:%S')

    if verbose:
        print(f"{timestamp} 📋 Analyzing: {filename_hint}")
        print(f"{timestamp} ✅ Language detected: {result.language}")
        print(f"{timestamp} ❌ Errors: {len(result.errors)}")
        print(f"{timestamp} ⚠️  Warnings: {len(result.warnings)}")
        print(f"{timestamp} ✅ Fixes applied: {len(result.fixes)}")

        for err in result.errors:
            print(f"{timestamp} ❌   Line {err.line}: [{err.code}] {err.message}")

        for warn in result.warnings:
            print(f"{timestamp} ⚠️    Line {warn.line}: [{warn.code}] {warn.message}")

        for fix in result.fixes:
            print(f"{timestamp} 📋   Line {fix.line}: {fix.description}")
            print(f"    Before: {fix.before}")
            print(f"    After:  {fix.after}")
    else:
        status = "✅" if len(result.errors) == 0 else "❌"
        print(f"{status} {filename_hint}: {len(result.errors)} errors, {len(result.warnings)} warnings, {len(result.fixes)} fixes [{result.language}]")

    if output_path:
        try:
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result.fixed_code)
            if verbose:
                print(f"{timestamp} ✅ Fixed code written to: {output_path}")
        except Exception as e:
            print(f"❌ Błąd zapisu: {e}", file=sys.stderr)
            return 1

    if log_file:
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'input_file': '<stdin>',
            'output_file': output_path,
            'result': result.to_dict()
        }
        try:
            os.makedirs(os.path.dirname(log_file) or '.', exist_ok=True)
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
            if verbose:
                print(f"{timestamp} ✅ Log written to: {log_file}")
        except Exception as e:
            print(f"❌ Błąd zapisu logu: {e}", file=sys.stderr)

    return 0 if len(result.errors) == 0 else 1


def process_batch(directory: str, verbose: bool = False) -> int:
    """Process all files in a directory."""
    path = Path(directory)
    if not path.is_dir():
        print(f"❌ Nie jest katalogiem: {directory}", file=sys.stderr)
        return 1
    
    extensions = ['.sh', '.py', '.php', '.js', '.sql', '.tf', '.yml', '.yaml', '.conf']
    files = []
    for ext in extensions:
        files.extend(path.rglob(f'*{ext}'))
    
    # Also find Dockerfiles
    files.extend(path.rglob('Dockerfile'))
    files.extend(path.rglob('docker-compose.yml'))
    files.extend(path.rglob('docker-compose.yaml'))
    
    if not files:
        print(f"⚠️  Brak plików do analizy w: {directory}")
        return 0
    
    print(f"📋 Znaleziono {len(files)} plików do analizy\n")
    
    total_errors = 0
    total_warnings = 0
    total_fixes = 0
    
    for file_path in sorted(set(files)):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            result = analyze_code(code, str(file_path))
            total_errors += len(result.errors)
            total_warnings += len(result.warnings)
            total_fixes += len(result.fixes)
            
            status = "✅" if len(result.errors) == 0 else "❌"
            rel_path = file_path.relative_to(path) if file_path.is_relative_to(path) else file_path
            print(f"{status} {rel_path}: {len(result.errors)}E {len(result.warnings)}W {len(result.fixes)}F [{result.language}]")
            
            if verbose:
                for err in result.errors:
                    print(f"   ❌ L{err.line}: [{err.code}] {err.message}")
                for warn in result.warnings:
                    print(f"   ⚠️  L{warn.line}: [{warn.code}] {warn.message}")
        
        except Exception as e:
            print(f"❌ {file_path}: {e}")
    
    print(f"\n📊 Podsumowanie: {total_errors} errors, {total_warnings} warnings, {total_fixes} fixes")
    return 0 if total_errors == 0 else 1


def fix_all_examples(verbose: bool = False, comment: bool = False) -> int:
    """Fix all files in examples/ directory and save to fixed/ subdirectories."""
    env_examples = os.environ.get('PACTFIX_EXAMPLES_DIR')
    examples_dir = Path(env_examples) if env_examples else Path('examples')
 
    if not examples_dir.exists():
        for parent in Path(__file__).resolve().parents:
            candidate = parent / 'examples'
            if candidate.exists() and candidate.is_dir():
                examples_dir = candidate
                break
     
    if not examples_dir.exists():
        print(f"❌ Nie znaleziono katalogu examples/", file=sys.stderr)
        return 1
    
    print(f"🔧 Pactfix - naprawianie wszystkich plików w {examples_dir}\n")
    
    results = []
    
    for subdir in sorted(examples_dir.iterdir()):
        if not subdir.is_dir():
            continue
        
        for file_path in subdir.iterdir():
            if file_path.is_file() and not file_path.name.startswith('fixed_'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                    
                    result = analyze_code(code, str(file_path))
                    if comment:
                        result.fixed_code = add_fix_comments(result)
                    
                    # Save fixed file
                    fixed_dir = subdir / 'fixed'
                    fixed_dir.mkdir(exist_ok=True)
                    
                    fixed_path = fixed_dir / f"fixed_{file_path.name}"
                    with open(fixed_path, 'w', encoding='utf-8') as f:
                        f.write(result.fixed_code)
                    
                    # Save log
                    log_path = fixed_dir / f"{file_path.stem}_log.json"
                    log_data = {
                        'source': str(file_path),
                        'fixed': str(fixed_path),
                        'language': result.language,
                        'errors': len(result.errors),
                        'warnings': len(result.warnings),
                        'fixes': len(result.fixes),
                        'details': result.to_dict()
                    }
                    with open(log_path, 'w', encoding='utf-8') as f:
                        json.dump(log_data, f, indent=2, ensure_ascii=False)
                    
                    status = "✅" if len(result.errors) == 0 else "❌"
                    print(f"{status} {subdir.name}/{file_path.name}: {len(result.errors)}E {len(result.warnings)}W {len(result.fixes)}F [{result.language}]")
                    
                    if verbose:
                        for err in result.errors:
                            print(f"   ❌ L{err.line}: [{err.code}] {err.message}")
                        for fix in result.fixes:
                            print(f"   🔧 L{fix.line}: {fix.description}")
                    
                    results.append({
                        'file': str(file_path),
                        'language': result.language,
                        'errors': len(result.errors),
                        'warnings': len(result.warnings),
                        'fixes': len(result.fixes)
                    })
                
                except Exception as e:
                    print(f"❌ {file_path}: {e}")
    
    # Summary
    total_errors = sum(r['errors'] for r in results)
    total_warnings = sum(r['warnings'] for r in results)
    total_fixes = sum(r['fixes'] for r in results)
    
    print(f"\n{'='*60}")
    print(f"📊 Podsumowanie: {len(results)} plików")
    print(f"   ❌ Errors:   {total_errors}")
    print(f"   ⚠️  Warnings: {total_warnings}")
    print(f"   🔧 Fixes:    {total_fixes}")
    
    # Save summary
    summary_path = examples_dir / 'fix_summary.json'
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_files': len(results),
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'total_fixes': total_fixes,
            'files': results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Raport zapisany: {summary_path}")
    
    return 0


def init_dockerfiles(output_dir: str) -> int:
    """Create Dockerfiles for all supported languages."""
    output_path = Path(output_dir)
    print(f"🐳 Creating Dockerfiles in {output_path}\n")
    
    try:
        created = create_all_dockerfiles(output_path)
        print(f"\n✅ Created {len(created)} Dockerfiles")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


def setup_sandbox_only(project_path: str, verbose: bool = False) -> int:
    """Setup sandbox without running fixes."""
    path = Path(project_path).resolve()
    
    if not path.exists():
        print(f"❌ Path does not exist: {path}", file=sys.stderr)
        return 1
    
    print(f"🔧 Setting up sandbox for: {path}\n")
    
    sandbox = Sandbox(str(path))
    sandbox.setup()
    
    print(f"\n✅ Sandbox ready in: {sandbox.sandbox_dir}")
    print(f"📋 Language detected: {sandbox.language}")
    print(f"\nTo build and run:")
    print(f"  cd {sandbox.sandbox_dir}")
    print(f"  docker-compose up --build")
    
    return 0


def process_project(project_path: str, comment: bool = False, sandbox: bool = False,
                    run_tests: bool = False, verbose: bool = False) -> int:
    """Process entire project - scan, fix all files, optionally run in sandbox.
    
    Modes:
    - Without --sandbox: Fix files IN PLACE (replace original files)
    - With --sandbox: Copy fixed files to .pactfix/ and run Docker sandbox
    """
    path = Path(project_path).resolve()
    
    if not path.exists():
        print(f"❌ Path does not exist: {path}", file=sys.stderr)
        return 1
    
    mode_str = "🐳 SANDBOX MODE" if sandbox else "📝 IN-PLACE FIX MODE"
    print(f"🔍 Pactfix - scanning project: {path}")
    print(f"   {mode_str}\n")
    
    # Detect project language
    language, stats = detect_project_language(path)
    print(f"📋 Detected project language: {language}")
    if verbose and stats.get('all_scores'):
        print(f"   Scores: {stats['all_scores']}")
    print()
    
    # Find all files to process
    extensions = ['.sh', '.py', '.php', '.js', '.ts', '.sql', '.tf', '.yml', '.yaml', 
                  '.conf', '.go', '.rs', '.java', '.cs', '.rb', '.html', '.css']
    
    files_to_process = []
    for ext in extensions:
        files_to_process.extend(path.rglob(f'*{ext}'))
    
    # Add Dockerfiles and special files
    files_to_process.extend(path.rglob('Dockerfile'))
    files_to_process.extend(path.rglob('Makefile'))
    
    # Filter out hidden directories and common excludes
    exclude_dirs = {'.git', '.pactfix', 'node_modules', '__pycache__', 'venv', '.venv', 
                    'vendor', 'target', 'build', 'dist', '.idea', '.vscode'}
    
    files_to_process = [
        f for f in files_to_process 
        if not any(excl in f.parts for excl in exclude_dirs)
        and f.is_file()
    ]
    
    if not files_to_process:
        print(f"⚠️  No files found to analyze in: {path}")
        return 0
    
    print(f"📁 Found {len(files_to_process)} files to analyze\n")
    
    # Process files
    results = []
    fixed_files = {}
    files_modified = []
    total_errors = 0
    total_warnings = 0
    total_fixes = 0
    
    # Only create .pactfix dir in sandbox mode
    pactfix_dir = path / '.pactfix' if sandbox else None
    
    for file_path in sorted(set(files_to_process)):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
            
            result = analyze_code(code, str(file_path))
            
            if comment and result.fixes:
                result.fixed_code = add_fix_comments(result)
            
            total_errors += len(result.errors)
            total_warnings += len(result.warnings)
            total_fixes += len(result.fixes)
            
            rel_path = file_path.relative_to(path)
            
            # Save fixed file
            if result.fixes:
                if sandbox:
                    # Sandbox mode: save to .pactfix/fixed/
                    fixed_dir = pactfix_dir / 'fixed'
                    fixed_dir.mkdir(parents=True, exist_ok=True)
                    fixed_file_path = fixed_dir / rel_path
                    fixed_file_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(fixed_file_path, 'w', encoding='utf-8') as f:
                        f.write(result.fixed_code)
                    fixed_files[str(rel_path)] = result.fixed_code
                else:
                    # In-place mode: overwrite original file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(result.fixed_code)
                    files_modified.append(str(rel_path))
            
            # Print status
            status = "✅" if len(result.errors) == 0 else "❌"
            
            if result.fixes or result.errors or verbose:
                fix_indicator = " 📝" if result.fixes and not sandbox else ""
                print(f"{status} {rel_path}: {len(result.errors)}E {len(result.warnings)}W {len(result.fixes)}F [{result.language}]{fix_indicator}")
                
                if verbose:
                    for err in result.errors:
                        print(f"   ❌ L{err.line}: [{err.code}] {err.message}")
                    for fix in result.fixes:
                        print(f"   🔧 L{fix.line}: {fix.description}")
            
            results.append({
                'file': str(rel_path),
                'language': result.language,
                'errors': len(result.errors),
                'warnings': len(result.warnings),
                'fixes': len(result.fixes)
            })
            
        except Exception as e:
            if verbose:
                print(f"❌ {file_path}: {e}")
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"📊 Project Summary: {path.name}")
    print(f"   📁 Files analyzed: {len(results)}")
    print(f"   ❌ Errors:   {total_errors}")
    print(f"   ⚠️  Warnings: {total_warnings}")
    print(f"   🔧 Fixes:    {total_fixes}")
    
    if not sandbox and files_modified:
        print(f"\n   � Files modified in place: {len(files_modified)}")
        for f in files_modified:
            print(f"      - {f}")
    
    # Sandbox mode
    if sandbox:
        pactfix_dir.mkdir(parents=True, exist_ok=True)
        
        # Save report
        report_path = pactfix_dir / 'report.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'project_path': str(path),
                'project_language': language,
                'total_files': len(results),
                'total_errors': total_errors,
                'total_warnings': total_warnings,
                'total_fixes': total_fixes,
                'comment_mode': comment,
                'files': results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n   📋 Report saved to: {report_path}")
        
        if fixed_files:
            print(f"   📄 Fixed files saved to: {pactfix_dir / 'fixed'}")
        
        print(f"\n{'='*60}")
        print("🐳 Setting up Docker sandbox...")
        
        sandbox_env = Sandbox(str(path))
        sandbox_env.setup()
        
        if fixed_files:
            print(f"\n📦 Copying {len(fixed_files)} fixed files to sandbox...")
            sandbox_env.copy_fixed_files(fixed_files)
        
        # Build and run
        print(f"\n🔨 Building Docker image for {language}...")
        success, build_output = sandbox_env.build()
        
        if success:
            print(f"\n🚀 Running sandbox...")
            run_success, run_output = sandbox_env.run()
            
            # Save output
            output_path = pactfix_dir / 'sandbox_output.txt'
            with open(output_path, 'w') as f:
                f.write(f"=== BUILD OUTPUT ===\n{build_output}\n\n")
                f.write(f"=== RUN OUTPUT ===\n{run_output}\n")
            
            if run_tests:
                print(f"\n🧪 Running tests...")
                test_success, test_output = sandbox_env.test()
                
                test_report_path = pactfix_dir / 'test_results.txt'
                with open(test_report_path, 'w') as f:
                    f.write(test_output)
                print(f"   📋 Test results saved to: {test_report_path}")
        
        print(f"\n✅ Sandbox ready in: {sandbox_env.sandbox_dir}")
        print(f"\nTo run manually:")
        print(f"  cd {sandbox_env.sandbox_dir}")
        print(f"  docker-compose up --build")
    
    return 0 if total_errors == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
