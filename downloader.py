"""
Downloader module for the YouTube downloader application.
Handles downloading videos and audio from YouTube.
"""

import os
import time
import yt_dlp
import threading
import queue
import logging
from utils import find_downloaded_file, DownloadError
from utils import logging  # Use the logging configuration from utils

def list_formats(url):
    """List available formats for a video."""

    def _list_formats(formats_queue):
        """Helper function to list formats in a thread."""
        try:
            with yt_dlp.YoutubeDL({'listformats': True, 'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                formats_queue.put(("success", info))
        except Exception as e:
            formats_queue.put(("error", str(e)))

    try:
        print("\nListing available formats...")
        formats_queue = queue.Queue()
        format_thread = threading.Thread(target=_list_formats, args=(formats_queue,))
        format_thread.daemon = True
        format_thread.start()

        # Show a loading indicator with a timeout
        print("Fetching formats", end="")
        for _ in range(30):  # Timeout after ~3 seconds
            if not format_thread.is_alive():
                break
            print(".", end="", flush=True)
            time.sleep(0.1)
        print()

        format_thread.join(10)  # Wait up to 10 more seconds

        status, result = formats_queue.get()
        if status == "error":
            logging.error(f"Error listing formats: {result}")
            print(f"Error listing formats: {result}")
            return False
        return True

    except Exception as e:
        logging.exception("Error during format listing")
        print(f"Error listing formats: {str(e)}")
        return False

def _download_with_progress(ydl, url, download_queue):
    """Helper function to download media in a thread."""
    try:
        ydl.download([url])
        download_queue.put(("success", None))
    except Exception as e:
        download_queue.put(("error", str(e)))

def download_media(url, ydl_opts, download_type, download_path):
    """Download media with progress monitoring."""

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown title')
            duration = info.get('duration', 'Unknown')
            view_count = info.get('view_count', 'Unknown')

            print(f"\nTitle: {title}")
            print(f"Duration: {duration} seconds")
            print(f"Views: {view_count}")

            # Log video information
            logging.info(f"Downloading: {title}, Duration: {duration}s, Views: {view_count}")

            filename = ydl.prepare_filename(info)
            if download_type == "audio":
                filename = os.path.splitext(filename)[0] + ".mp3"

            print(f"\nStarting {download_type} download...")
            print(f"File will be saved as: {filename}")

            download_queue = queue.Queue()
            download_thread = threading.Thread(target=_download_with_progress, args=(ydl, url, download_queue))
            download_thread.daemon = True
            download_thread.start()

            # Wait for download to complete and show progress
            print("Downloading", end="")
            while download_thread.is_alive():
                print(".", end="", flush=True)
                time.sleep(0.5)
            print()

            status, error = download_queue.get()
            if status == "error":
                raise DownloadError(error)

            downloaded_file_path = find_downloaded_file(filename, download_path)
            _log_and_print_download_status(download_type, downloaded_file_path)

            return downloaded_file_path

    except yt_dlp.utils.DownloadError as e:
        raise e  # yt-dlp specific errors are handled by the caller
    except Exception as e:
        logging.exception("Error during media download")
        print(f"\nAn unexpected error occurred during download: {str(e)}")
        raise  # Re-raise the exception

def _log_and_print_download_status(download_type, downloaded_file_path):
    """Log and print download completion status."""

    if downloaded_file_path and os.path.exists(downloaded_file_path):
        file_size = os.path.getsize(downloaded_file_path) / (1024 * 1024)  # Size in MB
        print(f"\n{download_type.capitalize()} download completed successfully!")
        print(f"File saved at: {downloaded_file_path} (Size: {file_size:.2f} MB)")
        logging.info(f"Download successful: {downloaded_file_path} (Size: {file_size:.2f} MB)")
    else:
        logging.warning(f"Expected file not found after download")
        print(f"\nWARNING: Expected file not found after download.")

def download_video_audio_separately(url, download_path):
    """Download video and audio as separate files."""

    try:
        video_opts = {
            'format': 'bestvideo[ext=mp4]/best[ext=mp4]/best',
            'outtmpl': os.path.join(download_path, '%(title)s_video.%(ext)s'),
            'verbose': False,
        }
        print("\nDownloading video file first...")
        video_path = download_media(url, video_opts, "video", download_path)

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
        print("\nDownloading audio file second...")
        audio_path = download_media(url, audio_opts, "audio", download_path)

        return video_path, audio_path

    except DownloadError as e:
        raise e
    except Exception as e:
        logging.exception("Error downloading video/audio separately")
        print(f"\nAn unexpected error occurred during separate download: {str(e)}")
        raise