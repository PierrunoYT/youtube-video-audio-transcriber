"""
Configuration module for the YouTube downloader application.
Handles environment variables and application settings.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Gemini model constants
GEMINI_MODEL_FLASH = 'gemini-2.0-flash'           # Faster model for transcription and basic operations
GEMINI_MODEL_PRO = 'gemini-2.5-pro-preview-03-25' # Advanced model for chatting and complex reasoning


class ConfigurationError(Exception):
    """Custom exception for configuration-related errors"""
    pass


def validate_config():
    """
    Validate all configuration settings and environment variables.
    
    Raises:
        ConfigurationError: If configuration is invalid
    """
    errors = []
    warnings = []
    
    # Validate API keys format (don't test connectivity here, that's done when needed)
    openai_key = get_openai_api_key()
    if openai_key and len(openai_key) < 20:
        errors.append("OpenAI API key appears to be too short")
    
    gemini_key = get_gemini_api_key()
    if gemini_key and len(gemini_key) < 20:
        errors.append("Gemini API key appears to be too short")
    
    if not openai_key and not gemini_key:
        warnings.append("No API keys configured - transcription features will not be available")
    
    # Validate default download path
    default_path = get_default_download_path()
    if default_path:
        try:
            path_obj = Path(default_path)
            if not path_obj.exists():
                warnings.append(f"Default download path does not exist: {default_path}")
            elif not os.access(default_path, os.W_OK):
                errors.append(f"Default download path is not writable: {default_path}")
        except Exception as e:
            errors.append(f"Invalid default download path: {default_path} - {str(e)}")
    
    # Log warnings
    for warning in warnings:
        logging.warning(f"Configuration warning: {warning}")
    
    # Raise errors if any
    if errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors)
        raise ConfigurationError(error_msg)
    
    return True


def load_config():
    """Load configuration settings from environment variables with validation."""
    
    config = {
        "openai_api_key": get_openai_api_key(),
        "gemini_api_key": get_gemini_api_key(),
        "default_download_path": get_default_download_path(),
        "media_extensions": ['.mp4', '.mp3', '.m4a', '.webm', '.mkv']
    }
    
    # Validate configuration
    try:
        validate_config()
    except ConfigurationError as e:
        logging.error(f"Configuration error: {e}")
        print(f"\nConfiguration Error: {e}")
        print("\nPlease check your environment variables and configuration.")
    
    return config

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