"""
pactfix Code Analyzer - Command Line Interface
"""

import argparse
import json
import sys
import logging
from pathlib import Path
from datetime import datetime

from .analyzer import analyze_file, analyze_code


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger('pactfix')


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog='pactfix',
        description='pactfix Code Analyzer - Analyze and fix code issues'
    )
    
    parser.add_argument(
        'input',
        help='Input file to analyze'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output file for fixed code (default: <input>_fixed.<ext>)'
    )
    
    parser.add_argument(
        '-l', '--language',
        choices=['bash', 'python', 'php', 'javascript', 'nodejs'],
        help='Force language detection (auto-detected by default)'
    )
    
    parser.add_argument(
        '--log-file',
        help='Write logs to file'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    
    parser.add_argument(
        '--no-fix',
        action='store_true',
        help='Only analyze, do not write fixed file'
    )
    
    args = parser.parse_args()
    
    logger = setup_logging(args.verbose)
    
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {args.input}")
        sys.exit(1)
    
    if args.output:
        output_path = args.output
    elif not args.no_fix:
        stem = input_path.stem
        suffix = input_path.suffix
        output_path = str(input_path.parent / f"{stem}_fixed{suffix}")
    else:
        output_path = None
    
    logger.info(f"📂 Analyzing: {args.input}")
    logger.info(f"🔍 Language: {args.language or 'auto-detect'}")
    
    try:
        result = analyze_file(
            str(input_path),
            output_path if not args.no_fix else None,
            args.language
        )
        
        logger.info(f"✅ Language detected: {result.language}")
        logger.info(f"❌ Errors: {len(result.errors)}")
        logger.info(f"⚠️  Warnings: {len(result.warnings)}")
        logger.info(f"🔧 Fixes applied: {len(result.fixes)}")
        
        for error in result.errors:
            logger.error(f"  Line {error.line}: [{error.code}] {error.message}")
        
        for warning in result.warnings:
            logger.warning(f"  Line {warning.line}: [{warning.code}] {warning.message}")
        
        for fix in result.fixes:
            logger.info(f"  Line {fix.line}: {fix.message}")
            logger.debug(f"    Before: {fix.before}")
            logger.debug(f"    After:  {fix.after}")
        
        if output_path and not args.no_fix:
            logger.info(f"💾 Fixed code written to: {output_path}")
        
        if args.log_file:
            log_data = {
                "timestamp": result.timestamp,
                "input_file": str(input_path),
                "output_file": output_path,
                "language": result.language,
                "errors_count": len(result.errors),
                "warnings_count": len(result.warnings),
                "fixes_count": len(result.fixes),
                "errors": [{"line": e.line, "code": e.code, "message": e.message} for e in result.errors],
                "warnings": [{"line": w.line, "code": w.code, "message": w.message} for w in result.warnings],
                "fixes": [{"line": f.line, "message": f.message, "before": f.before, "after": f.after} for f in result.fixes]
            }
            
            log_path = Path(args.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(json.dumps(log_data, indent=2, ensure_ascii=False), encoding='utf-8')
            logger.info(f"📝 Log written to: {args.log_file}")
        
        if args.json:
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        
        exit_code = 1 if result.errors else 0
        sys.exit(exit_code)
        
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
