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
import signal
import sys
from pathlib import Path
from utils import find_downloaded_file, DownloadError
from utils import logging  # Use the logging configuration from utils

# Default timeout configurations
DEFAULT_CONNECT_TIMEOUT = 30  # seconds
DEFAULT_DOWNLOAD_TIMEOUT = 600  # 10 minutes
DEFAULT_FORMAT_LIST_TIMEOUT = 60  # 1 minute

def list_formats(url, timeout=DEFAULT_FORMAT_LIST_TIMEOUT):
    """List available formats for a video with timeout handling."""

    def _list_formats(formats_queue, timeout_seconds):
        """Helper function to list formats in a thread with timeout."""
        try:
            # Configure yt-dlp with timeout settings
            ydl_opts = {
                'listformats': True, 
                'quiet': True,
                'socket_timeout': timeout_seconds,
                'retries': 2,
                'fragment_retries': 2,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                formats_queue.put(("success", info))
        except Exception as e:
            formats_queue.put(("error", str(e)))

    try:
        print(f"\nListing available formats (timeout: {timeout}s)...")
        formats_queue = queue.Queue()
        format_thread = threading.Thread(target=_list_formats, args=(formats_queue, timeout))
        format_thread.daemon = True
        format_thread.start()

        # Show a loading indicator with progress
        print("Fetching formats", end="")
        start_time = time.time()
        while format_thread.is_alive():
            elapsed = time.time() - start_time
            if elapsed > timeout:
                print(f"\n\nTimeout after {timeout} seconds while fetching formats.")
                print("This may be due to network issues or the video being unavailable.")
                return False
            
            print(".", end="", flush=True)
            time.sleep(0.5)
        print()

        # Get the result with a short timeout
        try:
            status, result = formats_queue.get(timeout=5)
            if status == "error":
                logging.error(f"Error listing formats: {result}")
                print(f"Error listing formats: {result}")
                return False
            return True
        except queue.Empty:
            print("Timeout waiting for format listing result.")
            return False

    except Exception as e:
        logging.exception("Error during format listing")
        print(f"Error listing formats: {str(e)}")
        return False

def _download_with_progress(ydl, url, download_queue, timeout_seconds):
    """Helper function to download media in a thread with timeout handling."""
    try:
        # Set up signal handler for timeout (Unix-like systems)
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Download timed out after {timeout_seconds} seconds")
        
        # Only set signal handler on Unix-like systems
        if hasattr(signal, 'SIGALRM'):
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout_seconds)
        
        try:
            ydl.download([url])
            download_queue.put(("success", None))
        finally:
            # Clean up signal handler
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)  # Cancel the alarm
                signal.signal(signal.SIGALRM, old_handler)  # Restore old handler
                
    except TimeoutError as e:
        download_queue.put(("timeout", str(e)))
    except json.JSONDecodeError as e:
        # Handle JSON parsing error specifically
        logging.error(f"JSON parsing error during download: {str(e)}")
        download_queue.put(("error", f"Error parsing YouTube response. Try another format or video."))
    except Exception as e:
        download_queue.put(("error", str(e)))

def download_media(url, ydl_opts, download_type, download_path, 
                  connect_timeout=DEFAULT_CONNECT_TIMEOUT, 
                  download_timeout=DEFAULT_DOWNLOAD_TIMEOUT):
    """Download media with comprehensive timeout handling and progress monitoring."""

    try:
        # Add timeout configurations to yt-dlp options
        enhanced_opts = ydl_opts.copy()
        enhanced_opts.update({
            'socket_timeout': connect_timeout,
            'retries': 3,
            'fragment_retries': 3,
            'retry_sleep_functions': {
                'http': lambda n: min(2 ** n, 30),  # Exponential backoff, max 30s
                'fragment': lambda n: min(2 ** n, 10),  # Exponential backoff, max 10s
            }
        })

        with yt_dlp.YoutubeDL(enhanced_opts) as ydl:
            print(f"Fetching video information (timeout: {connect_timeout}s)...")
            
            # Get video info with timeout
            info_start = time.time()
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as e:
                if time.time() - info_start > connect_timeout:
                    raise DownloadError(f"Timeout while fetching video information after {connect_timeout}s")
                raise e
                
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

            print(f"\nStarting {download_type} download (timeout: {download_timeout}s)...")
            print(f"File will be saved as: {filename}")

            download_queue = queue.Queue()
            download_thread = threading.Thread(
                target=_download_with_progress, 
                args=(ydl, url, download_queue, download_timeout)
            )
            download_thread.daemon = True
            download_thread.start()

            # Monitor download progress with timeout
            print("Downloading", end="")
            start_time = time.time()
            interval = 1.0
            last_dot_time = start_time
            
            while download_thread.is_alive():
                current_time = time.time()
                elapsed = current_time - start_time
                
                # Check for overall timeout
                if elapsed > download_timeout:
                    print(f"\n\nDownload timed out after {download_timeout} seconds.")
                    print("This may be due to:")
                    print("- Slow internet connection")
                    print("- Large file size")
                    print("- Network issues")
                    print("- Server problems")
                    raise DownloadError(f"Download timeout after {download_timeout} seconds")
                
                # Show progress dots
                if current_time - last_dot_time >= interval:
                    print(".", end="", flush=True)
                    last_dot_time = current_time
                
                time.sleep(0.1)
            print()
            
            # Get download result with timeout
            try:
                status, error = download_queue.get(timeout=10)
                if status == "timeout":
                    raise DownloadError(f"Download operation timed out: {error}")
                elif status == "error":
                    raise DownloadError(error)
            except queue.Empty:
                raise DownloadError("Download failed: No response from download thread")

            downloaded_file_path = find_downloaded_file(filename, download_path)
            _log_and_print_download_status(download_type, downloaded_file_path)

            return downloaded_file_path

    except yt_dlp.utils.DownloadError as e:
        # Handle yt-dlp specific errors
        error_msg = str(e)
        if "timeout" in error_msg.lower():
            raise DownloadError(f"Network timeout during download: {error_msg}")
        raise e
    except TimeoutError as e:
        raise DownloadError(f"Operation timed out: {str(e)}")
    except Exception as e:
        logging.exception("Error during media download")
        print(f"\nAn unexpected error occurred during download: {str(e)}")
        from utils import GenericError
        raise GenericError(f"Download failed: {str(e)}")

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

def download_video_audio_separately(url, download_path, 
                                   connect_timeout=DEFAULT_CONNECT_TIMEOUT,
                                   download_timeout=DEFAULT_DOWNLOAD_TIMEOUT):
    """Download video and audio as separate files with timeout handling."""

    try:
        from pathlib import Path
        download_dir = Path(download_path)
        
        video_opts = {
            'format': 'bestvideo[ext=mp4]/best[ext=mp4]/best',
            'outtmpl': str(download_dir / '%(title)s_video.%(ext)s'),
            'verbose': False,
            'ignoreerrors': True,
            'no_warnings': False,
        }
        print("\nDownloading video file first...")
        video_path = download_media(url, video_opts, "video", download_path, 
                                  connect_timeout, download_timeout)

        audio_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': str(download_dir / '%(title)s_audio.%(ext)s'),
            'verbose': False,
            'ignoreerrors': True,
            'no_warnings': False,
        }
        print("\nDownloading audio file second...")
        audio_path = download_media(url, audio_opts, "audio", download_path,
                                  connect_timeout, download_timeout)

        return video_path, audio_path

    except DownloadError as e:
        logging.error(f"Download error during separate download: {str(e)}")
        raise e
    except Exception as e:
        logging.exception("Error downloading video/audio separately")
        print(f"\nAn unexpected error occurred during separate download: {str(e)}")
        from utils import GenericError
        raise GenericError(f"Separate download failed: {str(e)}")