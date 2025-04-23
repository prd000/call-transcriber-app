import os
import tempfile
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from rev_ai.apiclient import RevAiAPIClient as ApiClient
from dotenv import load_dotenv
import time
from airtable_utils import save_call_to_airtable

# Load environment variables
# Remove explicit path loading, default should work now
# dotenv_path = os.path.join(os.path.dirname(__file__), '.env') 
# if os.path.exists(dotenv_path):
#    print(f"DEBUG: Found .env file at: {dotenv_path}")
#    load_dotenv(dotenv_path=dotenv_path)
# else:
#    print(f"DEBUG: .env file NOT found at: {dotenv_path}")
load_dotenv() # Use default loading

# --- Debugging Env Vars ---
print(f"DEBUG: REV_AI_API_KEY loaded as: {os.getenv('REV_AI_API_KEY')}") # Check Rev AI Key
print(f"DEBUG: AIRTABLE_API_KEY loaded as: {os.getenv('AIRTABLE_API_KEY')}")
print(f"DEBUG: AIRTABLE_BASE_ID loaded as: {os.getenv('AIRTABLE_BASE_ID')}")
print(f"DEBUG: AIRTABLE_TABLE_NAME loaded as: {os.getenv('AIRTABLE_TABLE_NAME')}")
# --------------------------

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'wav'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Set up Rev AI client
rev_ai_api_key = os.getenv('REV_AI_API_KEY')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if Rev AI API key is configured
    if not rev_ai_api_key:
        flash('Missing Rev AI API key. Please set the REV_AI_API_KEY environment variable.', 'error')
        return redirect(url_for('index'))
    
    # Check if a file was uploaded
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    prospect_name = request.form.get('prospect_name')
    prospect_email = request.form.get('prospect_email')
    call_type = request.form.get('call_type')
    call_outcome = request.form.get('call_outcome')
    reps = request.form.getlist('reps') # Use getlist for multiple values
    
    # Basic validation
    if not prospect_name or not call_type or not call_outcome or not reps:
        flash('Prospect Name, Call Type, Call Outcome, and at least one Rep are required.', 'error')
        return redirect(url_for('index'))
    
    # Check if file is empty
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('index'))
    
    # Check if file is allowed
    if not allowed_file(file.filename):
        flash('File format not supported. Please upload a .wav file.', 'error')
        return redirect(url_for('index'))
    
    # Save file to disk
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    try:
        # Initialize Rev AI client
        client = ApiClient(rev_ai_api_key)
        
        # Submit file for transcription
        job = client.submit_job_local_file(
            filepath, 
            metadata=f"CallTranscriber - {filename}",
            skip_diarization=False
        )
        
        # Store job ID and metadata in session
        session['job_id'] = job.id
        session['prospect_name'] = prospect_name
        session['prospect_email'] = prospect_email
        session['call_type'] = call_type
        session['call_outcome'] = call_outcome
        session['reps'] = reps # Store list of reps
        session['original_filename'] = filename # Store filename too
        
        flash('File uploaded successfully! Transcription is in progress...', 'success')
        return redirect(url_for('transcription_status'))
    
    except Exception as e:
        flash(f'Error submitting file to Rev AI: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/status')
def transcription_status():
    job_id = session.get('job_id')
    if not job_id:
        flash('No active transcription job found', 'error')
        return redirect(url_for('index'))
    
    client = ApiClient(rev_ai_api_key)
    try:
        job_details = client.get_job_details(job_id)
        status = job_details.status
        
        if status == 'transcribed':
            return redirect(url_for('show_transcription'))
        
        return render_template('status.html', status=status)
    except Exception as e:
        flash(f'Error checking transcription status: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/transcription')
def show_transcription():
    job_id = session.get('job_id')
    prospect_name = session.get('prospect_name')
    prospect_email = session.get('prospect_email')
    call_type = session.get('call_type')
    call_outcome = session.get('call_outcome')
    reps = session.get('reps') # Retrieve list of reps
    original_filename = session.get('original_filename') # Retrieve filename

    if not job_id:
        flash('No active transcription job found in session.', 'error')
        return redirect(url_for('index'))

    client = ApiClient(rev_ai_api_key)
    try:
        # Get transcription
        transcript = client.get_transcript_text(job_id)
        
        # Get transcript with speaker diarization
        transcript_obj = client.get_transcript_json(job_id)
        
        # Process transcript to extract speakers
        formatted_transcript = []
        current_speaker = None
        current_text = ""
        
        # Check if 'monologues' key exists and is a list
        if 'monologues' in transcript_obj and isinstance(transcript_obj['monologues'], list):
            for monologue in transcript_obj['monologues']:
                # Check if monologue is a dictionary and has required keys
                if isinstance(monologue, dict) and 'speaker' in monologue and 'elements' in monologue:
                    speaker = monologue['speaker']
                    
                    if speaker != current_speaker and current_text:
                        formatted_transcript.append({
                            "speaker": f"Speaker {current_speaker}", # Add "Speaker " prefix
                            "text": current_text.strip()
                        })
                        current_text = ""
                    
                    current_speaker = speaker
                    for element in monologue.get('elements', []):
                        # Check if element is a dictionary and has 'value' key
                        if isinstance(element, dict) and 'value' in element:
                             # Only append value if type is 'text'
                            if element.get('type') == 'text':
                                current_text += element['value'] + " " 
                            # Append punctuation directly without extra space    
                            elif element.get('type') == 'punct':
                                current_text = current_text.rstrip() + element['value'] + " " 
        
            # Add the last speaker's text
            if current_text:
                formatted_transcript.append({
                    "speaker": f"Speaker {current_speaker}", # Add "Speaker " prefix
                    "text": current_text.strip()
                })
        else:
             # Handle cases where 'monologues' might be missing or not a list
            flash('Could not process speaker diarization from the transcript.', 'warning')
            # Provide the raw transcript text as a fallback
            formatted_transcript.append({
                "speaker": "Transcript",
                "text": transcript
            })

        # --- Save to Airtable --- 
        call_data_for_airtable = {
            'prospect_name': prospect_name,
            'prospect_email': prospect_email,
            'call_type': call_type,
            'call_outcome': call_outcome,
            'reps': reps, # Add list of reps
            'formatted_transcript': formatted_transcript,
            'transcript': transcript, # Pass raw transcript too
            'job_id': job_id, # Pass job ID
            'filename': original_filename # Pass filename
        }
        if save_call_to_airtable(call_data_for_airtable):
            flash('Transcription successfully saved to Airtable!', 'success')
        else:
            # Error flash message is handled within save_call_to_airtable
            pass 
        # ------------------------

        return render_template('transcription.html', 
                               transcript=transcript, 
                               formatted_transcript=formatted_transcript)
    except Exception as e:
        flash(f'Error retrieving or processing transcription: {str(e)}', 'error')
        print(f"Error in /transcription route: {str(e)}") # Log detailed error
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True) 