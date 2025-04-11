# YouTube Video & Audio Downloader with Transcription and AI Analysis

A Python application that allows you to download videos and audio from YouTube, with the option to transcribe audio using OpenAI's Whisper model or Google's Gemini API. The Gemini API integration also enables summarization and question answering based on the audio content.

## Features

- Download YouTube videos in high quality
- Download audio-only from YouTube videos
- Download both video and audio
- List available formats before downloading
- Specify custom format codes for advanced users
- Transcribe downloaded audio using OpenAI's Whisper model
- Transcribe, summarize, and ask questions about audio using Google's Gemini API
- Simple command-line interface
- Helpful error messages and troubleshooting suggestions

## Requirements

- Python 3.7 or higher
- FFmpeg (required for audio extraction and conversion)
- OpenAI API key (for OpenAI transcription feature)
- Google Gemini API key (for Gemini transcription, summarization, and Q&A features)
- python-magic library (for MIME type detection)

## Installation

1. Clone this repository or download the source code

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Install FFmpeg:
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg` or equivalent for your distribution

## Usage

1. Run the script:
   ```
   python main.py
   ```

2. Follow the prompts:
   - Enter the YouTube video URL
   - Specify download location (or press Enter for default directory)
   - Choose what to download:
     - Video only
     - Audio only
     - Both video and audio
     - List available formats first (recommended for troubleshooting)
   - If you choose to list formats, you can then select a download option or specify a custom format code
   - If audio is downloaded, you'll be asked if you want to transcribe it

3. For transcription:
   - You'll need an OpenAI API key
   - If not set as an environment variable, you'll be prompted to enter it
   - Transcription will be saved as a text file in the same location as the audio

## Project Structure

The application is organized into several modules:

- `main.py` - Entry point and user interface
- `downloader.py` - Functions for downloading videos and audio
- `transcriber.py` - Functions for transcribing audio with OpenAI
- `gemini_api.py` - Functions for transcribing, summarizing, and Q&A with Google Gemini
- `utils.py` - Utility functions for URL validation, file handling, and error handling
- `config.py` - Configuration and environment variable handling

## Environment Variables

This application uses environment variables for configuration. You can set these in a `.env` file in the project directory:

1. Create a `.env` file in the project directory:

2. Edit the `.env` file and add your configuration:

   ```
   # OpenAI API Key for transcription feature
   OPENAI_API_KEY=your_openai_api_key_here

   # Google Gemini API Key for advanced AI features
   GEMINI_API_KEY=your_gemini_api_key_here

   # Default download path (optional)
   DEFAULT_DOWNLOAD_PATH=C:\Downloads
   ```

### Setting up API Keys

#### OpenAI API Key

For the OpenAI transcription feature to work, you need an OpenAI API key:

1. Sign up at [OpenAI](https://platform.openai.com/signup)
2. Generate an API key in your account dashboard
3. Add it to your `.env` file as shown above

Alternatively, you can set it as a system environment variable:
   - **Windows**: `set OPENAI_API_KEY=your-api-key`
   - **macOS/Linux**: `export OPENAI_API_KEY=your-api-key`

#### Google Gemini API Key

For the Gemini AI features (transcription, summarization, Q&A) to work, you need a Google Gemini API key:

1. Go to [Google AI Studio](https://ai.google.dev/)
2. Sign in with your Google account
3. Navigate to the API section and create an API key
4. Add it to your `.env` file as shown above

Alternatively, you can set it as a system environment variable:
   - **Windows**: `set GEMINI_API_KEY=your-api-key`
   - **macOS/Linux**: `export GEMINI_API_KEY=your-api-key`

Note: This application uses the official `google-generativeai` Python SDK (v0.3.0 or higher). If you get an import error, you may need to install it manually:
```
pip install google-generativeai python-magic
```

If no API keys are found, you'll be prompted to enter them when using the respective features.

## Notes

- Transcription quality depends on the audio quality and the AI model used
- Transcription of long audio files may take some time
- Using the OpenAI API for transcription will incur charges based on your OpenAI account
- Using the Google Gemini API will incur charges based on your Google AI account
- The Gemini API has a 20MB file size limit for inline data (larger files use file upload API)
- The Gemini API supports audio formats including MP3, WAV, AIFF, AAC, OGG, and FLAC
- This application uses the official `google-generativeai` SDK for Gemini API integration

## Testing

To run the test suite:

```
python test_gemini.py
```

The test suite verifies:
- URL validation functionality
- Gemini API connectivity
- Text generation capabilities
- Audio transcription functionality
- Error handling

## Troubleshooting

### Format Not Available Error

If you encounter a "Requested format is not available" error:

1. Try using option 4 to list available formats first
2. Then choose option 5 to specify a custom format code
3. For audio-only downloads (option 2), try format codes like 140 (m4a), 251 (webm), or 250 (webm)
4. For video downloads, you can combine formats like "137+140" (video+audio)
5. If all else fails, try option 2 (Audio only) which has better compatibility

### PhantomJS Warning

If you see warnings about PhantomJS:

1. These are usually not critical and the download may still work
2. If downloads fail, you can install PhantomJS from https://phantomjs.org/download.html
3. After installing, make sure it's in your system PATH

### Other Issues

- Make sure you have the latest version of yt-dlp installed
- Some videos may have restrictions that prevent downloading
- For region-restricted videos, you may need to use a VPN

## License

This project is open source and available under the MIT License.
