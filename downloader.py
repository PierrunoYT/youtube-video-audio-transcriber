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
import json
from pathlib import Path
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
    except json.JSONDecodeError as e:
        # Handle JSON parsing error specifically
        logging.error(f"JSON parsing error during download: {str(e)}")
        download_queue.put(("error", f"Error parsing YouTube response. Try another format or video."))
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
                file_path = Path(filename)
                filename = str(file_path.with_suffix(".mp3"))

            print(f"\nStarting {download_type} download...")
            print(f"File will be saved as: {filename}")

            download_queue = queue.Queue()
            download_thread = threading.Thread(target=_download_with_progress, args=(ydl, url, download_queue))
            download_thread.daemon = True
            download_thread.start()

            # Wait for download to complete and show progress
            print("Downloading", end="")
            timeout = 300  # 5 minutes timeout
            elapsed = 0
            interval = 0.5
            while download_thread.is_alive() and elapsed < timeout:
                print(".", end="", flush=True)
                time.sleep(interval)
                elapsed += interval
            print()
            
            if download_thread.is_alive():
                # If thread is still running after timeout
                print("\nDownload is taking too long, you may want to cancel and try another format.")
                
            try:
                status, error = download_queue.get(timeout=5)  # 5 second timeout for getting result
                if status == "error":
                    raise DownloadError(error)
            except queue.Empty:
                # Handle case where queue is empty (no result returned)
                raise DownloadError("Download failed: No response from download thread")

            downloaded_file_path = find_downloaded_file(filename, download_path)
            _log_and_print_download_status(download_type, downloaded_file_path)

            return downloaded_file_path

    except yt_dlp.utils.DownloadError as e:
        raise e  # yt-dlp specific errors are handled by the caller
    except Exception as e:
        logging.exception("Error during media download")
        print(f"\nAn unexpected error occurred during download: {str(e)}")
        from utils import GenericError
        raise GenericError(f"Download failed: {str(e)}")  # Raise a more specific exception

def _log_and_print_download_status(download_type, downloaded_file_path):
    """Log and print download completion status."""

    if downloaded_file_path:
        file_path = Path(downloaded_file_path)
        if file_path.exists():
            file_size = file_path.stat().st_size / (1024 * 1024)  # Size in MB
            print(f"\n{download_type.capitalize()} download completed successfully!")
            print(f"File saved at: {file_path} (Size: {file_size:.2f} MB)")
            logging.info(f"Download successful: {file_path} (Size: {file_size:.2f} MB)")
            return
    
    logging.warning(f"Expected file not found after download")
    print(f"\nWARNING: Expected file not found after download.")

def download_video_audio_separately(url, download_path):
    """Download video and audio as separate files."""

    try:
        from pathlib import Path
        download_dir = Path(download_path)
        
        video_opts = {
            'format': 'bestvideo[ext=mp4]/best[ext=mp4]/best',
            'outtmpl': str(download_dir / '%(title)s_video.%(ext)s'),
            'verbose': False,
            'ignoreerrors': True,  # Skip unavailable videos
            'no_warnings': False,  # Show warnings
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
            'outtmpl': str(download_dir / '%(title)s_audio.%(ext)s'),
            'verbose': False,
            'ignoreerrors': True,  # Skip unavailable videos
            'no_warnings': False,  # Show warnings
        }
        print("\nDownloading audio file second...")
        audio_path = download_media(url, audio_opts, "audio", download_path)

        return video_path, audio_path

    except DownloadError as e:
        logging.error(f"Download error during separate download: {str(e)}")
        raise e
    except Exception as e:
        logging.exception("Error downloading video/audio separately")
        print(f"\nAn unexpected error occurred during separate download: {str(e)}")
        from utils import GenericError
        raise GenericError(f"Separate download failed: {str(e)}")