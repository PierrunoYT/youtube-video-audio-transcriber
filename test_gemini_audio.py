"""
Test script for Gemini API audio transcription.
This script tests the audio transcription functionality of the Gemini API module.
"""
import os
import sys

# Add the parent directory to the path so we can import the gemini_api module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module we want to test
from gemini_api import check_gemini_availability, transcribe_audio_with_gemini

def test_gemini_availability():
    """Test if Gemini API is available and properly configured"""
    print("Testing Gemini API availability...")
    result = check_gemini_availability()
    if result:
        print("✅ Gemini API is available and properly configured!")
    else:
        print("❌ Gemini API is not available or not properly configured.")
    return result

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
            print("❌ Failed to transcribe audio.")
            return False
    except Exception as e:
        print(f"❌ Error during audio transcription: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("GEMINI API AUDIO TRANSCRIPTION TEST")
    print("=" * 50)

    # Test API availability
    if not test_gemini_availability():
        print("\nCannot proceed with further tests as Gemini API is not available.")
        return

    # Use the specific audio file we know exists
    audio_file = "Video shows moment roof collapsed in packed Dominican Republic club_audio.mp3"

    if not os.path.exists(audio_file):
        print(f"\n❌ Audio file not found: {audio_file}")
        print("Please run the main application first to download an audio file.")
        return

    most_recent_audio = audio_file

    # Test audio transcription
    test_audio_transcription(most_recent_audio)

    print("\nTests completed!")

if __name__ == "__main__":
    main()
