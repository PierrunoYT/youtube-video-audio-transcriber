# YouTube Video & Audio Downloader with Transcription

A Python application that allows you to download videos and audio from YouTube, with the option to transcribe audio using OpenAI's Whisper large-v3 model.

## Features

- Download YouTube videos in high quality
- Download audio-only from YouTube videos
- Download both video and audio
- Transcribe downloaded audio using OpenAI's Whisper large-v3 model
- Simple command-line interface

## Requirements

- Python 3.7 or higher
- FFmpeg (required for audio extraction and conversion)
- OpenAI API key (for transcription feature)

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
   python youtube_downloader.py
   ```

2. Follow the prompts:
   - Enter the YouTube video URL
   - Specify download location (or press Enter for current directory)
   - Choose what to download (video, audio, or both)
   - If audio is downloaded, you'll be asked if you want to transcribe it

3. For transcription:
   - You'll need an OpenAI API key
   - If not set as an environment variable, you'll be prompted to enter it
   - Transcription will be saved as a text file in the same location as the audio

## Environment Variables

This application uses environment variables for configuration. You can set these in a `.env` file in the project directory:

1. Copy `.env.example` to `.env`:
   ```
   cp .env.example .env
   ```

2. Edit the `.env` file and add your configuration:

   ```
   # OpenAI API Key for transcription feature
   OPENAI_API_KEY=your_api_key_here

   # Default download path (optional)
   DEFAULT_DOWNLOAD_PATH=C:\Downloads
   ```

### Setting up OpenAI API Key

For the transcription feature to work, you need an OpenAI API key:

1. Sign up at [OpenAI](https://platform.openai.com/signup)
2. Generate an API key in your account dashboard
3. Add it to your `.env` file as shown above

Alternatively, you can set it as a system environment variable:
   - **Windows**: `set OPENAI_API_KEY=your-api-key`
   - **macOS/Linux**: `export OPENAI_API_KEY=your-api-key`

If no API key is found, you'll be prompted to enter it when using the transcription feature.

## Notes

- Transcription quality depends on the audio quality and OpenAI's model
- Transcription of long audio files may take some time
- Using the OpenAI API for transcription will incur charges based on your OpenAI account

## License

This project is open source and available under the MIT License.
