"""
Configuration module for the YouTube downloader application.
Handles environment variables and application settings.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def load_config():
    """Load configuration settings from environment variables."""

    return {
        "openai_api_key": get_openai_api_key(),
        "gemini_api_key": get_gemini_api_key(),
        "default_download_path": get_default_download_path(),
        "media_extensions": ['.mp4', '.mp3', '.m4a', '.webm', '.mkv']
    }

# API Keys
def get_openai_api_key():
    """Get OpenAI API key from environment variables"""
    return os.environ.get("OPENAI_API_KEY")

def get_gemini_api_key():
    """Get Google Gemini API key from environment variables"""
    return os.environ.get("GEMINI_API_KEY")

# Default paths
def get_default_download_path():
    """Get default download path from environment variables or use current directory"""
    return os.environ.get("DEFAULT_DOWNLOAD_PATH") or os.getcwd()