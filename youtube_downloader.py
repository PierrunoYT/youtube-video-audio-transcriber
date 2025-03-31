import yt_dlp
import os
import time
import openai
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def transcribe_audio(audio_file_path):
    """Transcribe audio using OpenAI's Whisper large-v3 model and save as markdown"""
    try:
        # Check if API key is set
        if not os.environ.get("OPENAI_API_KEY"):
            api_key = input("\nPlease enter your OpenAI API key: ")
            os.environ["OPENAI_API_KEY"] = api_key

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
            paragraphs = transcript.text.split('. ')
            for i, paragraph in enumerate(paragraphs):
                if i < len(paragraphs) - 1:
                    f.write(f"{paragraph}.\n\n")
                else:
                    f.write(f"{paragraph}")

        print(f"\nTranscription completed and saved to: {transcript_path}")
        return transcript_path
    except Exception as e:
        print(f"\nError during transcription: {str(e)}")
        return None


def download_video():
    try:
        # Get the YouTube video URL from user
        url = input("Please enter the YouTube video URL: ")

        # Get download path from user or environment variable
        default_path = os.environ.get("DEFAULT_DOWNLOAD_PATH") or os.getcwd()
        download_path = input(f"\nEnter download path (press Enter for {default_path}): ")
        if not download_path:
            download_path = default_path

        # Ask user what to download
        print("\nWhat would you like to download?")
        print("1. Video only (MP4)")
        print("2. Audio only (MP3)")
        print("3. Video and separate audio file (no merging)")
        print("4. List available formats first")
        choice = input("Enter your choice (1-4): ")

        # If user wants to list formats first
        if choice == "4":
            print("\nListing available formats...")
            with yt_dlp.YoutubeDL({'listformats': True}) as ydl:
                ydl.extract_info(url, download=False)

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
                    'progress_hooks': [lambda d: print(f"\rDownloading: {d['_percent_str']} of {d['_total_bytes_str']}", end='') if d['status'] == 'downloading' else None],
                    'verbose': True,  # Add verbose output for debugging
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
                print(f"\nFetching {download_type} information...")
                downloaded_file_path = None

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    print(f"\nTitle: {info['title']}")
                    print(f"Duration: {info['duration']} seconds")
                    print(f"Views: {info['view_count']}")

                    # Get the output filename
                    filename = ydl.prepare_filename(info)

                    print(f"\nStarting {download_type} download...")
                    print(f"File will be saved as: {filename}")
                    ydl.download([url])
                    downloaded_file_path = filename

                    # Verify file exists
                    if os.path.exists(downloaded_file_path):
                        print(f"\n{download_type.capitalize()} download completed successfully!")
                        print(f"File saved at: {downloaded_file_path}")
                        file_size = os.path.getsize(downloaded_file_path) / (1024 * 1024)  # Size in MB
                        print(f"File size: {file_size:.2f} MB")
                    else:
                        print(f"\nWARNING: Expected file {downloaded_file_path} not found after download.")
                        # Try to find any recently created media files
                        print("Searching for recently downloaded files...")
                        base_dir = download_path or os.getcwd()
                        for file in os.listdir(base_dir):
                            full_path = os.path.join(base_dir, file)
                            if os.path.isfile(full_path) and os.path.getmtime(full_path) > time.time() - 60:  # Files created in the last minute
                                if file.endswith(('.mp4', '.mp3', '.m4a', '.webm')):
                                    print(f"Found possible download: {full_path}")
                                    downloaded_file_path = full_path
                                    break

                        # If still not found, try with different extension
                        if not downloaded_file_path or not os.path.exists(downloaded_file_path):
                            possible_extensions = ['.mp4', '.mp3', '.m4a', '.webm', '.mkv']
                            base_filename = os.path.splitext(filename)[0]
                            for ext in possible_extensions:
                                test_path = base_filename + ext
                                if os.path.exists(test_path):
                                    print(f"Found file with different extension: {test_path}")
                                    downloaded_file_path = test_path
                                    break

                if not downloaded_file_path or not os.path.exists(downloaded_file_path):
                    print("\nNo valid downloaded file found. Cannot proceed with transcription.")
                    return

                print(f"\n{download_type.capitalize()} download completed!")

                # Ask if user wants to transcribe audio if audio was downloaded
                if is_audio_download and os.path.exists(downloaded_file_path):
                    print("\n" + "=" * 60)
                    print("TRANSCRIPTION OPTION")
                    print("=" * 60)
                    print("The downloaded file contains audio that can be transcribed.")
                    print("OpenAI's Whisper model will be used for transcription.")
                    print("The transcription will be saved as a markdown file.")
                    transcribe_choice = input("\nWould you like to transcribe the audio using OpenAI's Whisper model? (Press Enter for yes/n for no): ").lower()
                    if transcribe_choice in ["", "yes", "y"]:
                        transcript_path = transcribe_audio(downloaded_file_path)
                        if transcript_path and os.path.exists(transcript_path):
                            print(f"\nTranscription saved successfully to: {transcript_path}")
                            print("You can open this markdown file in any text editor or markdown viewer.")
                    else:
                        print("\nTranscription skipped.")

                return  # Exit the function after custom format download

        # Configure yt-dlp options based on user choice
        ydl_opts = {
            'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
            'progress_hooks': [lambda d: print(f"\rDownloading: {d['_percent_str']} of {d['_total_bytes_str']}", end='') if d['status'] == 'downloading' else None],
            'verbose': True,  # Add verbose output for debugging
            'no_warnings': False,
            'ignoreerrors': False,
        }

        download_type = "content"
        is_audio_download = False

        if choice == "1":  # Video only (MP4)
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]/best[ext=mp4]/best',  # Best video quality in MP4 format
                'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
                'verbose': True,
                'progress_hooks': [lambda d: print(f"\rDownloading: {d['_percent_str']} of {d['_total_bytes_str']}", end='') if d['status'] == 'downloading' else None],
            }
            download_type = "video"
        elif choice == "2":  # Audio only (MP3)
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
                'verbose': True,
                'progress_hooks': [lambda d: print(f"\rDownloading: {d['_percent_str']} of {d['_total_bytes_str']}", end='') if d['status'] == 'downloading' else None],
            }
            download_type = "audio"
            is_audio_download = True
        else:  # Video and separate audio file (no merging)
            # First download video
            print("\nDownloading video file first...")
            video_opts = {
                'format': 'bestvideo[ext=mp4]/best[ext=mp4]/best',  # Best video quality in MP4 format
                'outtmpl': os.path.join(download_path, '%(title)s_video.%(ext)s'),
                'verbose': True,
                'progress_hooks': [lambda d: print(f"\rDownloading video: {d['_percent_str']} of {d['_total_bytes_str']}", end='') if d['status'] == 'downloading' else None],
            }

            with yt_dlp.YoutubeDL(video_opts) as ydl:
                ydl.download([url])

            # Then download audio
            print("\nDownloading audio file second...")
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.join(download_path, '%(title)s_audio.%(ext)s'),
                'verbose': True,
                'progress_hooks': [lambda d: print(f"\rDownloading audio: {d['_percent_str']} of {d['_total_bytes_str']}", end='') if d['status'] == 'downloading' else None],
            }
            download_type = "video and separate audio"
            is_audio_download = True

        print(f"\nSelected download type: {download_type}")
        print(f"Audio will be available for transcription: {is_audio_download}")

        # Download the content
        print(f"\nFetching {download_type} information...")
        downloaded_file_path = None

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                print(f"\nTitle: {info['title']}")
                print(f"Duration: {info['duration']} seconds")
                print(f"Views: {info['view_count']}")

                # Get the output filename
                filename = ydl.prepare_filename(info)
                if choice == "2":  # Audio only
                    # Change extension to mp3 for audio downloads
                    filename = os.path.splitext(filename)[0] + ".mp3"

                print(f"\nStarting {download_type} download...")
                print(f"File will be saved as: {filename}")

                # Perform the actual download
                print("\nDownloading... (this may take a while)")
                ydl.download([url])
                downloaded_file_path = filename

                # Verify file exists
                if os.path.exists(downloaded_file_path):
                    print(f"\n{download_type.capitalize()} download completed successfully!")
                    print(f"File saved at: {downloaded_file_path}")
                    file_size = os.path.getsize(downloaded_file_path) / (1024 * 1024)  # Size in MB
                    print(f"File size: {file_size:.2f} MB")
                else:
                    print(f"\nWARNING: Expected file {downloaded_file_path} not found after download.")
                    # Try to find any recently created media files
                    print("Searching for recently downloaded files...")
                    base_dir = download_path or os.getcwd()
                    for file in os.listdir(base_dir):
                        full_path = os.path.join(base_dir, file)
                        if os.path.isfile(full_path) and os.path.getmtime(full_path) > time.time() - 60:  # Files created in the last minute
                            if file.endswith(('.mp4', '.mp3', '.m4a', '.webm')):
                                print(f"Found possible download: {full_path}")
                                downloaded_file_path = full_path
                                break

                    # If still not found, try with different extension
                    if not downloaded_file_path or not os.path.exists(downloaded_file_path):
                        possible_extensions = ['.mp4', '.mp3', '.m4a', '.webm', '.mkv']
                        base_filename = os.path.splitext(filename)[0]
                        for ext in possible_extensions:
                            test_path = base_filename + ext
                            if os.path.exists(test_path):
                                print(f"Found file with different extension: {test_path}")
                                downloaded_file_path = test_path
                                break
        except Exception as e:
            print(f"\nError during download: {str(e)}")
            return

        if not downloaded_file_path or not os.path.exists(downloaded_file_path):
            print("\nNo valid downloaded file found. Cannot proceed with transcription.")
            return

        print(f"\n{download_type.capitalize()} download completed!")

        # Ask if user wants to transcribe audio if audio was downloaded
        if is_audio_download and os.path.exists(downloaded_file_path):
            print("\n" + "=" * 60)
            print("TRANSCRIPTION OPTION")
            print("=" * 60)
            print("The downloaded file contains audio that can be transcribed.")
            print("OpenAI's Whisper model will be used for transcription.")
            print("The transcription will be saved as a markdown file.")
            transcribe_choice = input("\nWould you like to transcribe the audio using OpenAI's Whisper model? (Press Enter for yes/n for no): ").lower()
            if transcribe_choice in ["", "yes", "y"]:
                transcript_path = transcribe_audio(downloaded_file_path)
                if transcript_path and os.path.exists(transcript_path):
                    print(f"\nTranscription saved successfully to: {transcript_path}")
                    print("You can open this markdown file in any text editor or markdown viewer.")
            else:
                print("\nTranscription skipped.")

    except Exception as e:
        error_message = str(e)
        print("\nAn error occurred:", error_message)

        if "Requested format is not available" in error_message:
            print("\nTry using option 2 (Audio only) which often has better compatibility.")
            print("Or you can try again with a different video.")

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
    download_video()