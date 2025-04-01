import yt_dlp
import os
import time
import openai
import re
import threading
import queue
from getpass import getpass
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables from .env file
load_dotenv()

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

def get_api_key_securely():
    """Get OpenAI API key securely without displaying on console"""
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ.get("OPENAI_API_KEY")
        
    print("\nAPI key not found in environment variables.")
    api_key = getpass("Please enter your OpenAI API key (input will be hidden): ")
    os.environ["OPENAI_API_KEY"] = api_key
    return api_key

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
            file.endswith(('.mp4', '.mp3', '.m4a', '.webm', '.mkv'))):
            print(f"Found possible download: {full_path}")
            return full_path
    
    # If still not found, try with different extension
    possible_extensions = ['.mp4', '.mp3', '.m4a', '.webm', '.mkv']
    base_filename = os.path.splitext(expected_path)[0]
    for ext in possible_extensions:
        test_path = base_filename + ext
        if os.path.exists(test_path):
            print(f"Found file with different extension: {test_path}")
            return test_path
            
    return None

def transcribe_audio(audio_file_path):
    """Transcribe audio using OpenAI's Whisper model and save as markdown"""
    try:
        # Check if API key is set (securely)
        get_api_key_securely()

        client = openai.OpenAI()
        print("\nTranscribing audio using OpenAI's Whisper model...")
        print("This may take a while depending on the file size.")

        # Check if file exists and is readable
        if not os.path.exists(audio_file_path):
            print(f"Error: File {audio_file_path} does not exist.")
            return None

        file_size_mb = os.path.getsize(audio_file_path) / (1024 * 1024)
        print(f"File size: {file_size_mb:.2f} MB")

        # OpenAI has a 25MB file size limit
        if file_size_mb > 25:
            print("Warning: File is larger than 25MB, which is OpenAI's limit. Transcription may fail.")
            proceed = input("Do you want to proceed anyway? (y/n): ").lower()
            if proceed != 'y':
                print("Transcription cancelled.")
                return None

        with open(audio_file_path, "rb") as audio_file:
            print("Sending file to OpenAI for transcription...")
            transcript = client.audio.transcriptions.create(
                model="whisper-1",  # Use the correct model name for the API
                file=audio_file,
                response_format="text"  # Ensure we get plain text
            )

        # Get video title from filename
        video_title = Path(audio_file_path).stem

        # Save transcript to markdown file
        transcript_path = audio_file_path.replace(Path(audio_file_path).suffix, "_transcript.md")
        with open(transcript_path, "w", encoding="utf-8") as f:
            # Format as markdown
            f.write(f"# Transcript: {video_title}\n\n")

            # Format paragraphs for better readability
            paragraphs = transcript.split('. ')
            for i, paragraph in enumerate(paragraphs):
                if i < len(paragraphs) - 1:
                    f.write(f"{paragraph}.\n\n")
                else:
                    f.write(f"{paragraph}")

        print(f"\nTranscription completed and saved to: {transcript_path}")
        return transcript_path
    except openai.APIConnectionError:
        print("\nError during transcription: Unable to connect to OpenAI API")
        print("Troubleshooting tips:")
        print("- Check your internet connection")
        print("- Verify the OpenAI API service is available: https://status.openai.com")
        return None
    except openai.APIError as e:
        print(f"\nError during transcription: OpenAI API error - {str(e)}")
        print("Troubleshooting tips:")
        print("- This could be a temporary issue with OpenAI's service")
        print("- Try again in a few minutes")
        return None
    except openai.RateLimitError:
        print("\nError during transcription: OpenAI API rate limit exceeded")
        print("Troubleshooting tips:")
        print("- You've reached your API usage limit")
        print("- Wait and try again later or check your API usage limits in your OpenAI account")
        return None
    except openai.AuthenticationError:
        print("\nError during transcription: Invalid OpenAI API key")
        print("Troubleshooting tips:")
        print("- Check that you've entered your API key correctly")
        print("- Verify your API key is still valid in your OpenAI account")
        print("- Create a new API key if needed: https://platform.openai.com/api-keys")
        return None
    except (FileNotFoundError, PermissionError) as e:
        print(f"\nError during transcription: File system error - {str(e)}")
        print("Troubleshooting tips:")
        print("- Check if the file exists and you have permission to access it")
        print("- Try downloading the file again")
        return None
    except Exception as e:
        print(f"\nError during transcription: {str(e)}")
        print("Troubleshooting tips:")
        print("- Try downloading the audio file again")
        print("- Make sure the audio file is in a supported format (MP3, M4A, WAV, etc.)")
        print("- Check that the audio file is not corrupted")
        return None

def list_formats(url):
    """List available formats for a video"""
    try:
        print("\nListing available formats...")
        formats_queue = queue.Queue()
        
        def _list_formats():
            try:
                with yt_dlp.YoutubeDL({'listformats': True, 'quiet': True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                    formats_queue.put(("success", info))
            except Exception as e:
                formats_queue.put(("error", str(e)))
        
        # Run format listing in a separate thread to avoid blocking
        format_thread = threading.Thread(target=_list_formats)
        format_thread.daemon = True
        format_thread.start()
        
        # Show a loading indicator
        print("Fetching formats", end="")
        for _ in range(30):  # Timeout after ~3 seconds
            if not format_thread.is_alive():
                break
            print(".", end="", flush=True)
            time.sleep(0.1)
        print()
        
        if format_thread.is_alive():
            print("Format listing is taking longer than expected, please wait...")
            format_thread.join(10)  # Wait up to 10 more seconds
        
        if not formats_queue.empty():
            status, result = formats_queue.get()
            if status == "error":
                print(f"Error listing formats: {result}")
                return False
            return True
        else:
            print("Timed out while listing formats")
            return False
    except Exception as e:
        print(f"Error listing formats: {str(e)}")
        return False

def download_media(url, ydl_opts, download_type, download_path):
    """Download media with progress monitoring"""
    try:
        downloaded_file_path = None
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            print(f"\nTitle: {info.get('title', 'Unknown title')}")
            print(f"Duration: {info.get('duration', 'Unknown')} seconds")
            print(f"Views: {info.get('view_count', 'Unknown')}")

            # Get the output filename
            filename = ydl.prepare_filename(info)
            if download_type == "audio":
                # Change extension to mp3 for audio downloads
                filename = os.path.splitext(filename)[0] + ".mp3"

            print(f"\nStarting {download_type} download...")
            print(f"File will be saved as: {filename}")

            # Run download in a separate thread to allow for progress updates
            download_queue = queue.Queue()
            def _download():
                try:
                    ydl.download([url])
                    download_queue.put(("success", None))
                except Exception as e:
                    download_queue.put(("error", str(e)))
            
            download_thread = threading.Thread(target=_download)
            download_thread.daemon = True
            download_thread.start()
            
            # Wait for download to complete
            dots = 0
            print("Downloading", end="")
            while download_thread.is_alive():
                print(".", end="", flush=True)
                dots = (dots + 1) % 4
                time.sleep(0.5)
            print()
            
            if not download_queue.empty():
                status, error = download_queue.get()
                if status == "error":
                    raise Exception(error)
            
            # Verify download was successful
            downloaded_file_path = find_downloaded_file(filename, download_path)
            
            if downloaded_file_path and os.path.exists(downloaded_file_path):
                print(f"\n{download_type.capitalize()} download completed successfully!")
                print(f"File saved at: {downloaded_file_path}")
                file_size = os.path.getsize(downloaded_file_path) / (1024 * 1024)  # Size in MB
                print(f"File size: {file_size:.2f} MB")
            else:
                print(f"\nWARNING: Expected file not found after download.")
            
            return downloaded_file_path
            
    except Exception as e:
        print(f"\nError during download: {str(e)}")
        return None

def download_video_audio_separately(url, download_path):
    """Download video and audio as separate files"""
    # First download video
    print("\nDownloading video file first...")
    video_opts = {
        'format': 'bestvideo[ext=mp4]/best[ext=mp4]/best',  # Best video quality in MP4 format
        'outtmpl': os.path.join(download_path, '%(title)s_video.%(ext)s'),
        'verbose': False,
    }
    
    video_path = download_media(url, video_opts, "video", download_path)
    
    # Then download audio
    print("\nDownloading audio file second...")
    audio_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(download_path, '%(title)s_audio.%(ext)s'),
        'verbose': False,
    }
    
    audio_path = download_media(url, audio_opts, "audio", download_path)
    
    return video_path, audio_path

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
        default_path = os.environ.get("DEFAULT_DOWNLOAD_PATH") or os.getcwd()
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

def handle_transcription_option(audio_file_path):
    """Handle the transcription option for downloaded audio"""
    print("\n" + "=" * 60)
    print("TRANSCRIPTION OPTION")
    print("=" * 60)
    print("The downloaded file contains audio that can be transcribed.")
    print("OpenAI's Whisper model will be used for transcription.")
    print("The transcription will be saved as a markdown file.")
    transcribe_choice = input("\nWould you like to transcribe the audio using OpenAI's Whisper model? (Press Enter for yes/n for no): ").lower()
    if transcribe_choice in ["", "yes", "y"]:
        transcript_path = transcribe_audio(audio_file_path)
        if transcript_path and os.path.exists(transcript_path):
            print(f"\nTranscription saved successfully to: {transcript_path}")
            print("You can open this markdown file in any text editor or markdown viewer.")
    else:
        print("\nTranscription skipped.")

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

if __name__ == "__main__":
    print("YouTube Video & Audio Downloader with Whisper Transcription")
    print("======================================================")
    print("Features:")
    print("- Download videos in MP4 format")
    print("- Extract audio as separate MP3 files")
    print("- Download both video and audio as separate files (no merging)")
    print("- Transcribe audio using OpenAI's Whisper model")
    print("- Save transcriptions as markdown files")
    print("======================================================")
    handle_download()