"""Pactfix CLI - Command line interface for code analysis."""

import argparse
import json
import sys
import os
from pathlib import Path
from datetime import datetime

from .analyzer import analyze_code, detect_language, SUPPORTED_LANGUAGES


def main():
    parser = argparse.ArgumentParser(
        prog='pactfix',
        description='Multi-language code and config file analyzer and fixer'
    )
    
    parser.add_argument('input', nargs='?', help='Input file to analyze')
    parser.add_argument('-o', '--output', help='Output file for fixed code')
    parser.add_argument('-l', '--language', choices=SUPPORTED_LANGUAGES, help='Force language detection')
    parser.add_argument('--log-file', help='Output JSON log file')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--batch', help='Process all files in directory')
    parser.add_argument('--fix-all', action='store_true', help='Fix all files in examples/')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--version', action='version', version='pactfix 1.0.0')
    
    args = parser.parse_args()
    
    if args.fix_all:
        return fix_all_examples(args.verbose)
    
    if args.batch:
        return process_batch(args.batch, args.verbose)
    
    if args.input == '-':
        return process_stdin(args.output, args.language, args.log_file, args.verbose, args.json)

    if not args.input:
        if not sys.stdin.isatty():
            return process_stdin(args.output, args.language, args.log_file, args.verbose, args.json)
        parser.print_help()
        return 1
    
    return process_file(args.input, args.output, args.language, args.log_file, args.verbose, args.json)


def process_file(input_path: str, output_path: str = None, language: str = None, 
                 log_file: str = None, verbose: bool = False, as_json: bool = False) -> int:
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


def process_stdin(output_path: str = None, language: str = None,
                  log_file: str = None, verbose: bool = False, as_json: bool = False) -> int:
    """Process code from stdin."""
    try:
        code = sys.stdin.read()
    except Exception as e:
        print(f"❌ Błąd odczytu stdin: {e}", file=sys.stderr)
        return 1

    filename_hint = output_path or '<stdin>'
    result = analyze_code(code, filename_hint, language)

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


def fix_all_examples(verbose: bool = False) -> int:
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


if __name__ == '__main__':
    sys.exit(main())


def fix_all_examples(verbose: bool = False) -> int:
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


if __name__ == '__main__':
    sys.exit(main())
