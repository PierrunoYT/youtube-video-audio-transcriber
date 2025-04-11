"""
This file has been split into multiple modules for better organization.
Please use main.py as the entry point for the application.

The code has been reorganized into the following files:
- main.py - Entry point and user interface
- downloader.py - Functions for downloading videos and audio
- transcriber.py - Functions for transcribing audio
- utils.py - Utility functions for URL validation and error handling
- config.py - Configuration and environment variable handling
"""

if __name__ == "__main__":
    print("This file has been deprecated. Please use main.py instead.")
    print("Running main.py for you...")
    try:
        import main
        main.main()
    except ImportError:
        print("Error: Could not import main.py. Please make sure it exists in the same directory.")
