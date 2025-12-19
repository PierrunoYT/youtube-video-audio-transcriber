"""
Transcription module for the YouTube downloader application.
Handles audio transcription using OpenAI's Whisper model.
"""

import os
from pathlib import Path
import openai
from utils import get_api_key_securely, logging, APIError, FilesystemError  # Import logging and custom exceptions

def _transcribe_with_openai(audio_file_path):
    """Transcribe audio using OpenAI's Whisper model.
    
    Args:
        audio_file_path (str): Path to the audio file to transcribe
        
    Returns:
        str: The transcribed text if successful
        None: If transcription was cancelled by the user due to file size warnings
        
    Raises:
        openai.APIError: If there's an error with the OpenAI API
    """

    client = openai.OpenAI()

    # OpenAI has a 25MB file size limit
    file_size_mb = os.path.getsize(audio_file_path) / (1024 * 1024)
    if file_size_mb > 25:
        logging.warning("File is larger than 25MB, which is OpenAI's limit. Transcription may fail.")
        proceed = input("Do you want to proceed anyway? (y/n): ").lower()
        if proceed != 'y':
            print("Transcription cancelled.")
            return None

    with open(audio_file_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
    return transcript.text

def _save_transcript_to_file(audio_file_path, transcript_text):
    """Save transcript to a markdown file.
    
    Args:
        audio_file_path (str): Path to the audio file
        transcript_text (str): The transcribed text to save
        
    Returns:
        str: Path to the saved transcript file
        
    Raises:
        FilesystemError: If there's an error saving the transcript
    """

    audio_path = Path(audio_file_path)
    video_title = audio_path.stem
    transcript_path = audio_path.parent / f"{audio_path.stem}_transcript.md"
    try:
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(f"# Transcript: {video_title}\n\n")
            # Write transcript text as-is without naive splitting
            # This preserves the original formatting and avoids breaking on abbreviations
            f.write(transcript_text)
        return str(transcript_path)
    except (FileNotFoundError, PermissionError) as e:
        raise FilesystemError(f"Error saving transcript: {str(e)}")

def transcribe_audio(audio_file_path):
    """Orchestrate audio transcription and saving.
    
    Args:
        audio_file_path (str): Path to the audio file to transcribe
        
    Returns:
        str: Path to the saved transcript file if successful
        None: If transcription was cancelled by the user
        
    Raises:
        APIError: If there's an error with the OpenAI API
        FilesystemError: If there's an error reading/writing files
        Exception: For other unexpected errors
    """

    try:
        get_api_key_securely()  # Ensure API key is set
        print("\nTranscribing audio using OpenAI's Whisper model...")
        print("This may take a while depending on the file size.")

        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"File {audio_file_path} does not exist.")

        transcript_text = _transcribe_with_openai(audio_file_path)
        if not transcript_text:
            return None  # Transcription failed

        transcript_path = _save_transcript_to_file(audio_file_path, transcript_text)
        print(f"\nTranscription completed and saved to: {transcript_path}")
        return transcript_path

    except openai.APIConnectionError as e:
        raise APIError(f"Unable to connect to OpenAI API: {str(e)}")
    except openai.APIError as e:
        raise APIError(f"OpenAI API error: {str(e)}")
    except openai.RateLimitError as e:
        raise APIError(f"OpenAI API rate limit exceeded: {str(e)}")
    except openai.AuthenticationError as e:
        raise APIError(f"Invalid OpenAI API key: {str(e)}")
    except FileNotFoundError as e:
        raise FilesystemError(str(e))
    except Exception as e:
        raise Exception(f"An unexpected error occurred during transcription: {str(e)}")

def handle_transcription_option(audio_file_path):
    """Handle the transcription option for downloaded audio."""

    print("\n" + "=" * 60)
    print("TRANSCRIPTION OPTIONS")
    print("=" * 60)
    print("The downloaded file contains audio that can be transcribed.")
    print("You can choose between different transcription services:")
    print("1. OpenAI's Whisper model (best for accurate transcription)")
    print("2. Google's Gemini API (allows summarization and Q&A)")

    service_choice = input("\nChoose a transcription service (1-2, or press Enter for OpenAI): ")

    if service_choice == "2":
        try:
            from gemini_api import handle_gemini_transcription_option
            handle_gemini_transcription_option(audio_file_path)
        except ImportError:
            print("\nError: Gemini API module not found. Falling back to OpenAI.")
            _handle_openai_transcription(audio_file_path)
    else:
        _handle_openai_transcription(audio_file_path)

def _handle_openai_transcription(audio_file_path):
    """Handle OpenAI transcription specifically."""

    print("\n" + "=" * 60)
    print("OPENAI TRANSCRIPTION")
    print("=" * 60)
    print("OpenAI's Whisper model will be used for transcription.")
    print("The transcription will be saved as a text file.")

    transcribe_choice = input("\nWould you like to transcribe the audio using OpenAI's Whisper model? (Press Enter for yes/n for no): ").lower()
    if transcribe_choice in ["", "yes", "y"]:
        try:
            transcript_path = transcribe_audio(audio_file_path)
            if transcript_path and os.path.exists(transcript_path):
                print(f"\nTranscription saved successfully to: {transcript_path}")
                print("You can open this markdown file in any text editor or markdown viewer.")

                _handle_post_transcription_options(audio_file_path, transcript_path)
        except APIError as e:
            logging.error(f"API Error during transcription: {e}")
            print(f"\nError during transcription: {e}")
        except FilesystemError as e:
            logging.error(f"Filesystem Error during transcription: {e}")
            print(f"\nError during transcription: {e}")
        except Exception as e:
            logging.error(f"Unexpected error during transcription: {e}")
            print(f"\nAn unexpected error occurred during transcription: {e}")
    else:
        print("\nTranscription skipped.")

def _handle_post_transcription_options(audio_file_path, transcript_path):
    """Handle options to summarize or chat with the transcript after successful transcription."""

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
    except Exception as e:
        logging.error(f"Error during post-transcription processing: {e}")
        print(f"\nError during post-transcription processing: {e}")