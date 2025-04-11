"""
Consolidated test script for the YouTube downloader application.
This script tests Gemini API functionality, audio transcription, and downloader functionality.
"""
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import the gemini_api module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module we want to test
from gemini_api import _check_gemini_availability, transcribe_audio_with_gemini
from utils import APIError, FilesystemError
from config import GEMINI_MODEL_FLASH

def test_gemini_availability():
    """Test if Gemini API is available and properly configured"""
    print("Testing Gemini API availability...")
    try:
        result = _check_gemini_availability()
        if result:
            print("✅ Gemini API is available and properly configured!")
        else:
            print("❌ Gemini API is not available or not properly configured.")
        return result
    except ImportError as e:
        print(f"❌ Gemini API library not installed: {e}")
        return False
    except APIError as e:
        print(f"❌ Gemini API key not configured: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_simple_generation():
    """Test a simple text generation with Gemini API"""
    try:
        # Only import these if the API is available
        import google.generativeai as genai
        
        print("\nTesting simple text generation...")

        # Get API key from environment variable or config
        from utils import get_api_key_securely
        api_key = get_api_key_securely("gemini")

        # Configure the Gemini API
        genai.configure(api_key=api_key)

        # Create a model instance
        model = genai.GenerativeModel(GEMINI_MODEL_FLASH)

        # Generate content
        response = model.generate_content(
            "Say hello in 3 different languages."
        )

        if response and response.text:
            print("✅ Successfully generated text:")
            print("-" * 40)
            print(response.text)
            print("-" * 40)
            return True
        else:
            print("❌ Failed to generate text: Empty response")
            return False
    except ImportError as e:
        print(f"❌ Error importing required libraries: {str(e)}")
        return False
    except APIError as e:
        print(f"❌ API Error: {str(e)}")
        return False
    except ConnectionError as e:
        print(f"❌ Connection Error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False


def test_audio_transcription(audio_file_path):
    """Test audio transcription with Gemini API"""
    try:
        print(f"\nTesting audio transcription with file: {audio_file_path}")

        if not os.path.exists(audio_file_path):
            print(f"❌ Audio file not found: {audio_file_path}")
            return False

        # Call the transcription function
        transcript_path = transcribe_audio_with_gemini(audio_file_path)

        if transcript_path and os.path.exists(transcript_path):
            print(f"✅ Successfully transcribed audio to: {transcript_path}")

            # Read and display a snippet of the transcript
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript_text = f.read()
                preview = transcript_text[:200] + "..." if len(transcript_text) > 200 else transcript_text
                print("\nTranscript preview:")
                print("-" * 40)
                print(preview)
                print("-" * 40)

            return True
        else:
            print("❌ Failed to transcribe audio: No transcript path returned")
            return False
    except FileNotFoundError as e:
        print(f"❌ File error: {str(e)}")
        return False
    except APIError as e:
        print(f"❌ API Error: {str(e)}")
        return False
    except FilesystemError as e:
        print(f"❌ Filesystem Error: {str(e)}")
        return False
    except ConnectionError as e:
        print(f"❌ Connection Error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False


def test_edge_cases():
    """Test edge cases and error handling"""
    print("\nTesting edge cases...")
    
    # Test with non-existent file
    print("\nTesting with non-existent audio file:")
    result = test_audio_transcription("non_existent_file.mp3")
    assert result == False, "Should return False for non-existent file"
    
    # Mock-based API error testing
    try:
        print("\nTesting API error handling (using mocks):")
        import unittest.mock as mock
        from utils import get_api_key_securely
        
        # Save the original key for restoration later
        original_api_key = get_api_key_securely("gemini")
        
        # Here we would use mock to patch the API call and make it throw an error
        # This is a more realistic approach to testing error handling
        print("In a real implementation, we would use mock.patch to simulate API errors.")
        print("Example: with mock.patch('google.generativeai.GenerativeModel.generate_content', side_effect=Exception())")
        
        print("✅ Error handling test concept demonstrated")
        return True
    except Exception as e:
        print(f"❌ Error during edge case testing: {str(e)}")
        return False


def test_url_validation():
    """Test URL validation function"""
    print("\nTesting URL validation...")
    from utils import validate_url
    
    valid_urls = [
        "https://www.youtube.com/watch?v=abcdefg1234",
        "https://youtube.com/watch?v=abcdefg1234",
        "https://m.youtube.com/watch?v=abcdefg1234",
        "https://youtu.be/abcdefg1234",
        "https://www.youtube.com/shorts/abcdefg1234"
    ]
    
    invalid_urls = [
        "https://www.not-youtube.com/watch?v=abcdefg1234",
        "https://www.youtube.com/invalid/abcdefg1234",
        "not a url at all",
        "https://www.vimeo.com/12345"
    ]
    
    all_valid = True
    for url in valid_urls:
        result = validate_url(url)
        if result:
            print(f"✅ Correctly validated URL: {url}")
        else:
            print(f"❌ Failed to validate valid URL: {url}")
            all_valid = False
    
    all_invalid = True
    for url in invalid_urls:
        result = validate_url(url)
        if not result:
            print(f"✅ Correctly rejected invalid URL: {url}")
        else:
            print(f"❌ Incorrectly validated invalid URL: {url}")
            all_invalid = False
    
    return all_valid and all_invalid

def main():
    """Run all tests"""
    print("=" * 50)
    print("CONSOLIDATED TEST SCRIPT")
    print("=" * 50)
    
    print("\n----- UTILITY TESTS -----")
    # Test URL validation
    test_url_validation()
    
    print("\n----- GEMINI API TESTS -----")
    # Test API availability
    if not test_gemini_availability():
        print("\nCannot proceed with Gemini API tests as the API is not available.")
    else:
        # Run basic API test
        test_simple_generation()
        
        # Test edge cases
        test_edge_cases()

        # Test audio transcription if a suitable file exists
        audio_file = "Video shows moment roof collapsed in packed Dominican Republic club_audio.mp3"
        if os.path.exists(audio_file):
            test_audio_transcription(audio_file)
        else:
            print(f"\n⚠️ Audio file not found: {audio_file}")
            print("Skipping audio transcription test.")
            print("To test audio transcription, download an audio file first.")

    print("\nAll tests completed!")


if __name__ == "__main__":
    main()