import os
import sys
from flask import Flask, request, jsonify, abort
from flask_cors import CORS # Import CORS
import random
import time
import werkzeug.utils
import secrets
import numpy as np # Keep if ML script still uses it internally via dependencies

# --- Adjust Import Path ---
# Add the directory containing this script (backend) to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
     sys.path.insert(0, current_dir)

# --- Import the ML processing function ---
try:
    # Import directly from the sibling file
    from audio_processor import process_audio_and_return_dialogue
    ML_FUNCTION_LOADED = True
    print("Successfully imported ML function from audio_processor.py")
except ImportError as e:
    print(f"############################################################")
    print(f"ERROR: Could not import ML function from audio_processor.py: {e}")
    print(f"Ensure audio_processor.py is in the same directory as backend.py ({current_dir})")
    print(f"Python Path: {sys.path}")
    print(f"############################################################")
    ML_FUNCTION_LOADED = False
    # Define a dummy function
    def process_audio_and_return_dialogue(audio_path: str, whisper_model_size: str = "base") -> dict | None:
         print("WARN: Using dummy ML function due to import error!")
         time.sleep(2)
         return {"dialogue": [{"speaker": "Dummy", "text": "ML function failed to import."}], "full_transcript": "ML function failed to import.", "error": "Import failed"}
except Exception as e_gen: # Catch other potential errors during import
     print(f"!!! General Error during ML import: {e_gen}")
     ML_FUNCTION_LOADED = False
     def process_audio_and_return_dialogue(audio_path: str, whisper_model_size: str = "base") -> dict | None:
          print("WARN: Using dummy ML function due to general import error!")
          time.sleep(2)
          return {"dialogue": [{"speaker": "Dummy", "text": "ML function general import error."}], "full_transcript": "ML function general import error.", "error": "General import error"}

# --- Load environment variables ---
# Looks for .env in the parent directory (project root)
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(dotenv_path):
     print(f"Loading .env from: {dotenv_path}")
     load_dotenv(dotenv_path=dotenv_path)
else:
     print(f"Warning: .env file not found at {dotenv_path}")


app = Flask(__name__)
CORS(app) # Enable CORS

# --- Configuration ---
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'temp_audio_uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- In-Memory Storage ---
analysis_results = {}
job_status = {}

# --- API Endpoints ---

@app.route('/process_audio', methods=['POST'])
def process_audio_endpoint():
    print("--------------------------------------")
    print("Received request at /process_audio")
    if not ML_FUNCTION_LOADED: return jsonify({"error": "ML processing module not loaded."}), 500
    if 'audioFile' not in request.files: return jsonify({"error": "Missing 'audioFile' in form data"}), 400
    file = request.files['audioFile'];
    if file.filename == '': return jsonify({"error": "No file selected"}), 400
    whisper_size = request.form.get('whisperModelSize', 'small') # Get model size from form
    if file:
        filename = werkzeug.utils.secure_filename(file.filename)
        if not filename: return jsonify({"error": "Invalid filename"}), 400
        temp_filename = f"{secrets.token_hex(8)}_{filename}"
        temp_audio_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
        job_id = f"job_{secrets.token_hex(8)}"; print(f"Generated Job ID: {job_id}")
        job_status[job_id] = "processing"; analysis_results[job_id] = {"status": "processing", "data": None}
        try:
            file.save(temp_audio_path); print(f"Audio saved to: {temp_audio_path}")
            # --- Call ML function ---
            print(f"Calling ML function for job {job_id} with model size {whisper_size}...")
            result_data = process_audio_and_return_dialogue(temp_audio_path, whisper_model_size=whisper_size)
            print(f"ML function finished for job {job_id}.")
            # --- Store results ---
            if result_data and result_data.get("error") is None:
                 job_status[job_id] = "completed"; analysis_results[job_id]["status"] = "completed"; analysis_results[job_id]["data"] = result_data
                 print(f"Stored successful analysis for job ID: {job_id}"); return jsonify({"message": "Audio processing started successfully.", "job_id": job_id}), 202
            else:
                 job_status[job_id] = "failed"; analysis_results[job_id]["status"] = "failed"; analysis_results[job_id]["data"] = result_data
                 print(f"Error: ML processing failed for job ID: {job_id}. Error: {result_data.get('error') if result_data else 'Unknown ML Error'}")
                 return jsonify({"message": "Audio processing initiated but failed.", "job_id": job_id}), 202
        except Exception as e:
             print(f"Error during file save or ML call for job {job_id}: {e}"); job_status[job_id] = "failed"; analysis_results[job_id]["status"] = "failed"; analysis_results[job_id]["data"] = {"error": f"Backend error: {str(e)}"}
             return jsonify({"message": "Server error during processing.", "job_id": job_id}), 500
        finally: # --- Cleanup ---
            if os.path.exists(temp_audio_path):
                try: os.remove(temp_audio_path); print(f"Removed temp file: {temp_audio_path}")
                except Exception as e_del: print(f"Warning: Failed delete {temp_audio_path}: {e_del}")
    else: return jsonify({"error": "Invalid file provided"}), 400

@app.route('/get_result/<string:job_id>', methods=['GET'])
def get_analysis_result(job_id):
    print("--------------------------------------"); print(f"Received request for result ID: {job_id}")
    result_info = analysis_results.get(job_id)
    if result_info: print(f"Returning result/status for job ID: {job_id}"); return jsonify(result_info), 200
    else: print(f"Job ID {job_id} not found."); abort(404, description=f"Analysis result for job ID {job_id} not found.")

@app.route('/get_status/<string:job_id>', methods=['GET'])
def get_job_status(job_id):
    status = job_status.get(job_id, "not_found"); return jsonify({"job_id": job_id, "status": status})

# --- Run the App ---
if __name__ == '__main__':
    # To run this:
    # 1. Navigate terminal to PARENT directory (AI-REPORT-GENERATOR)
    # 2. Activate venv (e.g., backend/venv/Scripts/activate)
    # 3. Run: python backend/app.py (renamed from backend.py)
    print("Starting Flask server...")
    app.run(debug=True, host='0.0.0.0', port=5000)