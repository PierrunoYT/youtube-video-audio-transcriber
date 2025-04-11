"""
Test script for the download functionality.
This script runs a simple download test without requiring interactive input.
"""

import sys
import yt_dlp
from pathlib import Path
from config import load_config
from utils import validate_url, handle_download_error, handle_filesystem_error, handle_generic_error

def test_download():
    """Test downloading functionality with a predefined URL."""
    
    # A popular test video that's often used for video downloader testing
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    print(f"\nTesting URL validation for: {test_url}")
    if not validate_url(test_url):
        print(f"\nError: '{test_url}' does not appear to be a valid YouTube URL.")
        return False
    
    print("\nURL is valid. Now testing format listing capabilities...")
    
    try:
        with yt_dlp.YoutubeDL({'listformats': True, 'quiet': False}) as ydl:
            info = ydl.extract_info(test_url, download=False)
            title = info.get('title', 'Unknown title')
            print(f"\nSuccessfully retrieved info for video: {title}")
            return True
    except yt_dlp.utils.DownloadError as e:
        print(f"\nDownload Error: {str(e)}")
        return False
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        return False

def main():
    """Run download test."""
    print("=" * 50)
    print("YOUTUBE DOWNLOADER TEST")
    print("=" * 50)
    
    success = test_download()
    
    if success:
        print("\n✅ Download functionality test completed successfully!")
    else:
        print("\n❌ Download functionality test failed.")
    
    print("\nNote: This test doesn't actually download the video, it just verifies")
    print("that the application can connect to YouTube and retrieve video information.")

if __name__ == "__main__":
    main()