"""
Main module for the YouTube downloader application.
Handles user interaction and orchestrates the download and transcription process.
"""
import os
import yt_dlp
from config import get_default_download_path
from utils import validate_url, handle_download_error, handle_filesystem_error, handle_generic_error
from downloader import list_formats, download_media, download_video_audio_separately
from transcriber import handle_transcription_option

def handle_download():
    try:
        # Get the YouTube video URL from user
        url = input("Please enter the YouTube video URL: ")

        # Validate URL format
        if not validate_url(url):
            print(f"\nError: '{url}' does not appear to be a valid YouTube URL.")
            print("Valid YouTube URLs should be in one of these formats:")
            print("- https://www.youtube.com/watch?v=VIDEO_ID")
            print("- https://youtu.be/VIDEO_ID")
            print("- https://www.youtube.com/shorts/VIDEO_ID")
            return

        # Get download path from user or environment variable
        default_path = get_default_download_path()
        download_path = input(f"\nEnter download path (press Enter for {default_path}): ")
        if not download_path:
            download_path = default_path

        # Verify the download path exists
        if not os.path.exists(download_path):
            create_dir = input(f"Directory {download_path} doesn't exist. Create it? (y/n): ").lower()
            if create_dir == 'y':
                try:
                    os.makedirs(download_path, exist_ok=True)
                    print(f"Created directory: {download_path}")
                except Exception as e:
                    print(f"Error creating directory: {str(e)}")
                    return
            else:
                print("Download cancelled.")
                return

        # Ask user what to download
        print("\nWhat would you like to download?")
        print("1. Video only (MP4)")
        print("2. Audio only (MP3)")
        print("3. Video and separate audio file (no merging)")
        print("4. List available formats first")
        choice = input("Enter your choice (1-4): ")

        # If user wants to list formats first
        if choice == "4":
            if not list_formats(url):
                print("Failed to list formats. Continuing with basic options...")

            print("\nNow that you've seen the available formats, what would you like to download?")
            print("1. Video only (MP4)")
            print("2. Audio only (MP3)")
            print("3. Video and separate audio file (no merging)")
            print("5. Specify custom format code")
            choice = input("Enter your choice (1-3, 5): ")

            # If user wants to specify a custom format
            if choice == "5":
                format_code = input("\nEnter the format code (e.g., 137+140, 22, etc.): ")
                extract_audio = input("Do you want to extract audio as MP3? (y/n): ").lower() in ['y', 'yes']

                ydl_opts = {
                    'format': format_code,
                    'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
                    'verbose': False,
                }

                # Add audio extraction if requested
                if extract_audio:
                    ydl_opts['postprocessors'] = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }]
                    is_audio_download = True
                else:
                    # Check if the format includes audio
                    is_audio_download = any(code in format_code for code in ['140', '139', '249', '250', '251', 'bestaudio']) or 'audio' in format_code.lower()

                download_type = "custom format" + ("/audio extraction" if extract_audio else "")

                print(f"\nSelected download type: {download_type}")
                print(f"Audio will be available for transcription: {is_audio_download}")

                # Download the content with custom format
                downloaded_file_path = download_media(url, ydl_opts, download_type, download_path)

                if not downloaded_file_path:
                    print("\nNo valid downloaded file found. Cannot proceed with transcription.")
                    return

                # Ask if user wants to transcribe audio if audio was downloaded
                if is_audio_download and os.path.exists(downloaded_file_path):
                    handle_transcription_option(downloaded_file_path)

                return

        # Configure yt-dlp options based on user choice
        download_type = "content"
        is_audio_download = False
        downloaded_file_path = None

        if choice == "1":  # Video only (MP4)
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]/best[ext=mp4]/best',  # Best video quality in MP4 format
                'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
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
                'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
                'verbose': False,
            }
            download_type = "audio"
            is_audio_download = True
            downloaded_file_path = download_media(url, ydl_opts, download_type, download_path)

        elif choice == "3":  # Video and separate audio file (no merging)
            video_path, audio_path = download_video_audio_separately(url, download_path)

            if audio_path and os.path.exists(audio_path):
                downloaded_file_path = audio_path
                is_audio_download = True
            elif video_path:
                downloaded_file_path = video_path

            download_type = "video and separate audio"

        if not downloaded_file_path or not os.path.exists(downloaded_file_path):
            print("\nNo valid downloaded file found. Cannot proceed with transcription.")
            return

        print(f"\n{download_type.capitalize()} download completed!")

        # Ask if user wants to transcribe audio if audio was downloaded
        if is_audio_download and os.path.exists(downloaded_file_path):
            handle_transcription_option(downloaded_file_path)

    except yt_dlp.utils.DownloadError as e:
        handle_download_error(e)
    except (FileNotFoundError, PermissionError) as e:
        handle_filesystem_error(e)
    except Exception as e:
        handle_generic_error(e)

def main():
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
