# ai-report-generator/backend/app.py

import os
import sys
# Ensure redirect and url_for are imported from Flask
from flask import Flask, request, jsonify, abort, render_template, url_for, redirect # <<< CORRECTED IMPORT
from flask_cors import CORS
import random
import time
import werkzeug.utils
import secrets
import numpy as np

# --- Path Adjustments (Keep as is) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root_from_backend = os.path.abspath(os.path.join(current_dir, '..'))
if project_root_from_backend not in sys.path:
    sys.path.insert(0, project_root_from_backend)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# --- ML Function Import (Keep as is) ---
try:
    from audio_processor import process_audio_and_return_dialogue
    ML_FUNCTION_LOADED = True
    print("Successfully imported ML function from audio_processor.py")
except ImportError as e:
    # ... (dummy function for error handling - keep as is) ...
    print(f"### ERROR importing ML: {e} ###"); ML_FUNCTION_LOADED = False
    def process_audio_and_return_dialogue(a,w): return {"error": "Import failed - DUMMY"}
except Exception as e_gen:
     print(f"!!! General Error during ML import: {e_gen}"); ML_FUNCTION_LOADED = False
     def process_audio_and_return_dialogue(a,w): return {"error": "General import error - DUMMY"}


# --- Load .env (Keep as is) ---
from dotenv import load_dotenv
dotenv_path = os.path.join(project_root_from_backend, '.env')
if os.path.exists(dotenv_path):
     print(f"Flask App: Loading .env from: {dotenv_path}"); load_dotenv(dotenv_path=dotenv_path)
else:
     print(f"Flask App Warning: .env file not found at {dotenv_path}")

# --- Flask App Initialization with Correct Paths (Keep as is) ---
app = Flask(__name__,
            template_folder=os.path.join(project_root_from_backend, 'frontend', 'templates'),
            static_folder=os.path.join(project_root_from_backend, 'frontend', 'static')
            )
CORS(app)

# --- Configuration & In-Memory Storage (Keep as is) ---
UPLOAD_FOLDER = os.path.join(current_dir, 'temp_audio_uploads')
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
analysis_results = {}
job_status = {}

# --- HTML Serving Endpoints (Keep as is - they use url_for) ---
@app.route('/', methods=['GET'])
def serve_index_page():
    return render_template('index.html')

@app.route('/upload', methods=['GET'])
def serve_upload_page():
    return render_template('upload.html')

@app.route('/report/<string:job_id>', methods=['GET'])
def show_report_page(job_id):
    print(f"Serving report page for job_id: {job_id}")
    return render_template('report.html', job_id=job_id)

# --- API Endpoints ---
@app.route('/submit_audio_for_report', methods=['POST'])
def submit_audio_for_report():
    # ... (Your existing logic for this endpoint, which uses redirect and url_for) ...
    # Make sure the line looks like this after successful processing:
    # return redirect(url_for('show_report_page', job_id=job_id))
    # ...
    print("--- /submit_audio_for_report endpoint hit ---")
    if not ML_FUNCTION_LOADED: return "ML Service not available", 500
    if 'audioFile' not in request.files: return "No audio file part in request", 400
    file = request.files['audioFile']
    if file.filename == '': return "No file selected", 400

    report_type = request.form.get('reportType', 'brief')
    whisper_model_size = request.form.get('whisperModelSize', 'small')
    print(f"Received file: {file.filename}, Report Type: {report_type}, Whisper Model: {whisper_model_size}")

    if file:
        filename = werkzeug.utils.secure_filename(file.filename)
        if not filename: return "Invalid filename", 400
        temp_filename = f"{secrets.token_hex(8)}_{filename}"
        temp_audio_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
        job_id = None
        try:
            file.save(temp_audio_path)
            print(f"Audio saved to: {temp_audio_path}")
            print(f"Calling ML function with model size {whisper_model_size}...")
            result_data = process_audio_and_return_dialogue(temp_audio_path, whisper_model_size=whisper_model_size)
            print(f"ML function finished.")

            if result_data and result_data.get("error") is None:
                job_id = f"job_{secrets.token_hex(8)}"
                analysis_results[job_id] = {
                    "status": "completed",
                    "data": result_data,
                    "report_type_requested": report_type
                }
                print(f"Processed data stored for job_id: {job_id}")
                # <<< THIS IS WHERE REDIRECT AND URL_FOR ARE USED >>>
                return redirect(url_for('show_report_page', job_id=job_id))
            else:
                error_msg = result_data.get("error") if result_data else "Unknown ML Error"
                print(f"ML processing failed: {error_msg}")
                return render_template('upload.html', error=f"Processing failed: {error_msg}")
        except Exception as e:
             print(f"Error during processing: {e}")
             return render_template('upload.html', error=f"Server error: {str(e)}")
        finally:
            if os.path.exists(temp_audio_path):
                try: os.remove(temp_audio_path)
                except Exception as e_del: print(f"Warn: Failed delete {temp_audio_path}: {e_del}")
    else: return "Invalid file", 400


@app.route('/api/get_report_data/<string:job_id>', methods=['GET'])
def get_report_data_api(job_id):
    # (Keep logic as is)
    print(f"--- API /api/get_report_data/{job_id} hit ---")
    result_info = analysis_results.get(job_id)
    if result_info and result_info.get("status") == "completed":
        return jsonify(result_info.get("data")), 200
    elif result_info:
         return jsonify({"status": result_info.get("status"), "error": "Report not ready or failed"}), 202
    else:
        print(f"Job ID {job_id} not found in API.")
        abort(404, description=f"Analysis result for job ID {job_id} not found.")


@app.route('/get_status/<string:job_id>', methods=['GET'])
def get_job_status(job_id):
    # (Keep logic as is)
    status = "not_found"
    if job_id in analysis_results:
        status = analysis_results[job_id].get("status", "unknown")
    return jsonify({"job_id": job_id, "status": status})


if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(debug=True, host='0.0.0.0', port=5000)