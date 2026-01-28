"""pactfix Code Analyzer - Python CLI Package"""

__version__ = "1.0.0"

from .analyzer import analyze_file, analyze_code
from .cli import main

__all__ = ["analyze_file", "analyze_code", "main"]
