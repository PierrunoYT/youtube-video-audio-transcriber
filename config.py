"""
Configuration module for the YouTube downloader application.
Handles environment variables and application settings.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Gemini model constants
GEMINI_MODEL_FLASH = 'gemini-2.0-flash'           # Faster model for transcription and basic operations
GEMINI_MODEL_PRO = 'gemini-2.5-pro-preview-03-25' # Advanced model for chatting and complex reasoning

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