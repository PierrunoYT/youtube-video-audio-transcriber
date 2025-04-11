"""
Transcription module for the YouTube downloader application.
Handles audio transcription using OpenAI's Whisper model.
"""
import os
import openai
from pathlib import Path
from utils import get_api_key_securely

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

def handle_transcription_option(audio_file_path):
    """Handle the transcription option for downloaded audio"""
    print("\n" + "=" * 60)
    print("TRANSCRIPTION OPTIONS")
    print("=" * 60)
    print("The downloaded file contains audio that can be transcribed.")
    print("You can choose between different transcription services:")
    print("1. OpenAI's Whisper model (best for accurate transcription)")
    print("2. Google's Gemini API (allows summarization and Q&A)")

    service_choice = input("\nChoose a transcription service (1-2, or press Enter for OpenAI): ")

    if service_choice == "2":
        # Import Gemini API module
        try:
            from gemini_api import handle_gemini_transcription_option
            handle_gemini_transcription_option(audio_file_path)
        except ImportError:
            print("\nError: Gemini API module not found. Falling back to OpenAI.")
            _handle_openai_transcription(audio_file_path)
    else:
        # Default to OpenAI
        _handle_openai_transcription(audio_file_path)

def _handle_openai_transcription(audio_file_path):
    """Handle OpenAI transcription specifically"""
    print("\n" + "=" * 60)
    print("OPENAI TRANSCRIPTION")
    print("=" * 60)
    print("OpenAI's Whisper model will be used for transcription.")
    print("The transcription will be saved as a text file.")
    transcribe_choice = input("\nWould you like to transcribe the audio using OpenAI's Whisper model? (Press Enter for yes/n for no): ").lower()
    if transcribe_choice in ["", "yes", "y"]:
        transcript_path = transcribe_audio(audio_file_path)
        if transcript_path and os.path.exists(transcript_path):
            print(f"\nTranscription saved successfully to: {transcript_path}")
            print("You can open this markdown file in any text editor or markdown viewer.")

            # Add Gemini AI features after successful transcription
            print("\nWould you like to:")
            print("1. Summarize the transcript")
            print("2. Ask a single question about the content")
            print("3. Start an interactive chat about the transcript")
            print("4. Start an interactive chat with the original audio")
            print("5. Skip")

            gemini_choice = input("\nEnter your choice (1-5): ")

            try:
                if gemini_choice == "1":
                    from gemini_api import summarize_transcript
                    summary_path = summarize_transcript(transcript_path)
                    if summary_path:
                        print(f"\nSummary saved to: {summary_path}")

                elif gemini_choice == "2":
                    from gemini_api import ask_question_about_transcript
                    question = input("\nEnter your question: ")
                    ask_question_about_transcript(transcript_path, question)

                elif gemini_choice == "3":
                    from gemini_api import chat_with_content
                    chat_with_content(transcript_path, "transcript")

                elif gemini_choice == "4":
                    from gemini_api import chat_with_content
                    chat_with_content(audio_file_path, "audio")

                else:
                    print("\nSkipping AI features.")

            except ImportError:
                print("\nError: Gemini API module not available. Skipping AI features.")
    else:
        print("\nTranscription skipped.")

