import yt_dlp
import os
import openai
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def transcribe_audio(audio_file_path):
    """Transcribe audio using OpenAI's Whisper model"""
    try:
        # Check if API key is set
        if not os.environ.get("OPENAI_API_KEY"):
            api_key = input("\nPlease enter your OpenAI API key: ")
            os.environ["OPENAI_API_KEY"] = api_key

        client = openai.OpenAI()
        print("\nTranscribing audio... This may take a while depending on the file size.")

        with open(audio_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=audio_file
            )

        # Save transcript to file
        transcript_path = audio_file_path.replace(Path(audio_file_path).suffix, "_transcript.txt")
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(transcript.text)

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
        print("1. Video only")
        print("2. Audio only")
        print("3. Both video and audio")
        choice = input("Enter your choice (1-3): ")

        # Configure yt-dlp options based on user choice
        ydl_opts = {
            'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
            'progress_hooks': [lambda d: print(f"\rDownloading: {d['_percent_str']} of {d['_total_bytes_str']}", end='') if d['status'] == 'downloading' else None],
        }

        download_type = "content"
        is_audio_download = False

        if choice == "1":  # Video only
            ydl_opts.update({
                'format': 'best',  # Simplified format selection
                'merge_output_format': 'mp4',
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
            })
            download_type = "video"
        elif choice == "2":  # Audio only
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
            download_type = "audio"
            is_audio_download = True
        else:  # Both video and audio (default)
            ydl_opts.update({
                'format': 'best',
                'merge_output_format': 'mp4',
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
                'keepvideo': True,
                'postprocessor_args': [
                    '-acodec', 'mp3', '-vcodec', 'copy'
                ],
            })
            download_type = "video and audio"
            is_audio_download = True

        # Download the content
        print(f"\nFetching {download_type} information...")
        downloaded_file_path = None

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
            ydl.download([url])
            downloaded_file_path = filename

        print(f"\n{download_type.capitalize()} download completed!")

        # Ask if user wants to transcribe audio if audio was downloaded
        if is_audio_download and os.path.exists(downloaded_file_path):
            transcribe_choice = input("\nWould you like to transcribe the audio using OpenAI's Whisper model? (yes/no): ").lower()
            if transcribe_choice in ["yes", "y"]:
                transcribe_audio(downloaded_file_path)

    except Exception as e:
        print("An error occurred:", str(e))

if __name__ == "__main__":
    print("YouTube Video & Audio Downloader with Transcription")
    print("===============================================")
    download_video()