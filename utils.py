"""
Utility functions for the YouTube downloader application.
Includes URL validation, file handling, and error handling.
"""
import os
import time
from urllib.parse import urlparse
from getpass import getpass
from pathlib import Path
from config import MEDIA_EXTENSIONS

def validate_url(url):
    """Validate if the URL is a proper YouTube URL"""
    try:
        parsed = urlparse(url)
        if parsed.netloc not in ['www.youtube.com', 'youtube.com', 'youtu.be']:
            return False

        if parsed.netloc == 'youtu.be' and not parsed.path:
            return False

        if parsed.netloc in ['www.youtube.com', 'youtube.com'] and not parsed.path.startswith('/watch'):
            if not (parsed.path.startswith('/shorts/') or parsed.path.startswith('/playlist')):
                return False

        return True
    except:
        return False

def get_api_key_securely(api_type="openai"):
    """Get API key securely without displaying on console

    Args:
        api_type (str): Type of API key to get ("openai" or "gemini")
    """
    if api_type.lower() == "openai":
        from config import get_openai_api_key

        api_key = get_openai_api_key()
        if api_key:
            return api_key

        print("\nOpenAI API key not found in environment variables.")
        api_key = getpass("Please enter your OpenAI API key (input will be hidden): ")
        os.environ["OPENAI_API_KEY"] = api_key
        return api_key

    elif api_type.lower() == "gemini":
        from config import get_gemini_api_key

        api_key = get_gemini_api_key()
        if api_key:
            return api_key

        print("\nGoogle Gemini API key not found in environment variables.")
        api_key = getpass("Please enter your Google Gemini API key (input will be hidden): ")
        os.environ["GEMINI_API_KEY"] = api_key
        return api_key

    else:
        raise ValueError(f"Unknown API type: {api_type}. Use 'openai' or 'gemini'.")

def find_downloaded_file(expected_path, download_path):
    """Find downloaded file even if the expected path doesn't exist"""
    if os.path.exists(expected_path):
        return expected_path

    # Try to find any recently created media files
    print("Searching for recently downloaded files...")
    base_dir = download_path or os.getcwd()

    # First check for recently modified files (last 60 seconds)
    for file in os.listdir(base_dir):
        full_path = os.path.join(base_dir, file)
        if (os.path.isfile(full_path) and
            os.path.getmtime(full_path) > time.time() - 60 and
            file.endswith(tuple(MEDIA_EXTENSIONS))):
            print(f"Found possible download: {full_path}")
            return full_path

    # If still not found, try with different extension
    base_filename = os.path.splitext(expected_path)[0]
    for ext in MEDIA_EXTENSIONS:
        test_path = base_filename + ext
        if os.path.exists(test_path):
            print(f"Found file with different extension: {test_path}")
            return test_path

    return None

def handle_download_error(error):
    """Handle yt-dlp download errors with helpful messages"""
    error_message = str(error)
    print("\nDownload Error:", error_message)

    if "Requested format is not available" in error_message:
        print("\nTroubleshooting tips:")
        print("- Try using option 2 (Audio only) which often has better compatibility")
        print("- Use option 4 to list available formats first, then choose a specific format")
        print("- For audio-only downloads, try format codes like 140 (m4a), 251 (webm), or 250 (webm)")
        print("- Try downloading from a different video")
    elif "Private video" in error_message or "Sign in to confirm your age" in error_message:
        print("\nTroubleshooting tips:")
        print("- This video is private or age-restricted and cannot be downloaded")
        print("- Try downloading a different video")
    elif "This video is unavailable" in error_message:
        print("\nTroubleshooting tips:")
        print("- The video may have been removed or is not available in your country")
        print("- Check if the video URL is correct")
        print("- Try downloading a different video")
    elif "HTTP Error 429" in error_message:
        print("\nTroubleshooting tips:")
        print("- YouTube is rate-limiting downloads from your IP address")
        print("- Wait a while before trying again")
        print("- Try downloading fewer videos in a short period")
    else:
        print("\nTroubleshooting tips:")
        print("- Check your internet connection")
        print("- Verify that the YouTube URL is valid and accessible in your browser")
        print("- Try using a different download option")
        print("- Update yt-dlp to the latest version with: pip install -U yt-dlp")

    print("\nFor technical support, please provide the following error details:")
    print(f"Error: {error_message}")

def handle_filesystem_error(error):
    """Handle filesystem errors"""
    print(f"\nFile system error: {str(error)}")
    print("\nTroubleshooting tips:")
    print("- Check if the download directory exists and you have permission to write to it")
    print("- Try specifying a different download location")
    print("- Make sure you have sufficient disk space")

    print("\nFor technical support, please provide the following error details:")
    print(f"Error: {str(error)}")

def handle_generic_error(error):
    """Handle generic errors"""
    error_message = str(error)
    print("\nAn unexpected error occurred:", error_message)

    print("\nTroubleshooting tips:")
    print("- Try restarting the application")
    print("- Check if FFmpeg is installed correctly (required for audio extraction)")
    print("- Update all dependencies with: pip install -r requirements.txt")

    print("\nFor technical support, please provide the following error details:")
    print(f"Error: {error_message}")
