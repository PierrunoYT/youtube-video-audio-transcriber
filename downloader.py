"""
Downloader module for the YouTube downloader application.
Handles downloading videos and audio from YouTube.
"""
import os
import time
import yt_dlp
import threading
import queue
from utils import find_downloaded_file

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
