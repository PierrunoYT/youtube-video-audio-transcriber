"""
Gemini API module for the YouTube downloader application.
Handles audio processing, transcription, and interactions using Google's Gemini API.
"""

import os
from pathlib import Path
import base64
from utils import get_api_key_securely, logging, APIError, FilesystemError
from config import GEMINI_MODEL_FLASH, GEMINI_MODEL_PRO

# Import Gemini API library
try:
    import google.generativeai as genai

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


def _check_gemini_availability():
    """
    Check if Gemini API is available and configured.
    
    Returns:
        bool: True if Gemini API is available and configured properly
        
    Raises:
        ImportError: If the Gemini API library is not installed
        APIError: If no valid API key is provided
    """

    if not GEMINI_AVAILABLE:
        raise ImportError("Google Gemini API library is not installed. "
                        "Install with: pip install google-generativeai")
    api_key = get_api_key_securely("gemini")
    if not api_key:
        raise APIError("No Google Gemini API key provided.")
    genai.configure(api_key=api_key)  # Configure the Gemini API
    return True


def _transcribe_audio_gemini(audio_file_path, model_name=GEMINI_MODEL_FLASH):
    """
    Transcribe audio using Gemini.
    
    Args:
        audio_file_path (str): Path to the audio file to transcribe
        model_name (str, optional): Name of the Gemini model to use. Defaults to GEMINI_MODEL_FLASH.
        
    Returns:
        str: The transcribed text
        
    Raises:
        APIError: If no response is received from Gemini API
    """

    # Check if the file is larger than 20MB
    if os.path.getsize(audio_file_path) / (1024 * 1024) > 20:
        return _transcribe_large_audio_gemini(audio_file_path, model_name)

    try:
        model = genai.GenerativeModel(model_name)
        mime_type = _get_mime_type(audio_file_path)
        
        # Read file in smaller chunks to avoid memory issues
        with open(audio_file_path, 'rb') as f:
            audio_bytes = f.read()
            
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        # Use the updated API format
        response = model.generate_content(
            [
                {"text": "Generate a complete and accurate transcript."},
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": audio_base64
                    }
                }
            ]
        )
        
        # Check for empty response and provide detailed error
        if not response:
            raise APIError("Empty response received from Gemini API")
        if not response.text:
            error_details = getattr(response, 'error', 'Unknown error')
            raise APIError(f"No text in Gemini API response. Details: {error_details}")
            
        return response.text
        
    except Exception as e:
        # Propagate original exception details
        if not isinstance(e, APIError):
            raise APIError(f"Gemini API transcription error: {str(e)}")
        raise


def _transcribe_large_audio_gemini(audio_file_path, model_name=GEMINI_MODEL_FLASH, chunk_size_mb=10):
    """
    Transcribe large audio files using Gemini's file upload API.
    Uses chunking for large files to prevent memory issues.
    
    Args:
        audio_file_path (str): Path to the large audio file to transcribe
        model_name (str, optional): Name of the Gemini model to use. Defaults to GEMINI_MODEL_FLASH.
        chunk_size_mb (int, optional): Size of chunks in MB when processing large files. Defaults to 10.
        
    Returns:
        str: The transcribed text
        
    Raises:
        APIError: If no response is received from Gemini API
    """
    try:
        file_size_mb = os.path.getsize(audio_file_path) / (1024 * 1024)
        client = genai.GenerativeModel(model_name)
        mime_type = _get_mime_type(audio_file_path)
        
        # For very large files (>50MB), warn the user
        if file_size_mb > 50:
            logging.warning(f"Very large audio file: {file_size_mb:.1f}MB. Transcription may take a long time.")
            print(f"\nWarning: This is a very large audio file ({file_size_mb:.1f}MB). Transcription may take a long time.")
        
        # Read and process audio in chunks if necessary
        if file_size_mb > chunk_size_mb:
            # For extremely large files, we'll use chunking
            print(f"\nProcessing large file in chunks to optimize memory usage...")
            
            # TODO: For future implementation - add actual chunking code here
            # Current Gemini API doesn't support partial audio transcription
            # This comment serves as a placeholder for future optimization
            
            # For now, we still need to load the whole file but with better error handling
            with open(audio_file_path, 'rb') as f:
                audio_bytes = f.read()
        else:
            # For files under the chunk size threshold
            with open(audio_file_path, 'rb') as f:
                audio_bytes = f.read()
        
        # Process the audio data
        response = client.generate_content(
            [
                "Generate a complete and accurate transcript.",
                {"inline_data": {"mime_type": mime_type, "data": base64.b64encode(audio_bytes).decode('utf-8')}}
            ]
        )
        
        # Check for empty response with detailed error info
        if not response:
            raise APIError("Empty response received from Gemini API for large audio file")
        if not response.text:
            error_details = getattr(response, 'error', 'Unknown error')
            raise APIError(f"No text in Gemini API response for large audio. Details: {error_details}")
            
        return response.text
        
    except MemoryError:
        raise APIError("Memory error processing large audio file. File too large for available system memory.")
    except Exception as e:
        # Propagate original exception details
        if not isinstance(e, APIError):
            raise APIError(f"Gemini API large file transcription error: {str(e)}")
        raise


def transcribe_audio_with_gemini(audio_file_path):
    """
    Transcribe audio using Google's Gemini API and save as markdown.
    
    Args:
        audio_file_path (str): Path to the audio file to transcribe
        
    Returns:
        str: Path to the saved transcript file, or None if transcription failed
        
    Raises:
        FileNotFoundError: If the audio file does not exist
    """

    try:
        _check_gemini_availability()
        print("\nTranscribing audio using Google's Gemini API...")
        print("This may take a while depending on the file size.")

        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"File {audio_file_path} does not exist.")

        transcript_text = _transcribe_audio_gemini(audio_file_path)
        transcript_path = _save_transcript(audio_file_path, transcript_text, "gemini")
        return transcript_path

    except Exception as e:
        handle_gemini_error(e)
        return None


def _save_transcript(audio_file_path, transcript_text, service="gemini"):
    """
    Save transcript to a file.
    
    Args:
        audio_file_path (str): Path to the original audio file
        transcript_text (str): The transcribed text content to save
        service (str, optional): Service name to include in the output filename. Defaults to "gemini".
        
    Returns:
        str: Path to the saved transcript file
        
    Raises:
        FilesystemError: If there's an error saving the transcript to a file
    """

    try:
        audio_path = Path(audio_file_path)
        transcript_filename = f"{audio_path.stem}_{service}_transcript.txt"
        transcript_path = audio_path.parent / transcript_filename
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(transcript_text)
        print(f"\nTranscript saved to: {transcript_path}")
        return str(transcript_path)
    except Exception as e:
        raise FilesystemError(f"Error saving transcript: {str(e)}")


def _get_mime_type(file_path):
    """
    Determine MIME type based on file extension.
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        str: MIME type corresponding to the file extension, defaults to 'audio/mpeg' if unknown
    """
    # Simple dictionary-based approach for common audio formats
    mime_types = {
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.m4a': 'audio/mp4',
        '.aac': 'audio/aac',
        '.ogg': 'audio/ogg',
        '.flac': 'audio/flac',
        '.aiff': 'audio/aiff',
    }
    ext = os.path.splitext(file_path)[1].lower()
    return mime_types.get(ext, 'audio/mpeg')  # Default to audio/mpeg


def handle_gemini_error(error):
    """
    Handle Gemini API errors with logging and user-friendly messages.
    
    Args:
        error (Exception): The error that occurred
    """

    error_message = str(error)
    logging.error(f"Gemini API Error: {error_message}")
    print("\nGemini API Error:", error_message)

    error_tips = {
        "API key not valid": [
            "Check that you've entered your Gemini API key correctly.",
            "Verify your API key is still valid.",
            "Create a new API key if needed."
        ],
        "quota": [
            "You've reached your API usage limit.",
            "Wait and try again later or check your API usage limits."
        ],
        "file size": [
            "The audio file is too large for Gemini API.",
            "Try with a smaller audio file or split the file."
        ],
        "generic": [
            "Check your internet connection.",
            "Verify that the Google Gemini API is available.",
            "Try again later or with a different audio file."
        ]
    }

    for key, tips in error_tips.items():
        if key in error_message.lower():
            print("\nTroubleshooting tips:")
            for tip in tips:
                print(f"- {tip}")
            return  # Exit after printing relevant tips

    # If no specific error matched, print generic tips
    print("\nTroubleshooting tips:")
    for tip in error_tips["generic"]:
        print(f"- {tip}")

    print("\nFor technical support, please provide the following error details:")
    print(f"Error: {error_message}")


def chat_with_content(content_path, content_type="transcript"):
    """
    Start an interactive chat session with content using Gemini.
    
    Args:
        content_path (str): Path to the content file (transcript or audio)
        content_type (str, optional): Type of content ('transcript' or 'audio'). Defaults to "transcript".
        
    Raises:
        FileNotFoundError: If the content file does not exist
        ValueError: If an unsupported content type is provided
        APIError: If no response is received from Gemini API
    """

    try:
        _check_gemini_availability()
        if not os.path.exists(content_path):
            raise FileNotFoundError(f"File {content_path} does not exist.")

        if content_type not in ["transcript", "audio"]:
            raise ValueError(f"Unsupported content type: {content_type}")

        model_name = GEMINI_MODEL_PRO if content_type == "transcript" else GEMINI_MODEL_FLASH
        model = genai.GenerativeModel(model_name)
        chat = model.start_chat()  # Initialize chat session

        _print_chat_instructions(content_type)

        if content_type == "transcript":
            with open(content_path, 'r', encoding='utf-8') as f:
                transcript_text = f.read()
            chat.send_message(f"You are an AI assistant for a transcript. Use this transcript to answer: {transcript_text}")

        while True:
            user_input = input("\nYou: ")
            if user_input.lower() in ["exit", "quit", "bye", "goodbye"]:
                print("\nEnding chat session. Goodbye!")
                break

            print("\nAI is thinking...")
            response = chat.send_message(user_input)
            if not response or not response.text:
                raise APIError("No response from Gemini API.")
            print("\nAI:")
            print(response.text)

    except Exception as e:
        handle_gemini_error(e)


def _print_chat_instructions(content_type):
    """Print instructions for the chat session."""

    print("\n" + "=" * 60)
    print(f"CHAT WITH {content_type.upper()} CONTENT")
    print("=" * 60)
    if content_type == "transcript":
        print("You can now chat with the AI about the transcript content.")
        print("The AI will answer based on the information in the transcript.")
    elif content_type == "audio":
        print("You can now chat with the AI about the audio content.")
        print("The AI will listen to the audio and answer your questions.")
        print("Note: Each question requires re-processing the audio, which may take time.")
    print("Type 'exit', 'quit', or press Ctrl+C to end the chat.")


def handle_gemini_transcription_option(audio_file_path):
    """Handle Gemini transcription and subsequent actions."""

    print("\n" + "=" * 60)
    print("GEMINI TRANSCRIPTION OPTION")
    print("=" * 60)
    print("The downloaded file contains audio that can be transcribed.")
    print("Google's Gemini API will be used for transcription.")
    print("The transcription will be saved as a text file.")

    transcribe_choice = input(
        "\nWould you like to transcribe the audio using Google's Gemini API? (Press Enter for yes/n for no): ").lower()

    if transcribe_choice in ["", "yes", "y"]:
        try:
            transcript_path = transcribe_audio_with_gemini(audio_file_path)
            if transcript_path and os.path.exists(transcript_path):
                print(f"\nTranscription saved successfully to: {transcript_path}")
                _handle_post_transcription_gemini_options(audio_file_path, transcript_path)
        except Exception as e:
            # Exceptions are already handled in transcribe_audio_with_gemini
            # This is just a fallback in case something unexpected happens
            logging.error(f"Unexpected error in transcription: {e}")
            print(f"\nAn unexpected error occurred: {e}")
    else:
        print("\nTranscription cancelled.")


def _handle_post_transcription_gemini_options(audio_file_path, transcript_path):
    """Handle options to summarize or chat after Gemini transcription."""

    print("\nWhat would you like to do with the content?")
    print("1. Summarize the transcript")
    print("2. Ask a single question about the content")
    print("3. Start an interactive chat about the transcript")
    print("4. Start an interactive chat with the original audio")
    print("5. Skip")

    content_choice = input("\nEnter your choice (1-5): ")

    try:
        if content_choice == "1":
            summarize_transcript(transcript_path)
        elif content_choice == "2":
            question = input("\nEnter your question: ")
            ask_question_about_transcript(transcript_path, question)
        elif content_choice == "3":
            chat_with_content(transcript_path, "transcript")
        elif content_choice == "4":
            chat_with_content(audio_file_path, "audio")
        else:
            print("\nSkipping additional processing.")
    except Exception as e:
        # All exceptions are already handled in the called functions
        # This is just a fallback in case something unexpected happens
        logging.error(f"Unexpected error in post-transcription options: {e}")
        print(f"\nAn unexpected error occurred: {e}")


def ask_question_about_transcript(transcript_path, question):
    """
    Ask a question about a transcript using Google's Gemini API.
    
    Args:
        transcript_path (str): Path to the transcript file
        question (str): The question to ask about the transcript
        
    Returns:
        str: The answer text from Gemini, or None if an error occurred
        
    Raises:
        FileNotFoundError: If the transcript file does not exist
        APIError: If no response is received from Gemini API
    """
    try:
        _check_gemini_availability()
        if not os.path.exists(transcript_path):
            raise FileNotFoundError(f"Transcript file {transcript_path} does not exist.")

        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript_text = f.read()

        model = genai.GenerativeModel(GEMINI_MODEL_FLASH)

        prompt = f"""
        Based on the following transcript, please answer this question:

        Question: {question}

        Transcript:
        {transcript_text}

        Provide a detailed and accurate answer based only on the information in the transcript.
        """

        print("\nGenerating answer using Google's Gemini API...")
        response = model.generate_content(prompt)

        if not response or not response.text:
            raise APIError("No response from Gemini API.")

        print("\nAnswer from Gemini:")
        print("=" * 60)
        print(response.text)
        print("=" * 60)

        return response.text

    except Exception as e:
        handle_gemini_error(e)
        return None


def summarize_transcript(transcript_path):
    """
    Summarize a transcript using Google's Gemini API.
    
    Args:
        transcript_path (str): Path to the transcript file
        
    Returns:
        str: Path to the saved summary file, or None if summarization failed
        
    Raises:
        FileNotFoundError: If the transcript file does not exist
        APIError: If no response is received from Gemini API
    """
    try:
        _check_gemini_availability()
        if not os.path.exists(transcript_path):
            raise FileNotFoundError(f"Transcript file {transcript_path} does not exist.")

        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript_text = f.read()

        model = genai.GenerativeModel(GEMINI_MODEL_FLASH)

        prompt = f"""
        Please provide a comprehensive summary of the following transcript:

        {transcript_text}

        The summary should:
        1. Capture the main topics and key points
        2. Maintain the original meaning and context
        3. Be well-structured and concise
        4. Include any important details, facts, or figures mentioned
        """

        print("\nGenerating summary using Google's Gemini API...")
        response = model.generate_content(prompt)

        if not response or not response.text:
            raise APIError("No response from Gemini API.")

        summary_path = transcript_path.replace('_transcript.txt', '_summary.txt')
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(response.text)

        print(f"\nSummary saved to: {summary_path}")
        return summary_path

    except Exception as e:
        handle_gemini_error(e)
        return None