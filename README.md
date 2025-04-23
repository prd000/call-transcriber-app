# Sales Call Transcriber

A Python web application to transcribe sales call recordings using Rev AI.

## Features

- Upload WAV audio files of sales calls
- Automatic transcription using Rev AI's API
- Speaker diarization to identify different speakers
- View transcription with speaker labels
- Copy transcription to clipboard

## Requirements

- Python 3.7+
- Rev AI API key 

## Setup

1. Clone this repository:
   ```
   git clone <repository-url>
   cd CallTranscriber
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your Rev AI API key:
   ```
   REV_AI_API_KEY=your_api_key_here
   ```

   You can get an API key from [Rev AI's website](https://www.rev.ai/).

## Usage

1. Start the application:
   ```
   python app.py
   ```

2. Open your browser and go to `http://127.0.0.1:5000`

3. Upload a WAV file of a sales call recording

4. Wait for the transcription to complete - this may take a few minutes depending on the length of the recording

5. View the transcription with speaker labels and copy to clipboard if needed

## File Structure

- `app.py`: The main Flask application
- `templates/`: HTML templates for the web interface
- `uploads/`: Directory where uploaded files are stored

## Notes

- Only WAV file format is supported
- Maximum file size is 100MB
- Transcription processing time depends on the file size and Rev AI's processing capacity 