# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running Commands
- Run tests: `python test_gemini.py` or `python test_download.py`
- Run single test: `python -c "from test_gemini import test_simple_generation; test_simple_generation()"`
- Run application: `python main.py`

## Code Style
- Docstrings: Use triple double-quotes with descriptive summaries
- Imports: Group standard library imports first, then external packages, then local modules
- Error handling: Use custom exception classes (APIError, DownloadError, FilesystemError) with contextual messages
- Logging: Use the logging module with appropriate severity levels
- Functions: Use snake_case with descriptive names and type hints where possible
- Use try/except blocks with specific exceptions
- Use consistent 4-space indentation
- Follow PEP 8 guidelines