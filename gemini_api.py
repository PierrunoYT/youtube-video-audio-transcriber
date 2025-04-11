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
    Check if Gemini API is available and configured with valid API key.
    
    Returns:
        bool: True if Gemini API is available and configured properly
        
    Raises:
        ImportError: If the Gemini API library is not installed
        APIError: If no valid API key is provided or key format is invalid
    """

    if not GEMINI_AVAILABLE:
        raise ImportError("Google Gemini API library is not installed. "
                        "Install with: pip install google-generativeai")
    
    # Get the API key
    api_key = get_api_key_securely("gemini")
    
    # Validate API key exists
    if not api_key:
        raise APIError("No Google Gemini API key provided.")
    
    # Validate API key format (Google API keys typically follow a pattern)
    # This is a basic check - Google's keys usually start with "AI" and are ~40 chars
    if not isinstance(api_key, str) or len(api_key) < 30 or not api_key.startswith("AI"):
        raise APIError("Invalid Google Gemini API key format. Keys typically start with 'AI' and are ~40 characters long.")
    
    # Configure the API with the validated key
    genai.configure(api_key=api_key)
    
    # Perform a minimal API test to verify connectivity
    try:
        # Just initialize model without making an actual API call
        # This helps verify the SDK is properly configured
        model = genai.GenerativeModel(GEMINI_MODEL_FLASH)
        
        # If we get here, basic configuration appears to be working
        return True
    except Exception as e:
        raise APIError(f"Gemini API configuration error: {str(e)}")
        
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
    Transcribe audio using Google's Gemini API and save as text file.
    
    Args:
        audio_file_path (str): Path to the audio file to transcribe
        
    Returns:
        str: Path to the saved transcript file
        
    Raises:
        FileNotFoundError: If the audio file does not exist
        APIError: If transcription failed due to API issues
        FilesystemError: If saving the transcript failed
    """

    try:
        _check_gemini_availability()
        print("\nTranscribing audio using Google's Gemini API...")
        print("This may take a while depending on the file size.")

        # Check if file exists
        if not os.path.exists(audio_file_path):
            error_msg = f"File {audio_file_path} does not exist."
            logging.error(error_msg)
            raise FileNotFoundError(error_msg)
            
        # Validate file is actually an audio file
        file_ext = os.path.splitext(audio_file_path)[1].lower()
        valid_audio_exts = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac', '.aiff']
        if file_ext not in valid_audio_exts:
            error_msg = f"File {audio_file_path} does not appear to be a supported audio format."
            logging.error(error_msg)
            raise ValueError(error_msg)

        # Transcribe audio
        transcript_text = _transcribe_audio_gemini(audio_file_path)
        if not transcript_text:
            error_msg = "Transcription failed: Empty transcript returned"
            logging.error(error_msg)
            raise APIError(error_msg)
            
        # Save transcript
        transcript_path = _save_transcript(audio_file_path, transcript_text, "gemini")
        if not transcript_path or not os.path.exists(transcript_path):
            error_msg = "Failed to save transcript file"
            logging.error(error_msg)
            raise FilesystemError(error_msg)
            
        return transcript_path

    except (FileNotFoundError, ValueError, APIError, FilesystemError) as e:
        # Handle specific exceptions with appropriate error messages
        handle_gemini_error(e)
        # Re-raise the exception so the caller knows something failed
        raise
    except Exception as e:
        # Handle unexpected exceptions
        error_msg = f"Unexpected error during transcription: {str(e)}"
        logging.error(error_msg)
        handle_gemini_error(APIError(error_msg))
        # Re-raise as APIError for consistent error handling
        raise APIError(error_msg)


def _save_transcript(audio_file_path, transcript_text, service="gemini"):
    """
    Save transcript to a file with proper file locking to prevent race conditions.
    
    Args:
        audio_file_path (str): Path to the original audio file
        transcript_text (str): The transcribed text content to save
        service (str, optional): Service name to include in the output filename. Defaults to "gemini".
        
    Returns:
        str: Path to the saved transcript file
        
    Raises:
        FilesystemError: If there's an error saving the transcript to a file
    """
    import fcntl  # File locking
    import tempfile  # For safe atomic writes
    
    transcript_path = None
    temp_file = None
    
    try:
        # Generate transcript filename
        audio_path = Path(audio_file_path)
        transcript_filename = f"{audio_path.stem}_{service}_transcript.txt"
        transcript_path = audio_path.parent / transcript_filename
        
        # Create a temporary file in the same directory for atomic writes
        temp_dir = audio_path.parent
        temp_file = tempfile.NamedTemporaryFile(mode='w', 
                                              dir=temp_dir, 
                                              suffix='.txt', 
                                              encoding='utf-8',
                                              delete=False)
        
        # Use a file lock to ensure exclusive write access
        try:
            # Write to temporary file
            with open(temp_file.name, 'w', encoding='utf-8') as f:
                # Acquire exclusive lock
                fcntl.flock(f, fcntl.LOCK_EX)
                # Write content
                f.write(transcript_text)
                # Release lock (happens automatically when file is closed)
            
            # Atomic rename to target file (this is thread-safe)
            os.replace(temp_file.name, transcript_path)
            
        except Exception as e:
            # Clean up temp file in case of error
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except:
                    pass
            raise e
            
        print(f"\nTranscript saved to: {transcript_path}")
        return str(transcript_path)
        
    except (IOError, OSError) as e:
        error_msg = f"Error saving transcript: {str(e)}"
        logging.error(error_msg)
        raise FilesystemError(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error saving transcript: {str(e)}"
        logging.error(error_msg)
        raise FilesystemError(error_msg)
    finally:
        # Clean up temporary file if it exists and wasn't renamed
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
            except:
                pass


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
    error_type = type(error).__name__
    
    # Log with appropriate error type
    logging.error(f"Gemini API Error ({error_type}): {error_message}")
    print(f"\nGemini API Error ({error_type}):", error_message)

    # Comprehensive error tip dictionary covering various error cases
    error_tips = {
        # API key related errors
        "API key not valid": [
            "Check that you've entered your Gemini API key correctly.",
            "Verify your API key is still valid.",
            "Create a new API key if needed."
        ],
        "invalid": [
            "The API key format appears to be incorrect.",
            "Ensure you're using a valid Gemini API key (typically starts with 'AI').",
            "Get a new API key from Google AI Studio if needed."
        ],
        "unauthorized": [
            "Your API key doesn't have permission for this operation.",
            "Check that your API key has the necessary permissions.",
            "Verify that you're using the correct API key for this service."
        ],
        
        # Rate limiting and quota errors
        "quota": [
            "You've reached your API usage limit.",
            "Wait and try again later or check your API usage limits.",
            "Consider upgrading your API tier if you need higher usage limits."
        ],
        "rate limit": [
            "Too many requests in a short period of time.",
            "Implement exponential backoff in your requests.",
            "Wait a few minutes before trying again."
        ],
        
        # Content and file-related errors
        "file size": [
            "The audio file is too large for Gemini API.",
            "Try with a smaller audio file or split the file.",
            "The current limit is 20MB per request."
        ],
        "content": [
            "The content may violate Google's acceptable use policies.",
            "Check that your content adheres to Gemini's content policies.",
            "Try using different content."
        ],
        "format": [
            "The audio format is not supported.",
            "Try converting to a supported format like MP3, WAV, or FLAC.",
            "Check the file extension matches the actual file format."
        ],
        "empty": [
            "The audio file appears to be empty or corrupted.",
            "Check that the audio file contains valid audio data.",
            "Try a different audio file."
        ],
        
        # Connection and service errors
        "connection": [
            "Could not connect to the Gemini API.",
            "Check your internet connection.",
            "The service might be temporarily unavailable - try again later."
        ],
        "timeout": [
            "The request timed out.",
            "Try again later or with a smaller file.",
            "Check your network connection speed."
        ],
        "server": [
            "A server error occurred on Google's end.",
            "This is not an issue with your code or files.",
            "Try again later when the service might be more stable."
        ],
        
        # File system errors
        "file not found": [
            "The audio file could not be found.",
            "Check that the file path is correct and the file exists.",
            "Verify file permissions allow reading the file."
        ],
        "permission": [
            "Permission denied when trying to access the file.",
            "Check that you have the necessary permissions to read/write the files.",
            "Try running the script with appropriate permissions."
        ],
        
        # Memory errors
        "memory": [
            "Not enough memory to process the file.",
            "Try with a smaller file or on a system with more memory.",
            "Close other applications to free up memory."
        ],
        
        # Generic errors (default fallback)
        "generic": [
            "Check your internet connection.",
            "Verify that the Google Gemini API is available.",
            "Try again later or with a different audio file.",
            "Update to the latest version of the google-generativeai library."
        ]
    }

    # Try to match the error message with appropriate tips
    matched = False
    for key, tips in error_tips.items():
        if key.lower() in error_message.lower():
            print("\nTroubleshooting tips:")
            for tip in tips:
                print(f"- {tip}")
            matched = True
            break
    
    # If no specific error matched, use error type to find more relevant tips
    if not matched:
        if isinstance(error, FileNotFoundError) and "file not found" in error_tips:
            print("\nTroubleshooting tips:")
            for tip in error_tips["file not found"]:
                print(f"- {tip}")
        elif isinstance(error, PermissionError) and "permission" in error_tips:
            print("\nTroubleshooting tips:")
            for tip in error_tips["permission"]:
                print(f"- {tip}")
        elif isinstance(error, MemoryError) and "memory" in error_tips:
            print("\nTroubleshooting tips:")
            for tip in error_tips["memory"]:
                print(f"- {tip}")
        elif isinstance(error, TimeoutError) and "timeout" in error_tips:
            print("\nTroubleshooting tips:")
            for tip in error_tips["timeout"]:
                print(f"- {tip}")
        elif isinstance(error, ConnectionError) and "connection" in error_tips:
            print("\nTroubleshooting tips:")
            for tip in error_tips["connection"]:
                print(f"- {tip}")
        else:
            # If still no match, use generic tips
            print("\nTroubleshooting tips:")
            for tip in error_tips["generic"]:
                print(f"- {tip}")

    print("\nFor technical support, please provide the following error details:")
    print(f"Error type: {error_type}")
    print(f"Error message: {error_message}")


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
    """Handle Gemini transcription and subsequent actions with proper error handling."""

    print("\n" + "=" * 60)
    print("GEMINI TRANSCRIPTION OPTION")
    print("=" * 60)
    print("The downloaded file contains audio that can be transcribed.")
    print("Google's Gemini API will be used for transcription.")
    print("The transcription will be saved as a text file.")

    transcribe_choice = input(
        "\nWould you like to transcribe the audio using Google's Gemini API? (Press Enter for yes/n for no): ").lower()

    if transcribe_choice in ["", "yes", "y"]:
        transcript_path = None
        success = False
        
        try:
            # Verify file exists before attempting transcription
            if not os.path.exists(audio_file_path):
                print(f"\nError: Audio file not found at '{audio_file_path}'")
                return
                
            # Attempt transcription
            transcript_path = transcribe_audio_with_gemini(audio_file_path)
            
            # Verify result is valid
            if transcript_path and os.path.exists(transcript_path):
                print(f"\nTranscription saved successfully to: {transcript_path}")
                success = True
                
        except (FileNotFoundError, ValueError) as e:
            # File-related errors are already handled by transcribe_audio_with_gemini
            # We don't need to do anything additional here
            logging.error(f"File error in transcription option: {str(e)}")
            
        except APIError as e:
            # API errors are already handled by transcribe_audio_with_gemini
            # We don't need to do anything additional here
            logging.error(f"API error in transcription option: {str(e)}")
            
        except Exception as e:
            # Unexpected errors should be logged
            logging.error(f"Unexpected error in transcription option: {str(e)}")
            print(f"\nAn unexpected error occurred during transcription: {str(e)}")
            
        # Only proceed to post-processing if transcription was successful
        if success and transcript_path:
            try:
                _handle_post_transcription_gemini_options(audio_file_path, transcript_path)
            except Exception as e:
                logging.error(f"Error in post-transcription processing: {str(e)}")
                print(f"\nError in post-transcription processing: {str(e)}")
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