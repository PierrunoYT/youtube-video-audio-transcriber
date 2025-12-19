"""
Utility functions for the YouTube downloader application.
Includes URL validation, API key handling, file operations, and error handling.
"""

import os
import time
import logging
from urllib.parse import urlparse
from getpass import getpass
from pathlib import Path
from config import load_config, ConfigurationError
# Removed magic library dependency

# Initialize logging (you can customize this)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration
config = load_config()
MEDIA_EXTENSIONS = config["media_extensions"]


class DownloadError(Exception):
    """Custom exception for download errors"""
    pass


class FilesystemError(Exception):
    """Custom exception for filesystem errors"""
    pass


class APIError(Exception):
    """Custom exception for API related errors"""
    pass


class GenericError(Exception):
    """Custom exception for generic errors"""
    pass


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


def validate_url(url):
    """Validate if the URL is a proper YouTube URL"""

    try:
        parsed = urlparse(url)
        if parsed.netloc not in ['www.youtube.com', 'm.youtube.com', 'youtube.com', 'youtu.be']:
            return False

        if parsed.netloc in ['www.youtube.com', 'm.youtube.com', 'youtube.com'] and not parsed.path.startswith('/watch'):
            if not (parsed.path.startswith('/shorts/') or parsed.path.startswith('/playlist')):
                return False

        if parsed.netloc == 'youtu.be' and not parsed.path.startswith('/'):
            return False

        return True
    except ValueError:
        return False
    except Exception as e:
        logging.error(f"URL validation error: {e}")
        return False


def get_api_key_securely(api_type="openai"):
    """Get API key securely without displaying on console

    Args:
        api_type (str): Type of API key to get ("openai" or "gemini")
    """

    if api_type.lower() == "openai":
        api_key = config["openai_api_key"]
        if api_key:
            return api_key

        print("\nOpenAI API key not found in environment variables.")
        api_key = getpass("Please enter your OpenAI API key (input will be hidden): ")
        os.environ["OPENAI_API_KEY"] = api_key
        logging.info("OpenAI API key obtained from user input.")
        return api_key

    elif api_type.lower() == "gemini":
        api_key = config["gemini_api_key"]
        if api_key:
            return api_key

        print("\nGoogle Gemini API key not found in environment variables.")
        api_key = getpass("Please enter your Google Gemini API key (input will be hidden): ")
        os.environ["GEMINI_API_KEY"] = api_key
        logging.info("Gemini API key obtained from user input.")
        return api_key
    else:
        raise ValueError(f"Unknown API type: {api_type}. Use 'openai' or 'gemini'.")


def find_downloaded_file(expected_path, download_path):
    """Find downloaded file even if the expected path doesn't exist.
    
    Args:
        expected_path (str): The expected path to the downloaded file
        download_path (str): The directory where files are downloaded
        
    Returns:
        str: Path to the found file, or None if not found
    """

    expected_file = Path(expected_path)
    base_dir = Path(download_path or os.getcwd())

    # First, check if the exact expected path exists
    if expected_file.exists():
        logging.info(f"Found expected file: {expected_file}")
        return str(expected_file)

    # Try to find a file with the same stem and a supported extension
    for ext in MEDIA_EXTENSIONS:
        potential_file = base_dir / (expected_file.stem + ext)
        if potential_file.exists():
            logging.info(f"Found file with matching stem: {potential_file}")
            return str(potential_file)

    # Look for files with partial name matches (more specific than just recent files)
    # This helps avoid picking up unrelated files
    stem_parts = expected_file.stem.split('_')
    if len(stem_parts) > 1:
        # Try matching on first significant part of the filename
        search_pattern = stem_parts[0]
        matching_files = []
        current_time = time.time()
        
        for file in base_dir.glob('*'):
            if file.is_file() and file.suffix.lower() in MEDIA_EXTENSIONS:
                # Check if filename starts with the same base and was recently modified
                if file.stem.startswith(search_pattern):
                    modified_time = file.stat().st_mtime
                    if current_time - modified_time < 60:  # Only 1 minute to reduce false positives
                        matching_files.append((file, modified_time))
        
        if matching_files:
            most_recent_match = max(matching_files, key=lambda item: item[1])[0]
            logging.warning(f"Found approximate match (recent file with similar name): {most_recent_match}")
            return str(most_recent_match)

    # Last resort: look for ANY recently modified media file (with strict time limit)
    recent_files = []
    current_time = time.time()
    for file in base_dir.glob('*'):
        if file.is_file() and file.suffix.lower() in MEDIA_EXTENSIONS:
            modified_time = file.stat().st_mtime
            if current_time - modified_time < 30:  # Only 30 seconds to minimize false positives
                recent_files.append((file, modified_time))

    if recent_files:
        most_recent_file = max(recent_files, key=lambda item: item[1])[0]
        logging.warning(f"Found most recent file (fallback): {most_recent_file}. This may not be the correct file.")
        print(f"\nWarning: Could not find exact file, using most recent download: {most_recent_file.name}")
        return str(most_recent_file)

    logging.warning(f"No downloaded file found matching {expected_file} in {base_dir}")
    return None


def handle_download_error(error):
    """Handle yt-dlp download errors with helpful messages"""

    error_message = str(error)
    logging.error(f"Download error: {error_message}")
    print("\nDownload Error:", error_message)

    error_messages = {
        "Requested format is not available": [
            "Troubleshooting tips:",
            "- Try using option 2 (Audio only) which often has better compatibility",
            "- Use option 4 to list available formats first, then choose a specific format",
            "- For audio-only downloads, try format codes like 140 (m4a), 251 (webm), or 250 (webm)",
            "- Try downloading from a different video"
        ],
        "Private video": [
            "Troubleshooting tips:",
            "- This video is private or age-restricted and cannot be downloaded",
            "- Try downloading a different video"
        ],
        "This video is unavailable": [
            "Troubleshooting tips:",
            "- The video may have been removed or is not available in your country",
            "- Check if the video URL is correct",
            "- Try downloading a different video"
        ],
        "HTTP Error 429": [
            "Troubleshooting tips:",
            "- YouTube is rate-limiting downloads from your IP address",
            "- Wait a while before trying again",
            "- Try downloading fewer videos in a short period"
        ],
        "generic": [
            "Troubleshooting tips:",
            "- Check your internet connection",
            "- Verify that the YouTube URL is valid and accessible in your browser",
            "- Try using a different download option",
            "- Update yt-dlp to the latest version with: pip install -U yt-dlp"
        ]
    }

    for key, tips in error_messages.items():
        if key in error_message:
            print("\n".join([""] + tips))
            raise DownloadError(error_message)

    print("\n".join([""] + error_messages["generic"]))  # Print generic tips
    raise DownloadError(error_message)


def handle_filesystem_error(error):
    """Handle filesystem errors"""

    error_message = str(error)
    logging.error(f"Filesystem error: {error_message}")
    print(f"\nFile system error: {error_message}")
    print("\nTroubleshooting tips:")
    print("- Check if the download directory exists and you have permission to write to it")
    print("- Try specifying a different download location")
    print("- Make sure you have sufficient disk space")
    raise FilesystemError(error_message)


def handle_generic_error(error):
    """Handle generic errors"""

    error_message = str(error)
    logging.error(f"Generic error: {error_message}")
    print("\nAn unexpected error occurred:", error_message)
    print("\nTroubleshooting tips:")
    print("- Try restarting the application")
    print("- Check if FFmpeg is installed correctly (required for audio extraction)")
    print("- Update all dependencies with: pip install -r requirements.txt")
    raise GenericError(error_message)


def handle_api_error(error, service_name="API"):
    """
    Standardized API error handler for all services.
    
    Args:
        error (Exception): The error that occurred
        service_name (str): Name of the service (e.g., "OpenAI", "Gemini")
    """
    error_message = str(error)
    error_type = type(error).__name__
    
    logging.error(f"{service_name} Error ({error_type}): {error_message}")
    print(f"\n{service_name} Error ({error_type}):", error_message)
    
    # Common troubleshooting tips
    print(f"\nTroubleshooting tips for {service_name}:")
    print("- Check your internet connection")
    print("- Verify your API key is valid and has necessary permissions")
    print("- Check if you've exceeded your API usage limits")
    print("- Try again later if the service is temporarily unavailable")


def handle_validation_error(error, context=""):
    """
    Standardized validation error handler.
    
    Args:
        error (Exception): The validation error
        context (str): Additional context about what was being validated
    """
    error_message = str(error)
    logging.error(f"Validation Error{' in ' + context if context else ''}: {error_message}")
    print(f"\nValidation Error{' in ' + context if context else ''}:", error_message)
    
    print("\nPlease check:")
    print("- Input format and requirements")
    print("- File paths and permissions")
    print("- Configuration settings")