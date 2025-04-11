"""
Gemini API module for the YouTube downloader application.
Handles audio processing, transcription, and summarization using Google's Gemini API.
"""
import os
from pathlib import Path
from utils import get_api_key_securely

# Import Gemini API library
try:
    import google.genai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    try:
        # Try the older library as fallback
        import google.generativeai as genai
        GEMINI_AVAILABLE = True
    except ImportError:
        GEMINI_AVAILABLE = False

def check_gemini_availability():
    """Check if Gemini API is available and properly configured"""
    if not GEMINI_AVAILABLE:
        print("\nGoogle Gemini API library is not installed.")
        print("To install it, run: pip install google-genai")
        print("Note: The new Google Gen AI SDK has replaced the older google-generativeai library.")
        return False

    try:
        # Try to get API key
        api_key = get_api_key_securely("gemini")
        if not api_key:
            print("\nNo Google Gemini API key provided. Gemini features will not be available.")
            return False

        # Configure the Gemini API client
        try:
            # Try the new SDK configuration method
            # Store the client globally so it can be used throughout the module
            global gemini_client
            gemini_client = genai.Client(api_key=api_key)
        except AttributeError:
            # Fall back to the older library configuration method
            genai.configure(api_key=api_key)
        return True
    except Exception as e:
        print(f"\nError configuring Gemini API: {str(e)}")
        return False

def transcribe_audio_with_gemini(audio_file_path):
    """Transcribe audio using Google's Gemini API and save as markdown"""
    try:
        # Check if Gemini API is available
        if not check_gemini_availability():
            return None

        print("\nTranscribing audio using Google's Gemini API...")
        print("This may take a while depending on the file size.")

        # Check if file exists and is readable
        if not os.path.exists(audio_file_path):
            print(f"Error: File {audio_file_path} does not exist.")
            return None

        file_size_mb = os.path.getsize(audio_file_path) / (1024 * 1024)
        print(f"File size: {file_size_mb:.2f} MB")

        # Gemini has a 20MB file size limit for inline data
        if file_size_mb > 20:
            print("Warning: File is larger than 20MB, which is Gemini's inline data limit.")
            print("Using file upload method instead...")
            return transcribe_large_audio_with_gemini(audio_file_path)

        # Create a Gemini model instance
        if 'gemini_client' in globals():
            # The new SDK uses a different approach
            model = gemini_client.models.get(model='gemini-1.5-flash')
            model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            model = genai.GenerativeModel('gemini-1.5-flash')

        # Read the audio file
        with open(audio_file_path, 'rb') as f:
            audio_bytes = f.read()

        # Determine MIME type based on file extension
        mime_type = get_mime_type(audio_file_path)

        # Create the prompt for transcription
        prompt = "Generate a complete and accurate transcript of this audio file."

        # Create content with the audio data
        contents = [
            prompt,
            {"inlineData": {"mimeType": mime_type, "data": audio_bytes}}
        ]

        # Generate the transcript
        print("Sending file to Google Gemini for transcription...")
        response = model.generate_content(contents)

        if not response or not response.text:
            print("Error: No response from Gemini API.")
            return None

        # Save the transcript to a file
        transcript_path = save_transcript(audio_file_path, response.text, "gemini")

        return transcript_path

    except Exception as e:
        handle_gemini_error(e)
        return None

def transcribe_large_audio_with_gemini(audio_file_path):
    """Transcribe large audio files using Gemini's file upload API"""
    try:
        # Check if Gemini API is available
        if not check_gemini_availability():
            return None

        # Create a client instance
        if 'gemini_client' in globals():
            client = gemini_client
        else:
            client = genai.Client()

        # Upload the file
        print("Uploading audio file to Google Gemini...")
        uploaded_file = client.files.upload(file=audio_file_path)

        # Create a model instance
        model = client.models.generate_content('gemini-1.5-flash')

        # Generate the transcript
        print("Requesting transcription from Google Gemini...")
        response = model.generate_content(
            ["Generate a complete and accurate transcript of this audio file.", {"fileData": {"fileUri": uploaded_file.uri, "mimeType": "audio/mpeg"}}]
        )

        if not response or not response.text:
            print("Error: No response from Gemini API.")
            return None

        # Save the transcript to a file
        transcript_path = save_transcript(audio_file_path, response.text, "gemini")

        # Clean up the uploaded file
        client.files.delete(uploaded_file.name)

        return transcript_path

    except Exception as e:
        handle_gemini_error(e)
        return None

def summarize_transcript(transcript_path):
    """Summarize a transcript using Google's Gemini API"""
    try:
        # Check if Gemini API is available
        if not check_gemini_availability():
            return None

        # Check if file exists
        if not os.path.exists(transcript_path):
            print(f"Error: Transcript file {transcript_path} does not exist.")
            return None

        # Read the transcript
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript_text = f.read()

        # Create a Gemini model instance
        if 'gemini_client' in globals():
            # The new SDK uses a different approach
            model = gemini_client.models.get(model='gemini-1.5-flash')
            model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            model = genai.GenerativeModel('gemini-1.5-flash')

        # Create the prompt for summarization
        prompt = f"""
        Please provide a comprehensive summary of the following transcript:

        {transcript_text}

        The summary should:
        1. Capture the main topics and key points
        2. Maintain the original meaning and context
        3. Be well-structured and concise
        4. Include any important details, facts, or figures mentioned
        """

        # Generate the summary
        print("\nGenerating summary using Google's Gemini API...")
        response = model.generate_content(prompt)

        if not response or not response.text:
            print("Error: No response from Gemini API.")
            return None

        # Save the summary to a file
        summary_path = transcript_path.replace('_transcript.txt', '_summary.txt')
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(response.text)

        print(f"\nSummary saved to: {summary_path}")
        return summary_path

    except Exception as e:
        handle_gemini_error(e)
        return None

def ask_question_about_audio(audio_file_path, question):
    """Ask a question about an audio file using Google's Gemini API"""
    try:
        # Check if Gemini API is available
        if not check_gemini_availability():
            return None

        # Check if file exists and is readable
        if not os.path.exists(audio_file_path):
            print(f"Error: File {audio_file_path} does not exist.")
            return None

        file_size_mb = os.path.getsize(audio_file_path) / (1024 * 1024)

        # Determine if we need to use file upload API
        if file_size_mb > 20:
            return ask_question_about_large_audio(audio_file_path, question)

        # Create a Gemini model instance
        if 'gemini_client' in globals():
            # The new SDK uses a different approach
            model = gemini_client.models.get(model='gemini-1.5-flash')
            model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            model = genai.GenerativeModel('gemini-1.5-flash')

        # Read the audio file
        with open(audio_file_path, 'rb') as f:
            audio_bytes = f.read()

        # Determine MIME type based on file extension
        mime_type = get_mime_type(audio_file_path)

        # Create the prompt with the question
        prompt = f"Listen to this audio and answer the following question: {question}"

        # Create content with the audio data
        contents = [
            prompt,
            {"inlineData": {"mimeType": mime_type, "data": audio_bytes}}
        ]

        # Generate the answer
        print("\nProcessing audio and generating answer using Google's Gemini API...")
        response = model.generate_content(contents)

        if not response or not response.text:
            print("Error: No response from Gemini API.")
            return None

        print("\nAnswer from Gemini:")
        print("=" * 60)
        print(response.text)
        print("=" * 60)

        return response.text

    except Exception as e:
        handle_gemini_error(e)
        return None

def ask_question_about_large_audio(audio_file_path, question):
    """Ask a question about a large audio file using Gemini's file upload API"""
    try:
        # Check if Gemini API is available
        if not check_gemini_availability():
            return None

        # Create a client instance
        if 'gemini_client' in globals():
            client = gemini_client
        else:
            client = genai.Client()

        # Upload the file
        print("Uploading audio file to Google Gemini...")
        uploaded_file = client.files.upload(file=audio_file_path)

        # Create a model instance
        model = client.models.generate_content('gemini-1.5-flash')

        # Generate the answer
        print("Processing audio and generating answer...")
        response = model.generate_content(
            [f"Listen to this audio and answer the following question: {question}", {"fileData": {"fileUri": uploaded_file.uri, "mimeType": "audio/mpeg"}}]
        )

        if not response or not response.text:
            print("Error: No response from Gemini API.")
            return None

        print("\nAnswer from Gemini:")
        print("=" * 60)
        print(response.text)
        print("=" * 60)

        # Clean up the uploaded file
        client.files.delete(uploaded_file.name)

        return response.text

    except Exception as e:
        handle_gemini_error(e)
        return None

def ask_question_about_transcript(transcript_path, question):
    """Ask a question about a transcript using Google's Gemini API"""
    try:
        # Check if Gemini API is available
        if not check_gemini_availability():
            return None

        # Check if file exists
        if not os.path.exists(transcript_path):
            print(f"Error: Transcript file {transcript_path} does not exist.")
            return None

        # Read the transcript
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript_text = f.read()

        # Create a Gemini model instance
        if 'gemini_client' in globals():
            # The new SDK uses a different approach
            model = gemini_client.models.get(model='gemini-1.5-flash')
            model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            model = genai.GenerativeModel('gemini-1.5-flash')

        # Create the prompt with the question
        prompt = f"""
        Based on the following transcript, please answer this question:

        Question: {question}

        Transcript:
        {transcript_text}

        Provide a detailed and accurate answer based only on the information in the transcript.
        """

        # Generate the answer
        print("\nGenerating answer using Google's Gemini API...")
        response = model.generate_content(prompt)

        if not response or not response.text:
            print("Error: No response from Gemini API.")
            return None

        print("\nAnswer from Gemini:")
        print("=" * 60)
        print(response.text)
        print("=" * 60)

        return response.text

    except Exception as e:
        handle_gemini_error(e)
        return None

def save_transcript(audio_file_path, transcript_text, service="gemini"):
    """Save transcript to a file"""
    try:
        # Create the transcript filename
        audio_path = Path(audio_file_path)
        transcript_filename = f"{audio_path.stem}_{service}_transcript.txt"
        transcript_path = audio_path.parent / transcript_filename

        # Save the transcript
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(transcript_text)

        print(f"\nTranscript saved to: {transcript_path}")
        return str(transcript_path)

    except Exception as e:
        print(f"Error saving transcript: {str(e)}")
        return None

def get_mime_type(file_path):
    """Determine MIME type based on file extension"""
    extension = os.path.splitext(file_path)[1].lower()

    mime_types = {
        '.mp3': 'audio/mp3',
        '.wav': 'audio/wav',
        '.m4a': 'audio/m4a',
        '.aac': 'audio/aac',
        '.ogg': 'audio/ogg',
        '.flac': 'audio/flac',
        '.aiff': 'audio/aiff',
    }

    return mime_types.get(extension, 'audio/mpeg')  # Default to audio/mpeg if unknown

def handle_gemini_error(error):
    """Handle Gemini API errors with helpful messages"""
    error_message = str(error)
    print("\nGemini API Error:", error_message)

    if "API key not valid" in error_message or "authentication" in error_message.lower():
        print("\nTroubleshooting tips:")
        print("- Check that you've entered your Gemini API key correctly")
        print("- Verify your API key is still valid in your Google AI account")
        print("- Create a new API key if needed: https://ai.google.dev/gemini-api/docs/api-key")
    elif "quota" in error_message.lower() or "rate limit" in error_message.lower():
        print("\nTroubleshooting tips:")
        print("- You've reached your API usage limit")
        print("- Wait and try again later or check your API usage limits in your Google AI account")
    elif "file size" in error_message.lower() or "too large" in error_message.lower():
        print("\nTroubleshooting tips:")
        print("- The audio file is too large for Gemini API")
        print("- Try with a smaller audio file or split the file into smaller chunks")
    else:
        print("\nTroubleshooting tips:")
        print("- Check your internet connection")
        print("- Verify that the Google Gemini API is available")
        print("- Try again later or with a different audio file")

    print("\nFor technical support, please provide the following error details:")
    print(f"Error: {error_message}")

def chat_with_content(content_path, content_type="transcript"):
    """Start an interactive chat session with the content using Google's Gemini API"""
    try:
        # Check if Gemini API is available
        if not check_gemini_availability():
            return None

        # Check if file exists
        if not os.path.exists(content_path):
            print(f"Error: File {content_path} does not exist.")
            return None

        # Initialize chat session

        # Read the content
        if content_type == "transcript":
            with open(content_path, 'r', encoding='utf-8') as f:
                content_text = f.read()

            # Create a Gemini model instance with chat capability
            if 'gemini_client' in globals():
                # The new SDK uses a different approach
                model = gemini_client.models.get(model='gemini-1.5-pro')
                model = genai.GenerativeModel('gemini-1.5-pro')
            else:
                model = genai.GenerativeModel('gemini-1.5-pro')

            # Create system instruction
            system_instruction = f"You are an AI assistant that helps users understand and analyze the content of a transcript. "\
                               f"You will answer questions based only on the information in the following transcript:\n\n{content_text}"

            print("\n" + "=" * 60)
            print("CHAT WITH TRANSCRIPT CONTENT")
            print("=" * 60)
            print("You can now chat with the AI about the transcript content.")
            print("The AI will answer based on the information in the transcript.")
            print("Type 'exit', 'quit', or press Ctrl+C to end the chat.")

        elif content_type == "audio":
            # For audio, we'll use a different approach since we can't include the audio in every message

            print("\n" + "=" * 60)
            print("CHAT WITH AUDIO CONTENT")
            print("=" * 60)
            print("You can now chat with the AI about the audio content.")
            print("The AI will listen to the audio and answer your questions.")
            print("Type 'exit', 'quit', or press Ctrl+C to end the chat.")
            print("Note: Each question requires re-processing the audio, which may take time.")

            # No chat history needed for audio as each question is processed independently

        else:
            print(f"Error: Unsupported content type: {content_type}")
            return None

        # Start the chat loop
        while True:
            # Get user input
            user_input = input("\nYou: ")

            # Check if user wants to exit
            if user_input.lower() in ["exit", "quit", "bye", "goodbye"]:
                print("\nEnding chat session. Goodbye!")
                break

            # Process based on content type
            if content_type == "transcript":
                # Generate response
                print("\nAI is thinking...")
                response = model.generate_content(
                    contents=user_input,
                    generation_config={
                        "system_instruction": system_instruction
                    }
                )

                if not response or not response.text:
                    print("Error: No response from Gemini API.")
                    continue

                # Display response
                print("\nAI:")
                print(response.text)

            elif content_type == "audio":
                # For audio, we process each question independently
                response_text = ask_question_about_audio(content_path, user_input)

                if not response_text:
                    print("Error: Could not process audio question.")
                    continue

        return True

    except KeyboardInterrupt:
        print("\nChat session interrupted. Goodbye!")
        return None
    except Exception as e:
        handle_gemini_error(e)
        return None

def handle_gemini_transcription_option(audio_file_path):
    """Handle the Gemini transcription option for downloaded audio"""
    print("\n" + "=" * 60)
    print("GEMINI TRANSCRIPTION OPTION")
    print("=" * 60)
    print("The downloaded file contains audio that can be transcribed.")
    print("Google's Gemini API will be used for transcription.")
    print("The transcription will be saved as a text file.")

    transcribe_choice = input("\nWould you like to transcribe the audio using Google's Gemini API? (Press Enter for yes/n for no): ").lower()

    if transcribe_choice in ["", "yes", "y"]:
        transcript_path = transcribe_audio_with_gemini(audio_file_path)

        if transcript_path and os.path.exists(transcript_path):
            print(f"\nTranscription saved successfully to: {transcript_path}")

            print("\nWhat would you like to do with the content?")
            print("1. Summarize the transcript")
            print("2. Ask a single question about the content")
            print("3. Start an interactive chat about the transcript")
            print("4. Start an interactive chat with the original audio")
            print("5. Skip")

            content_choice = input("\nEnter your choice (1-5): ")

            if content_choice == "1":
                summary_path = summarize_transcript(transcript_path)
                if summary_path and os.path.exists(summary_path):
                    print(f"\nSummary saved successfully to: {summary_path}")

            elif content_choice == "2":
                question = input("\nEnter your question: ")
                ask_question_about_transcript(transcript_path, question)

            elif content_choice == "3":
                chat_with_content(transcript_path, "transcript")

            elif content_choice == "4":
                chat_with_content(audio_file_path, "audio")

            else:
                print("\nSkipping additional processing.")
    else:
        print("\nTranscription cancelled.")
