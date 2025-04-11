"""
Main module for the YouTube downloader application.
Handles user interaction and orchestrates the download and transcription process.
"""

import os
import yt_dlp
from pathlib import Path
from config import load_config
from utils import validate_url, handle_download_error, handle_filesystem_error, handle_generic_error
from downloader import list_formats, download_media, download_video_audio_separately
from transcriber import handle_transcription_option

def _get_user_input(prompt, default=None):
    """Get user input with an optional default value."""
    if default:
        return input(f"{prompt} (press Enter for {default}): ") or default
    return input(prompt)

def _validate_and_create_dir(path):
    """Validate if a directory exists, and create it if the user agrees."""
    
    dir_path = Path(path)
    if not dir_path.exists():
        create_dir = _get_user_input(f"Directory {dir_path} doesn't exist. Create it? (y/n): ").lower()
        if create_dir == 'y':
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"Created directory: {dir_path}")
                return True
            except Exception as e:
                print(f"Error creating directory: {str(e)}")
                return False
        else:
            print("Download cancelled.")
            return False
    return True

def _handle_custom_format_download(url, download_path):
    """Handle downloading with a custom format code."""

    format_code = _get_user_input("\nEnter the format code (e.g., 137+140, 22, etc.): ")
    extract_audio = _get_user_input("Do you want to extract audio as MP3? (y/n): ").lower() in ['y', 'yes']

    download_dir = Path(download_path)
    ydl_opts = {
        'format': format_code,
        'outtmpl': str(download_dir / '%(title)s.%(ext)s'),
        'verbose': False,
    }

    if extract_audio:
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
        is_audio_download = True
    else:
        is_audio_download = any(code in format_code for code in ['140', '139', '249', '250', '251', 'bestaudio']) or 'audio' in format_code.lower()

    download_type = "custom format" + ("/audio extraction" if extract_audio else "")

    print(f"\nSelected download type: {download_type}")
    print(f"Audio will be available for transcription: {is_audio_download}")

    downloaded_file_path = download_media(url, ydl_opts, download_type, download_path)

    if downloaded_file_path and is_audio_download:
        file_path = Path(downloaded_file_path)
        if file_path.exists():
            handle_transcription_option(downloaded_file_path)

def _handle_standard_download(url, download_path, choice):
    """Handle standard download options (video, audio, both)."""

    download_type = "content"
    is_audio_download = False
    downloaded_file_path = None
    download_dir = Path(download_path)

    if choice == "1":  # Video only (MP4)
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]/best[ext=mp4]/best',
            'outtmpl': str(download_dir / '%(title)s.%(ext)s'),
            'verbose': False,
        }
        download_type = "video"
        downloaded_file_path = download_media(url, ydl_opts, download_type, download_path)

    elif choice == "2":  # Audio only (MP3)
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': str(download_dir / '%(title)s.%(ext)s'),
            'verbose': False,
        }
        download_type = "audio"
        is_audio_download = True
        downloaded_file_path = download_media(url, ydl_opts, download_type, download_path)

    elif choice == "3":  # Video and separate audio file (no merging)
        video_path, audio_path = download_video_audio_separately(url, download_path)
        if audio_path:
            audio_file = Path(audio_path)
            if audio_file.exists():
                downloaded_file_path = audio_path
                is_audio_download = True
        elif video_path:
            downloaded_file_path = video_path
        download_type = "video and separate audio"

    if downloaded_file_path and is_audio_download:
        file_path = Path(downloaded_file_path)
        if file_path.exists():
            handle_transcription_option(downloaded_file_path)

def handle_download():
    """Main function to handle the download process."""

    try:
        url = _get_user_input("Please enter the YouTube video URL: ")
        if not validate_url(url):
            print(f"\nError: '{url}' does not appear to be a valid YouTube URL.")
            print("Valid YouTube URLs should be in one of these formats:")
            print("- www.youtube.com")
            print("- m.youtube.com")
            print("- youtube.com")
            return

        config = load_config()  # Load configuration
        download_path = _get_user_input("\nEnter download path", config["default_download_path"])

        if not _validate_and_create_dir(download_path):
            return

        print("\nWhat would you like to download?")
        print("1. Video only (MP4)")
        print("2. Audio only (MP3)")
        print("3. Video and separate audio file (no merging)")
        print("4. List available formats first")
        choice = _get_user_input("Enter your choice (1-4): ")

        if choice == "4":
            if not list_formats(url):
                print("Failed to list formats. Continuing with basic options...")

            print("\nNow that you've seen the available formats, what would you like to download?")
            print("1. Video only (MP4)")
            print("2. Audio only (MP3)")
            print("3. Video and separate audio file (no merging)")
            print("5. Specify custom format code")
            choice = _get_user_input("Enter your choice (1-3, 5): ")

            if choice == "5":
                _handle_custom_format_download(url, download_path)
            else:
                _handle_standard_download(url, download_path, choice)
        else:
            _handle_standard_download(url, download_path, choice)

    except yt_dlp.utils.DownloadError as e:
        handle_download_error(e)
    except (FileNotFoundError, PermissionError) as e:
        handle_filesystem_error(e)
    except Exception as e:
        handle_generic_error(e)

def main():
    """Main entry point of the application."""

    print("YouTube Video & Audio Downloader with AI Transcription & Analysis")
    print("======================================================")
    print("Features:")
    print("- Download videos in MP4 format")
    print("- Extract audio as separate MP3 files")
    print("- Download both video and audio as separate files (no merging)")
    print("- Transcribe audio using OpenAI's Whisper model or Google's Gemini API")
    print("- Summarize transcripts using Google's Gemini API")
    print("- Interactive chat with transcript or audio content using Gemini")
    print("- Save transcriptions and summaries as text files")
    print("======================================================")
    handle_download()

if __name__ == "__main__":
    main()