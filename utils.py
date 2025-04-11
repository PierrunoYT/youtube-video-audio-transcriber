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
from config import load_config
import magic  # For more reliable MIME type detection (install python-magic)

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
    """Find downloaded file even if the expected path doesn't exist"""

    expected_file = Path(expected_path)
    base_dir = Path(download_path or os.getcwd())

    if expected_file.exists():
        logging.info(f"Found expected file: {expected_path}")
        return str(expected_file)

    # Try to find a file with the same stem and a supported extension
    for ext in MEDIA_EXTENSIONS:
        potential_file = base_dir / (expected_file.stem + ext)
        if potential_file.exists():
            logging.info(f"Found file with matching stem: {potential_file}")
            return str(potential_file)

    # If still not found, try to find the most recently modified file
    # within a reasonable timeframe (e.g., last 5 minutes).
    recent_files = []
    for file in base_dir.glob('*'):
        if file.is_file() and file.suffix.lower() in MEDIA_EXTENSIONS:
            modified_time = file.stat().st_mtime
            if time.time() - modified_time < 300:  # 5 minutes
                recent_files.append((file, modified_time))

    if recent_files:
        most_recent_file = max(recent_files, key=lambda item: item[1])[0]
        logging.info(f"Found most recent file: {most_recent_file}")
        return str(most_recent_file)

    logging.warning(f"No downloaded file found matching {expected_path} in {download_path}")
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