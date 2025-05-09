# ai-report-generator/backend/audio_processor.py

import os
import torch
import torchaudio
from pyannote.audio import Pipeline as DiarizationPipeline
from huggingface_hub import login
from dotenv import load_dotenv
import time
import warnings
from itertools import groupby
from operator import itemgetter
import string
import subprocess
import numpy as np
import whisper # Use the openai-whisper library directly

# --- Load Env Vars & Config ---
# Load .env file from the project root (two levels up)
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
if os.path.exists(dotenv_path):
    print(f"ML Script: Loading .env from: {dotenv_path}")
    load_dotenv(dotenv_path=dotenv_path)
else:
     print(f"ML Script Warning: .env file not found at {dotenv_path}")

HF_TOKEN = os.getenv("HUGGINGFACE_ACCESS_TOKEN_READ")
DIARIZATION_MODEL = "pyannote/speaker-diarization-3.1"
DEFAULT_WHISPER_MODEL = "openai/whisper-small" # This matches transformers, adjust if needed for openai-whisper lib
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# --- Suppress warnings ---
warnings.filterwarnings("ignore")


# --- Pre-load models LAZILY ---
diarization_pipeline_instance = None
whisper_model_instance = None
loaded_whisper_size = None

def _load_diarization_pipeline():
    global diarization_pipeline_instance
    if diarization_pipeline_instance is None:
        print(f"Loading diarization pipeline ({DIARIZATION_MODEL}) on {DEVICE}...")
        start_time = time.time()
        try:
            if HF_TOKEN: login(token=HF_TOKEN)
            diarization_pipeline_instance = DiarizationPipeline.from_pretrained(
                DIARIZATION_MODEL,
                use_auth_token=HF_TOKEN if HF_TOKEN else True
            ).to(DEVICE)
            print(f"Diarization pipeline loaded in {time.time() - start_time:.2f}s")
        except Exception as e:
            print(f"ERROR loading diarization pipeline: {e}")
            raise RuntimeError(f"Failed to load diarization model: {e}")
    return diarization_pipeline_instance

def _load_whisper_model(model_size="small"): # Defaulting to small here
    global whisper_model_instance, loaded_whisper_size
    # Map transformers size to openai-whisper size if needed (base, small, medium, large)
    valid_sizes = ['tiny', 'base', 'small', 'medium', 'large']
    if model_size not in valid_sizes:
        print(f"Warning: Invalid whisper model size '{model_size}'. Defaulting to 'small'.")
        model_size = 'small'

    if whisper_model_instance is None or loaded_whisper_size != model_size:
        print(f"Loading Whisper model ({model_size}) on {DEVICE}...")
        start_time = time.time()
        try:
            # Use device string directly for openai-whisper
            device_str = "cuda" if DEVICE.type == "cuda" else "cpu"
            whisper_model_instance = whisper.load_model(model_size, device=device_str)
            loaded_whisper_size = model_size
            print(f"Whisper model loaded in {time.time() - start_time:.2f}s")
        except Exception as e:
            print(f"ERROR loading Whisper model: {e}")
            raise RuntimeError(f"Failed to load Whisper model: {e}")
    return whisper_model_instance

# --- Conversion Helper ---
def convert_to_wav_16k_mono(input_path, output_path):
    print(f"Converting '{input_path}' to '{output_path}' (16kHz mono WAV)...")
    try:
        if not os.path.exists(input_path): return False
        command = ['ffmpeg','-i', input_path,'-ar', '16000','-ac', '1','-y', output_path]
        process = subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)
        print("FFmpeg stderr:", process.stderr)
        print("Conversion successful.")
        return True
    except FileNotFoundError: print("ERROR: ffmpeg not found."); return False
    except subprocess.TimeoutExpired: print("ERROR: FFmpeg conversion timed out."); return False
    except subprocess.CalledProcessError as e: print(f"ERROR during FFmpeg conversion: {e.stderr}"); return False
    except Exception as e: print(f"ERROR during conversion: {e}"); return False

# --- Speaker Label Helper ---
def get_speaker_label(speaker_id, unique_speakers):
    try: idx = unique_speakers.index(speaker_id); return string.ascii_uppercase[idx]
    except: return speaker_id

# --- THE CORE PROCESSING FUNCTION FOR THE BACKEND ---
def process_audio_and_return_dialogue(input_audio_path: str, whisper_model_size: str = DEFAULT_WHISPER_MODEL) -> dict | None:
    results = {"dialogue": [], "full_transcript": None, "error": None}
    converted_path = None
    needs_cleanup = False
    start_process_time = time.time()
    print(f"--- Starting Audio Processing for: {input_audio_path} ---")

    try:
        # 1. Ensure correct audio format
        converted_path = os.path.splitext(input_audio_path)[0] + "_16k_mono_temp.wav"
        if not convert_to_wav_16k_mono(input_audio_path, converted_path):
            raise ValueError("Audio conversion failed.")
        needs_cleanup = True
        audio_path_for_processing = converted_path

        # 2. Diarization
        pipeline = _load_diarization_pipeline()
        print("Running diarization...")
        start_time = time.time()
        diarization = pipeline(audio_path_for_processing)
        print(f"Diarization finished in {time.time() - start_time:.2f}s")
        diarization_segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            diarization_segments.append({"speaker": speaker, "start": turn.start, "end": turn.end})
        diarization_segments.sort(key=itemgetter('start'))
        unique_speakers = sorted(list(diarization.labels()))
        print(f"Diarization found {len(unique_speakers)} speakers: {unique_speakers}")

        # 3. Transcription
        model = _load_whisper_model(whisper_model_size)
        print(f"Running transcription with Whisper {whisper_model_size}...")
        start_time = time.time()
        # Use language='en' to force English decoding with openai-whisper library
        transcription_result = model.transcribe(audio_path_for_processing, fp16=False if DEVICE.type == 'cpu' else True, language='en')
        print(f"Transcription finished in {time.time() - start_time:.2f}s")
        results["full_transcript"] = transcription_result["text"].strip()

        # 4. Combine Results (Using simpler segment midpoint alignment)
        print("Combining results...")
        processed_dialogue = []
        if diarization_segments and "segments" in transcription_result:
            current_dialogue_text = ""
            current_speaker_label = None
            unique_speakers_list = unique_speakers # Use the list from diarization

            for segment_info in transcription_result["segments"]:
                segment_start = segment_info["start"]
                segment_end = segment_info["end"]
                segment_text = segment_info["text"].strip()
                segment_midpoint = segment_start + (segment_end - segment_start) / 2
                assigned_speaker = "Unknown"
                for turn in diarization_segments:
                    if segment_midpoint >= turn["start"] and segment_midpoint < turn["end"]:
                         assigned_speaker = get_speaker_label(turn["speaker"], unique_speakers_list)
                         break
                if assigned_speaker == current_speaker_label:
                     current_dialogue_text += " " + segment_text
                else:
                     if current_speaker_label is not None and current_dialogue_text:
                          processed_dialogue.append({"speaker": current_speaker_label, "text": current_dialogue_text})
                     current_speaker_label = assigned_speaker
                     current_dialogue_text = segment_text
            if current_speaker_label is not None and current_dialogue_text:
                 processed_dialogue.append({"speaker": current_speaker_label, "text": current_dialogue_text})
            results["dialogue"] = processed_dialogue
            print("Combined diarization and transcription.")
        elif results["full_transcript"]:
            print("Diarization failed or transcription segments missing, using raw transcript.")
            results["dialogue"] = [{"speaker": "Unknown", "text": results["full_transcript"]}]
        else:
            raise ValueError("Transcription failed to produce text.")

    except Exception as e:
        print(f"ERROR during audio processing: {e}")
        results["error"] = str(e)
        # import traceback; traceback.print_exc() # Uncomment for detailed debug

    finally:
        if needs_cleanup and converted_path and os.path.exists(converted_path):
            try: os.remove(converted_path); print(f"Removed temporary file: {converted_path}")
            except Exception as e_del: print(f"Warning: Failed remove {converted_path}: {e_del}")

    print(f"--- Finished Audio Processing (Total Time: {time.time() - start_process_time:.2f}s) ---")
    return results if results["dialogue"] or results["full_transcript"] else None

# --- Testing Block ---
if __name__ == '__main__':
    # To test this script directly:
    # 1. Ensure .env file is in the parent (project root) directory
    # 2. Ensure test audio file path is correct relative to *this file*
    # 3. Run: python audio_processor.py from within the backend directory
    print("Testing audio processor module...")
    test_audio = "../stt_audio.mp3" # Adjust if your test audio is elsewhere
    if not os.path.exists(test_audio):
         print(f"Test audio file not found at: {test_audio}")
    else:
         result = process_audio_and_return_dialogue(test_audio)
         # ... (rest of test print logic) ...
         if result and not result.get("error"):
            print("\n--- Processing Result ---")
            # ... (print dialogue/transcript) ...
         elif result and result.get("error"):
            print(f"\nProcessing failed with error: {result['error']}")
         else: print("\nProcessing failed.")