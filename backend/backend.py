# ai-report-generator/backend/app.py

import os
import sys
from flask import Flask, request, jsonify, abort, render_template, url_for, redirect
from flask_cors import CORS
import random # Keep if used for anything else, or remove
import time
import werkzeug.utils
import secrets
import numpy as np # Keep if audio_processor or its deps still use it globally
from supabase import create_client, Client # <<< Import Supabase >>>

# --- Path Adjustments (Keep as is) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root_from_backend = os.path.abspath(os.path.join(current_dir, '..'))
# ... (rest of sys.path modifications as before) ...
if project_root_from_backend not in sys.path: sys.path.insert(0, project_root_from_backend)
if current_dir not in sys.path: sys.path.insert(0, current_dir)


# --- ML Function Import (Keep as is) ---
try:
    from audio_processor import process_audio_and_return_dialogue # This now returns processed_text too
    ML_FUNCTION_LOADED = True
    print("Successfully imported ML function from audio_processor.py")
except ImportError as e:
    # ... (dummy function for error handling - keep as is) ...
    print(f"### ERROR importing ML: {e} ###"); ML_FUNCTION_LOADED = False
    def process_audio_and_return_dialogue(a,w): return {"error": "Import failed - DUMMY"}
except Exception as e_gen:
     print(f"!!! General Error during ML import: {e_gen}"); ML_FUNCTION_LOADED = False
     def process_audio_and_return_dialogue(a,w): return {"error": "General import error - DUMMY"}

# --- Load .env ---
from dotenv import load_dotenv
dotenv_path = os.path.join(project_root_from_backend, '.env')
if os.path.exists(dotenv_path):
     print(f"Flask App: Loading .env from: {dotenv_path}"); load_dotenv(dotenv_path=dotenv_path)
else:
     print(f"Flask App Warning: .env file not found at {dotenv_path}")

# --- Initialize Supabase Client ---
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY") # This should be your Service Role Key for backend

supabase: Client = None # type: ignore # Initialize to None
SUPABASE_INITIALIZED = False

if not supabase_url or not supabase_key:
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print("ERROR: SUPABASE_URL or SUPABASE_KEY not found in .env.")
    print("Supabase integration will NOT work.")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
else:
    try:
        print(f"Initializing Supabase client with URL: {supabase_url[:20]}...")
        supabase = create_client(supabase_url, supabase_key)
        print("Supabase client initialized successfully.")
        SUPABASE_INITIALIZED = True
    except Exception as e_sb:
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"ERROR: Failed to initialize Supabase client: {e_sb}")
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

app = Flask(__name__,
            template_folder=os.path.join(project_root_from_backend, 'frontend', 'templates'),
            static_folder=os.path.join(project_root_from_backend, 'frontend', 'static')
            )
CORS(app)

# --- Configuration ---
UPLOAD_FOLDER = os.path.join(current_dir, 'temp_audio_uploads')
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- REMOVE In-Memory Storage Dictionaries ---
# analysis_results = {} # No longer used
# job_status = {}       # No longer used

# --- HTML Serving Endpoints (Keep as is) ---
@app.route('/', methods=['GET'])
def serve_index_page(): return render_template('index.html')

@app.route('/upload', methods=['GET'])
def serve_upload_page(): return render_template('upload.html')

@app.route('/report/<string:job_id>', methods=['GET']) # job_id here will be Supabase primary key
def show_report_page(job_id):
    print(f"Serving report page for job_id: {job_id}")
    return render_template('report.html', job_id=job_id)

# --- API Endpoints ---
# backend/app.py
# ... (Keep ALL your existing imports at the top: os, sys, Flask, CORS, random, time, werkzeug, secrets, numpy, supabase, load_dotenv)
# ... (Keep your existing sys.path modifications)
# ... (Keep your existing ML function import try-except block where ML_FUNCTION_LOADED is set)
# ... (Keep your existing .env loading)
# ... (Keep your existing Supabase client initialization where SUPABASE_INITIALIZED is set)
# ... (Keep app = Flask(...), CORS(app), UPLOAD_FOLDER config)
# ... (Keep HTML serving routes: serve_index_page, serve_upload_page, show_report_page)
# ... (Keep API routes: get_report_data_api, get_job_status)

@app.route('/process_audio', methods=['POST'])
def process_audio_endpoint():
    print("--------------------------------------")
    print("Received request at /process_audio")
    
    # <<< --- START OF ADDED DEBUG STATEMENTS --- >>>
    print(f"DEBUG Endpoint: Value of ML_FUNCTION_LOADED at entry: {ML_FUNCTION_LOADED}")
    print(f"DEBUG Endpoint: Value of SUPABASE_INITIALIZED at entry: {SUPABASE_INITIALIZED}")
    # You can also print sys.path again here if you suspect it changes during reloads
    # print(f"DEBUG Endpoint: Current sys.path at endpoint entry: {sys.path}")
    # <<< --- END OF ADDED DEBUG STATEMENTS --- >>>

    if not ML_FUNCTION_LOADED:
        print("DEBUG Endpoint: ML_FUNCTION_LOADED is False, returning error.") # Added for clarity
        return jsonify({"error": "ML processing module not loaded on server."}), 500
    if not SUPABASE_INITIALIZED: # Assuming you added this check from previous suggestions
        print("DEBUG Endpoint: SUPABASE_INITIALIZED is False, returning error.") # Added for clarity
        return jsonify({"error": "Supabase client not initialized on server."}), 500

    if 'audioFile' not in request.files:
        print("Error: No 'audioFile' part in request.")
        return jsonify({"error": "Missing 'audioFile' in request form data"}), 400

    file = request.files['audioFile']
    if file.filename == '':
        print("Error: No file selected.")
        return jsonify({"error": "No file selected"}), 400
    
    report_type_requested = request.form.get('reportType', 'brief')
    whisper_model_size = request.form.get('whisperModelSize', 'small')
    print(f"Received file: {file.filename}, Report Type: {report_type_requested}, Whisper Model: {whisper_model_size}")
    
    temp_audio_path = None 
    job_id_from_supabase = None 

    if file:
        filename = werkzeug.utils.secure_filename(file.filename)
        if not filename:
            return jsonify({"error": "Invalid filename"}), 400
        
        temp_filename = f"{secrets.token_hex(8)}_{filename}"
        temp_audio_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)

        try:
            file.save(temp_audio_path)
            print(f"Audio file saved temporarily to: {temp_audio_path}")

            print(f"Calling ML function for audio '{filename}' with model size {whisper_model_size}...")
            result_data = process_audio_and_return_dialogue(temp_audio_path, whisper_model_size=whisper_model_size)
            print(f"ML function finished.")

            if result_data is None or result_data.get("error"):
                error_msg = result_data.get("error") if result_data else "Unknown ML Error"
                print(f"ML processing failed: {error_msg}")
                # For now, let's not try to save to DB if ML fails, just return error to user
                # This simplifies debugging. We can add DB logging of errors later.
                return jsonify({"error": f"Audio processing failed: {error_msg}"}), 500 # Return 500 for ML error

            raw_transcript = result_data.get("full_transcript", "")
            dialogue_data = result_data.get("dialogue", [])
            processed_text = result_data.get("processed_text", "")

            print("Storing initial data in Supabase table 'transcripts_log'...")
            data_to_insert = {
                'audio_filename': filename,
                'raw_transcript': raw_transcript,
                'dialogue_json': dialogue_data,
                'processed_text': processed_text,
                'status': 'completed_preprocessing',
                'whisper_model_size': whisper_model_size,
                'report_type_requested': report_type_requested
            }
            
            # Ensure supabase client is used only if initialized
            if not supabase: # supabase is the global client instance
                 print("ERROR: Supabase client is None inside endpoint. Cannot proceed.")
                 # This should ideally be caught by SUPABASE_INITIALIZED at the top,
                 # but as a safeguard within the try block:
                 raise ConnectionError("Supabase client not available for database operation.")

            response = supabase.table('transcripts_log').insert(data_to_insert).execute()
            print(f"Supabase insert response: {response}")

            if response.data and len(response.data) > 0:
                job_id_from_supabase = response.data[0]['id'] 
                print(f"Data stored in Supabase with ID (job_id): {job_id_from_supabase}")
                return redirect(url_for('show_report_page', job_id=str(job_id_from_supabase))) # Ensure job_id is string for URL
            else:
                error_detail = response.error.message if response.error else "No data returned after insert"
                print(f"Error storing data in Supabase: {error_detail}")
                return render_template('upload.html', error=f"Failed to store transcript: {error_detail}")

        except Exception as e:
             print(f"General error during processing or Supabase interaction: {e}")
             import traceback
             traceback.print_exc() # Print full traceback for detailed debugging
             return render_template('upload.html', error=f"Server error: {str(e)}")
        finally:
            if temp_audio_path and os.path.exists(temp_audio_path):
                 try:
                     os.remove(temp_audio_path)
                     print(f"Removed temporary audio file: {temp_audio_path}")
                 except Exception as e_del:
                     print(f"Warning: Failed to delete temp audio {temp_audio_path}: {e_del}")
    else:
        return jsonify({"error": "Invalid file provided"}), 400




@app.route('/api/get_report_data/<string:job_id>', methods=['GET'])
def get_report_data_api(job_id):
    print(f"--- API /api/get_report_data/{job_id} hit ---")
    if not SUPABASE_INITIALIZED: return jsonify({"error": "Supabase client not initialized."}), 500
    try:
        # Fetch data from 'transcripts_log' table where 'id' matches job_id
        # Supabase primary keys are often UUIDs if auto-generated, or integers if you set it
        # If your 'id' column in Supabase is integer, convert job_id: int(job_id)
        # If it's UUID text, just use job_id as string.
        # For now, assuming job_id (Firebase push key like) matches text or you use a text PK
        
        # Let's assume the primary key 'id' for transcripts_log is what we are using as job_id
        # If it's an integer from a sequence, you might need to cast job_id
        # For now, assuming it's a text/uuid type that matches the generated job_id string
        response = supabase.table('transcripts_log').select("*").eq('id', job_id).maybe_single().execute()

        print(f"Supabase get_report_data response: {response}")
        if response.data:
            # The data needed by frontend is directly what's stored.
            # We add a "status" field for consistency with frontend polling logic,
            # even though the record itself has it.
            return_data = response.data
            return_data_with_status = {
                "status": response.data.get("status", "unknown"), # Get status from the record
                "data": return_data # Pass the whole Supabase record as 'data'
            }
            return jsonify(return_data_with_status), 200
        else:
            print(f"Job ID {job_id} not found in Supabase for get_report_data.")
            abort(404, description=f"Analysis result for job ID {job_id} not found.")
    except Exception as e:
         print(f"Error fetching result from Supabase for job {job_id}: {e}")
         abort(500, description="Error fetching result from database.")


@app.route('/get_status/<string:job_id>', methods=['GET'])
def get_job_status(job_id):
    print(f"--- API /get_status/{job_id} hit ---")
    if not SUPABASE_INITIALIZED: return jsonify({"job_id": job_id, "status": "error_db_conn"}), 500
    try:
        response = supabase.table('transcripts_log').select("status").eq('id', job_id).maybe_single().execute()
        if response.data and 'status' in response.data:
            return jsonify({"job_id": job_id, "status": response.data['status']})
        else:
            return jsonify({"job_id": job_id, "status": "not_found"}) # Or "unknown" if record exists but no status
    except Exception as e:
         print(f"Error fetching status from Supabase for job {job_id}: {e}")
         return jsonify({"job_id": job_id, "status": "error_fetching"}), 500

# --- Run the App ---
if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(debug=True, host='0.0.0.0', port=5000)