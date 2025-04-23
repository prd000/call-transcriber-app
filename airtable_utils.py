import os
import json
from pyairtable import Api
from flask import flash

def prepare_readable_transcript(formatted_transcript):
    """Converts the diarized transcript list into a readable multi-line string."""
    lines = []
    if isinstance(formatted_transcript, list):
        for item in formatted_transcript:
            speaker = item.get("speaker", "Unknown Speaker")
            text = item.get("text", "")
            lines.append(f"{speaker}: {text}")
    return "\n".join(lines)

def prepare_json_transcript(formatted_transcript):
    """Converts the diarized transcript list into a JSON string."""
    try:
        return json.dumps(formatted_transcript, ensure_ascii=False)
    except TypeError:
        return "[]" # Return empty JSON array on error

def save_call_to_airtable(call_data):
    """Saves call data, including transcript and metadata, to Airtable.

    Args:
        call_data (dict): A dictionary containing call information.
                          Expected keys: 'prospect_name', 'prospect_email',
                          'call_type', 'call_outcome', 'reps',
                          'formatted_transcript'.
    """
    # --- Get credentials INSIDE the function --- 
    airtable_api_key = os.getenv('AIRTABLE_API_KEY')
    airtable_base_id = os.getenv('AIRTABLE_BASE_ID')
    airtable_table_name = os.getenv('AIRTABLE_TABLE_NAME')
    # -----------------------------------------
    
    # Check if credentials were loaded correctly *now*
    if not all([airtable_api_key, airtable_base_id, airtable_table_name]):
        flash('Airtable integration is not configured. Please set AIRTABLE_API_KEY, AIRTABLE_BASE_ID, and AIRTABLE_TABLE_NAME environment variables in .env and restart the app.', 'warning')
        print("Airtable credentials missing in environment variables when trying to save.") # Log for server console
        # Optionally add a print here to show what was found, e.g.:
        # print(f"DEBUG (save fn): Key={airtable_api_key}, Base={airtable_base_id}, Table={airtable_table_name}")
        return False

    try:
        # Use the locally retrieved credentials
        api = Api(airtable_api_key)
        table = api.get_table(airtable_base_id, airtable_table_name)

        # Prepare the data payload for Airtable, matching column names
        airtable_payload = {
            'Prospect Name': call_data.get('prospect_name', 'N/A'),
            'Prospect Email': call_data.get('prospect_email'),
            'Call Type': call_data.get('call_type', 'N/A'),
            'Call Outcome': call_data.get('call_outcome', 'N/A'),
            'Rep(s)': call_data.get('reps', []),
            'String Transcript': prepare_readable_transcript(call_data.get('formatted_transcript', [])),
            'JSON Transcript': prepare_json_transcript(call_data.get('formatted_transcript', [])),
            # Optional fields (uncomment and ensure columns exist in Airtable if needed)
            # 'File Name': call_data.get('filename', ''),
            # 'Transcription Job ID': call_data.get('job_id', ''),
            # 'Raw Transcript': call_data.get('transcript', '') # If you have a column for the raw text
        }

        # Make sure your Airtable table has columns named exactly:
        # 'Prospect Name', 'Prospect Email', 'Call Type' (Single Select/Text),
        # 'Call Outcome', 'Rep(s)' (Multiple Select),
        # 'String Transcript' (Long Text), 'JSON Transcript' (Long Text)

        airtable_payload = {k: v for k, v in airtable_payload.items() if v is not None}

        table.create(airtable_payload)
        print(f"Successfully saved call for {call_data.get('prospect_name')} to Airtable.")
        return True

    except Exception as e:
        flash(f'Error saving data to Airtable: {str(e)}', 'error')
        print(f"Error saving to Airtable: {str(e)}") 
        return False 