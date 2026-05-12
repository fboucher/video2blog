#!/usr/bin/env python3
import io
import hashlib
import json
import os
import re
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List
from urllib.parse import urlparse

from datetime import datetime, timezone, timedelta

from flask import Flask, render_template, request, jsonify, send_file, url_for
from werkzeug.utils import secure_filename

from keyframe_extractor import extract_keyframes, extract_frames_at_timestamps
import db_service
import gemini_service
from editing_routes import editing_bp


# Constants
APP_VERSION = os.environ.get('APP_VERSION', '0.5.1-preview')
UPLOAD_FOLDER = '/app/uploads'
OUTPUT_FOLDER = '/app/output'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv'}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
GEMINI_CACHE_TTL_HOURS = 48

# Flask app configuration
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Ensure directories exist
Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
Path(OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)

# Initialize database
db_service.init_db()

# Register blueprints
app.register_blueprint(editing_bp)


def sanitize_filename(video_name: str) -> str:
    """Return a filesystem-safe filename with a unique suffix.

    Strips special characters from *video_name*, then appends a short
    random suffix so concurrent uploads of identically-named files don't
    collide.
    """
    import uuid
    name, ext = os.path.splitext(video_name)
    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
    suffix = uuid.uuid4().hex[:8]
    return f"{safe_name}_{suffix}{ext}"


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed.

    Args:
        filename: Name of the file to check.

    Returns:
        True if file extension is allowed, False otherwise.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def is_valid_url(url: str) -> bool:
    """Validate URL format using regex.

    Args:
        url: The URL to validate.

    Returns:
        True if URL is valid, False otherwise.
    """
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None


def _resolve_gemini_uri(filename: str, filepath: str | None = None) -> tuple[str, str]:
    """Return (gemini_uri, cache_status), uploading from disk only when needed.

    URL-based videos (where gemini_file_uri is a public URL) are always
    treated as fresh — Gemini handles them natively and they never expire.
    """
    gemini_info = db_service.get_gemini_file_info(filename)

    if gemini_info and gemini_info.get("uri"):
        uri = gemini_info["uri"]
        # URL refs are handled natively by Gemini — no TTL applies
        if uri.startswith("http://") or uri.startswith("https://"):
            return uri, "fresh"

    cache = _gemini_cache_status(gemini_info)

    if cache.get("gemini_cache_status") == "fresh":
        return gemini_info["uri"], "fresh"

    if not filepath or not os.path.exists(filepath):
        raise FileNotFoundError(f"Local video file not found for re-upload: {filepath!r}")

    uri = gemini_service.upload_video(filepath)
    timestamp = datetime.now(timezone.utc).isoformat()
    db_service.update_gemini_upload(filename, uri, timestamp)
    return uri, "re-uploaded"


@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html', version=APP_VERSION)


GEMINI_CACHE_TTL_HOURS = 48


def _gemini_cache_status(gemini_info: dict) -> dict:
    """Compute gemini_cache_status and optional expires_in_hours from DB Gemini info."""
    if not gemini_info or not gemini_info.get("uri"):
        return {"gemini_cache_status": "not_uploaded"}
    uploaded_at_str = gemini_info.get("uploaded_at")
    if not uploaded_at_str:
        return {"gemini_cache_status": "not_uploaded"}
    try:
        uploaded_at = datetime.fromisoformat(uploaded_at_str)
        if uploaded_at.tzinfo is None:
            uploaded_at = uploaded_at.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - uploaded_at).total_seconds() / 3600
        if age_hours < GEMINI_CACHE_TTL_HOURS:
            return {
                "gemini_cache_status": "fresh",
                "expires_in_hours": int(GEMINI_CACHE_TTL_HOURS - age_hours),
            }
        return {"gemini_cache_status": "expired"}
    except Exception:
        return {"gemini_cache_status": "not_uploaded"}


@app.route('/videos/list')
def list_all_videos():
    """List all videos (local files + URL-based) with Gemini cache status.

    Returns:
        JSON with video list; each entry includes id, name, source,
        local_filename, gemini_cache_status, can_select, can_delete_local,
        and for fresh local videos, expires_in_hours.
    """
    import cv2

    # Build a lookup map of DB records keyed by local_filename
    all_syncs = db_service.list_all_syncs()
    db_by_filename = {r['local_filename']: r for r in all_syncs}

    videos = []

    # --- Local files ---
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        for filename in sorted(os.listdir(app.config['UPLOAD_FOLDER'])):
            if not allowed_file(filename):
                continue
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file_stats = os.stat(filepath)

            cap = cv2.VideoCapture(filepath)
            fps = duration = 0
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = total_frames / fps if fps > 0 else 0
                cap.release()

            db_record = db_by_filename.get(filename, {})
            gemini_info = db_service.get_gemini_file_info(filename)
            cache = _gemini_cache_status(gemini_info)

            frames_folder = Path(filename).stem
            frames_dir = os.path.join(app.config['OUTPUT_FOLDER'], frames_folder)
            has_frames = os.path.isdir(frames_dir) and any(
                f.endswith('.jpg') for f in os.listdir(frames_dir)
            )
            draft_info = db_service.get_latest_draft_by_video_id(filename)
            entry = {
                'id': db_record.get('id'),
                'name': db_record.get('video_name', filename),
                'source': 'local_only',
                'local_filename': filename,
                'filename': filename,
                'filepath': filepath,
                'size': file_stats.st_size,
                'modified': file_stats.st_mtime,
                'duration': duration,
                'fps': fps,
                'gemini_uri': gemini_info['uri'] if gemini_info else None,
                'can_select': True,
                'can_delete_local': True,
                'has_draft': draft_info is not None,
                'draft_id': draft_info['id'] if draft_info else None,
                'has_frames': has_frames,
                'frames_folder': frames_folder if has_frames else None,
            }
            entry.update(cache)
            videos.append(entry)

    # Track local filenames already added so URL records that were converted
    # to local files don't appear twice.
    local_filenames_added = {v['local_filename'] for v in videos}

    # --- URL-based videos (no local file) ---
    for record in all_syncs:
        lf = record.get('local_filename', '')
        if not record.get('source_url') or not lf.startswith('url-'):
            continue
        if lf in local_filenames_added:
            continue
        draft_info = db_service.get_latest_draft_by_video_id(lf)
        entry = {
            'id': record['id'],
            'name': record.get('video_name', lf),
            'source': 'url',
            'local_filename': lf,
            'filename': lf,
            'gemini_cache_status': 'fresh',
            'duration': 0,
            'size': 0,
            'fps': 0,
            'can_select': True,
            'can_delete_local': True,
            'modified': 0,
            'has_draft': draft_info is not None,
            'draft_id': draft_info['id'] if draft_info else None,
            'has_frames': False,
            'frames_folder': None,
        }
        videos.append(entry)

    videos.sort(key=lambda v: -v['modified'])
    return jsonify({'videos': videos})

@app.route('/list-uploads')
def list_uploads():
    """List all video files in the uploads folder.
    
    Returns:
        JSON list of available video files.
    """
    video_files = []
    
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if allowed_file(filename):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file_stats = os.stat(filepath)
                video_files.append({
                    'filename': filename,
                    'filepath': filepath,
                    'size': file_stats.st_size,
                    'modified': file_stats.st_mtime
                })
    
    # Sort by modification time, newest first
    video_files.sort(key=lambda x: x['modified'], reverse=True)
    
    return jsonify({'files': video_files})


@app.route('/select-file', methods=['POST'])
def select_file():
    """Select an existing file from uploads folder.
    
    Returns:
        JSON response with file information.
    """
    data = request.json
    
    if not data or 'filename' not in data:
        return jsonify({'error': 'No filename provided'}), 400
    
    filename = data['filename']
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    if not allowed_file(filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    # Get video info
    import cv2
    cap = cv2.VideoCapture(filepath)
    if not cap.isOpened():
        return jsonify({'error': 'Unable to open video file'}), 400
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    
    return jsonify({
        'success': True,
        'filename': filename,
        'filepath': filepath,
        'duration': duration,
        'fps': fps,
        'total_frames': total_frames,
        'width': width,
        'height': height
    })


@app.route('/delete-file', methods=['POST'])
def delete_file():
    """Delete a video file from uploads folder.
    
    Returns:
        JSON response with deletion status.
    """
    data = request.json
    
    if not data or 'filename' not in data:
        return jsonify({'error': 'No filename provided'}), 400
    
    filename = data['filename']
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    try:
        # URL-based videos have no local file — just remove the DB record
        if filename.startswith('url-'):
            db_service.delete_sync_by_filename(filename)
            return jsonify({'success': True, 'message': f'Deleted {filename}'})

        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404

        # Delete the local file then the DB record
        os.remove(filepath)
        db_service.delete_sync_by_filename(filename)

        return jsonify({'success': True, 'message': f'Deleted {filename}'})
    except Exception as e:
        return jsonify({'error': f'Failed to delete file: {str(e)}'}), 500


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle video file upload.

    Saves the file locally, then asynchronously uploads to Gemini Files API
    when GEMINI_API_KEY is configured. Gemini errors do not fail the response.

    Returns:
        JSON response with upload status and file information.
    """
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    file = request.files['video']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # Save uploaded file locally
    file.save(filepath)

    # Get video info
    import cv2
    cap = cv2.VideoCapture(filepath)
    if not cap.isOpened():
        os.remove(filepath)
        return jsonify({'error': 'Unable to open video file'}), 400

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    video_name = request.form.get('video_name', '').strip() or Path(filename).stem

    # Register the file in the DB so Gemini info can be stored later
    db_service.add_sync(local_filename=filename, video_name=video_name)

    # Upload to Gemini Files API if configured
    gemini_uri = None
    gemini_cache_status = 'not_uploaded'
    gemini_upload_error = None

    if gemini_service.is_configured():
        try:
            gemini_uri = gemini_service.upload_video(filepath)
            timestamp = datetime.now(timezone.utc).isoformat()
            db_service.update_gemini_upload(filename, gemini_uri, timestamp)
            gemini_cache_status = 'fresh'
        except Exception as exc:
            gemini_upload_error = str(exc)
            print(f"[upload] Gemini upload failed for {filename}: {exc}")

    response = {
        'success': True,
        'filename': filename,
        'filepath': filepath,
        'duration': duration,
        'fps': fps,
        'total_frames': total_frames,
        'width': width,
        'height': height,
        'gemini_uri': gemini_uri,
        'gemini_cache_status': gemini_cache_status,
    }
    if gemini_upload_error:
        response['gemini_upload_error'] = gemini_upload_error

    return jsonify(response)


@app.route('/videos/upload-to-gemini', methods=['POST'])
def upload_to_gemini():
    """Re-upload a locally stored video to Gemini Files API.

    Body: {"filename": "video.mp4"}

    Returns:
        JSON with status, uri, and gemini_cache_status.
    """
    data = request.get_json()
    if not data or 'filename' not in data:
        return jsonify({'error': 'filename is required'}), 400

    filename = data['filename']
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404

    if not gemini_service.is_configured():
        return jsonify({'error': 'GEMINI_API_KEY is not configured'}), 503

    try:
        uri = gemini_service.upload_video(filepath)
        timestamp = datetime.now(timezone.utc).isoformat()
        db_service.update_gemini_upload(filename, uri, timestamp)
        return jsonify({'status': 'ok', 'uri': uri, 'gemini_cache_status': 'fresh'})
    except Exception as exc:
        print(f"[upload-to-gemini] Failed for {filename}: {exc}")
        return jsonify({'error': str(exc)}), 500


@app.route('/videos/extract-frames-url', methods=['POST'])
def extract_frames_url():
    """Download a URL video via yt-dlp and run keyframe extraction.

    Expects JSON body: {"filename": "<pseudo-filename>", "timestamps": "10.5,25.0"}
    If timestamps are provided they are used for extraction; otherwise scene detection is used.
    Returns JSON: {"frames": [...], "filename": "<local_filename>"} or error.
    """
    data = request.get_json()
    filename = data.get('filename') if data else None

    if not filename:
        return jsonify({'error': 'filename required'}), 400

    record = db_service.get_sync_by_filename(filename)
    if not record:
        return jsonify({'error': 'video not found'}), 404

    source_url = record.get('source_url')
    if not source_url:
        return jsonify({'error': 'no source URL for this video'}), 400

    upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
    local_stem = os.path.splitext(filename)[0]
    output_path = os.path.join(upload_folder, local_stem)

    try:
        local_path = gemini_service.download_video_from_url(source_url, output_path)
        local_filename = os.path.basename(local_path)
    except Exception as e:
        return jsonify({'error': f'Download failed: {e}'}), 500

    db_service.convert_url_video_to_local(filename, local_filename)

    output_dir = os.path.join(app.config['OUTPUT_FOLDER'], Path(local_filename).stem)
    timestamps_raw = data.get('timestamps') if data else None
    try:
        if timestamps_raw:
            timestamps = [float(t.strip()) for t in str(timestamps_raw).split(',') if t.strip()]
            frames_per_ts = int(data.get('frames_per_timestamp', 1))
            results = extract_frames_at_timestamps(local_path, output_dir, timestamps, frames_per_ts)
        else:
            results = extract_keyframes(local_path, output_dir)
        frame_files = sorted(f for f in os.listdir(output_dir) if f.endswith('.jpg'))
        return jsonify({
            'success': True,
            'filename': local_filename,
            'total_frames': len(results),
            'frames': frame_files[:20],
            'all_frames_count': len(frame_files),
            'output_dir': output_dir,
        })
    except Exception as e:
        return jsonify({'error': f'Frame extraction failed: {e}'}), 500


@app.route('/upload-from-url', methods=['POST'])
def upload_from_url():
    """Register a video URL for Gemini Q&A without downloading the file.

    Flow:
    1. Validate URL format
    2. Return existing record if this URL was already registered
    3. Generate a pseudo-filename (url-<md5>) as the DB key
    4. Store the URL as the Gemini file reference (no upload performed)
    5. Return qa_ready signal for the frontend
    """
    data = request.get_json()

    if not data or 'url' not in data:
        return jsonify({'error': 'No URL provided'}), 400

    video_url = data['url'].strip()

    if not is_valid_url(video_url):
        return jsonify({'error': 'Invalid URL format. Must start with http:// or https://'}), 400

    # Return existing record if this URL was already registered
    existing = db_service.get_video_by_url(video_url)
    if existing:
        return jsonify({
            'filename': existing['local_filename'],
            'gemini_cache_status': 'fresh',
            'source': 'url',
            'qa_ready': True,
        })

    # Derive a stable pseudo-filename from the URL
    url_hash = hashlib.md5(video_url.encode()).hexdigest()[:12]
    pseudo_filename = f"url-{url_hash}"

    video_name = data.get('video_name') or pseudo_filename

    # Register the record in the DB (no local file created)
    db_service.add_sync(
        local_filename=pseudo_filename,
        video_name=video_name,
        sync_status='synced',
        source_url=video_url,
    )

    # Obtain the URL ref from gemini_service and persist it as the file URI
    url_ref = gemini_service.upload_from_url(video_url)
    db_service.update_gemini_upload(
        pseudo_filename,
        url_ref,
        datetime.now(timezone.utc).isoformat(),
    )

    return jsonify({
        'filename': pseudo_filename,
        'gemini_cache_status': 'fresh',
        'source': 'url',
        'qa_ready': True,
    })


@app.route('/extract', methods=['POST'])
def extract():
    """Extract frames based on user parameters.
    
    Returns:
        JSON response with extraction results.
    """
    data = request.json
    
    if not data or 'filepath' not in data:
        return jsonify({'error': 'No filepath provided'}), 400
    
    filepath = data['filepath']
    if not os.path.exists(filepath):
        return jsonify({'error': 'Video file not found'}), 404
    
    mode = data.get('mode', 'scene')
    filename = os.path.basename(filepath)
    output_dir = os.path.join(app.config['OUTPUT_FOLDER'], Path(filename).stem)
    
    try:
        if mode == 'timestamp':
            # Timestamp extraction mode
            timestamps_str = data.get('timestamps', '')
            if not timestamps_str:
                return jsonify({'error': 'No timestamps provided'}), 400
            
            try:
                timestamps = [float(ts.strip()) for ts in timestamps_str.split(',')]
            except ValueError:
                return jsonify({'error': 'Invalid timestamp format. Use comma-separated numbers'}), 400
            
            frames_per_timestamp = int(data.get('frames_per_timestamp', 3))
            
            results = extract_frames_at_timestamps(
                filepath,
                output_dir,
                timestamps,
                frames_per_timestamp
            )
            
            metadata_file = 'timestamp_frames_metadata.json'
            
        else:
            # Scene detection mode
            threshold = float(data.get('threshold', 0.3))
            max_frames = int(data.get('max_frames', 100))
            
            results = extract_keyframes(
                filepath,
                output_dir,
                threshold,
                max_frames
            )
            
            metadata_file = 'keyframes_metadata.json'
        
        # Get list of extracted frame files
        frame_files = [f for f in os.listdir(output_dir) if f.endswith('.jpg')]
        frame_files.sort()
        
        return jsonify({
            'success': True,
            'output_dir': output_dir,
            'total_frames': len(results),
            'frames': frame_files[:20],  # Return first 20 for preview
            'metadata_file': metadata_file,
            'all_frames_count': len(frame_files)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/list-frames/<path:folder>')
def list_frames_in_folder(folder):
    """Return sorted list of .jpg filenames in an output subfolder."""
    folder_path = os.path.join(app.config['OUTPUT_FOLDER'], folder)
    if not os.path.isdir(folder_path):
        return jsonify({'frames': []})
    frames = sorted(f for f in os.listdir(folder_path) if f.endswith('.jpg'))
    return jsonify({'frames': frames})


@app.route('/frames/<path:filename>')
def serve_frame(filename):
    """Serve extracted frame images.
    
    Args:
        filename: Path to the frame file (relative to output folder).
    
    Returns:
        The requested image file.
    """
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='image/jpeg')
    return jsonify({'error': 'Frame not found'}), 404


@app.route('/metadata/<path:filename>')
def serve_metadata(filename):
    """Serve metadata JSON files.
    
    Args:
        filename: Path to the metadata file (relative to output folder).
    
    Returns:
        The requested JSON file.
    """
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='application/json')
    return jsonify({'error': 'Metadata not found'}), 404


@app.route('/download-all/<path:job_name>')
def download_all_frames(job_name):
    """Download all frames from a job as a ZIP file.
    
    Args:
        job_name: Name of the extraction job directory.
    
    Returns:
        ZIP file containing all extracted frames.
    """
    job_dir = os.path.join(app.config['OUTPUT_FOLDER'], job_name)
    
    if not os.path.exists(job_dir) or not os.path.isdir(job_dir):
        return jsonify({'error': 'Job not found'}), 404
    
    # Create ZIP file in memory
    memory_file = io.BytesIO()
    
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add all image files to ZIP
        for filename in os.listdir(job_dir):
            if filename.endswith('.jpg'):
                file_path = os.path.join(job_dir, filename)
                zf.write(file_path, filename)
        
        # Also include metadata files
        for filename in os.listdir(job_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(job_dir, filename)
                zf.write(file_path, filename)
    
    memory_file.seek(0)
    
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'{job_name}_frames.zip'
    )


@app.route('/download-frame/<path:job_name>/<path:filename>')
def download_single_frame(job_name, filename):
    """Download a single frame image.
    
    Args:
        job_name: Name of the extraction job directory.
        filename: Name of the frame file.
    
    Returns:
        The requested image file as download.
    """
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], job_name, filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'Frame not found'}), 404
    
    return send_file(
        filepath,
        mimetype='image/jpeg',
        as_attachment=True,
        download_name=filename
    )


@app.route('/jobs')
def list_jobs():
    """List all extraction jobs (output directories).
    
    Returns:
        JSON list of all job directories.
    """
    jobs = []
    if os.path.exists(app.config['OUTPUT_FOLDER']):
        for item in os.listdir(app.config['OUTPUT_FOLDER']):
            item_path = os.path.join(app.config['OUTPUT_FOLDER'], item)
            if os.path.isdir(item_path):
                frame_count = len([f for f in os.listdir(item_path) if f.endswith('.jpg')])
                jobs.append({
                    'name': item,
                    'frame_count': frame_count,
                    'path': item_path
                })
    return jsonify({'jobs': jobs})


@app.route('/delete-frame/<path:job_name>/<path:filename>', methods=['DELETE'])
def delete_single_frame_api(job_name, filename):
    """Delete a single extracted frame.
    
    Args:
        job_name: Name of the extraction job directory.
        filename: Name of the frame file to delete.
    
    Returns:
        JSON response with deletion status.
    """
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], job_name, filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'Frame not found'}), 404
    
    if not filename.endswith('.jpg'):
        return jsonify({'error': 'Invalid file type'}), 400
    
    try:
        os.remove(filepath)
        return jsonify({
            'success': True,
            'message': f'Deleted {filename}'
        })
    except Exception as e:
        return jsonify({'error': f'Failed to delete frame: {str(e)}'}), 500


@app.route('/delete-all-frames/<path:job_name>', methods=['DELETE'])
def delete_all_frames_api(job_name):
    """Delete all extracted frames for a job.
    
    Args:
        job_name: Name of the extraction job directory.
    
    Returns:
        JSON response with deletion status.
    """
    job_dir = os.path.join(app.config['OUTPUT_FOLDER'], job_name)
    
    if not os.path.exists(job_dir) or not os.path.isdir(job_dir):
        return jsonify({'error': 'Job not found'}), 404
    
    try:
        import shutil
        shutil.rmtree(job_dir)
        return jsonify({
            'success': True,
            'message': f'Deleted all frames for {job_name}'
        })
    except Exception as e:
        return jsonify({'error': f'Failed to delete frames: {str(e)}'}), 500


@app.route('/gemini/generate-blog', methods=['POST'])
def gemini_generate_blog():
    """Generate a blog post from a local video using Gemini.

    Expects JSON body: {"filename": str, "messages": list (optional)}

    Returns:
        JSON: {"blog": str, "frames": list, "source": str, "gemini_cache_status": str}
    """
    data = request.get_json()

    if not data or 'filename' not in data:
        return jsonify({'error': 'filename is required'}), 400

    if not gemini_service.is_configured():
        return jsonify({'error': 'Gemini API is not configured'}), 503

    filename = secure_filename(data['filename'])
    messages = data.get('messages', [])
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if not os.path.exists(filepath):
        return jsonify({'error': 'Video file not found'}), 404

    try:
        uri, cache_status = _resolve_gemini_uri(filename, filepath)
    except Exception as e:
        return jsonify({'error': f'Failed to resolve Gemini file URI: {str(e)}'}), 500

    try:
        result = gemini_service.generate_blog(uri, messages)
    except Exception as e:
        return jsonify({'error': f'Blog generation failed: {str(e)}'}), 500

    draft = result.get('draft', '')
    timestamps = result.get('timestamps', [])
    output_dir = os.path.join(app.config['OUTPUT_FOLDER'], Path(filename).stem)

    try:
        if timestamps:
            frames = extract_frames_at_timestamps(filepath, output_dir, [float(t) for t in timestamps])
            source = 'gemini-timestamps'
        else:
            frames = extract_keyframes(filepath, output_dir)
            source = 'scene-detection'
    except Exception as e:
        return jsonify({'error': f'Frame extraction failed: {str(e)}'}), 500

    frame_files = [f['filename'] for f in frames]

    return jsonify({
        'blog': draft,
        'frames': frame_files,
        'source': source,
        'gemini_cache_status': cache_status,
    })


@app.route('/gemini/ask', methods=['POST'])
def gemini_ask():
    """Answer a question about a video using Gemini Q&A.

    Accepts both local uploads (filename points to /app/uploads/) and
    URL-based videos (pseudo-filename created by /upload-from-url).

    Expects JSON body:
        {"filename": str, "messages": [{"role": "user"|"model", "parts": [str]}, ...]}

    Returns:
        JSON: {"answer": str, "gemini_cache_status": str}
    """
    data = request.get_json()

    if not data or 'filename' not in data or 'messages' not in data:
        return jsonify({'error': 'filename and messages are required'}), 400

    if not gemini_service.is_configured():
        return jsonify({'error': 'Gemini API is not configured'}), 503

    filename = data['filename']
    messages = data['messages']

    if not messages:
        return jsonify({'error': 'messages must not be empty'}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    try:
        # filepath is passed only if it exists; URL-based videos have no local file
        uri, cache_status = _resolve_gemini_uri(
            filename,
            filepath if os.path.exists(filepath) else None,
        )
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': f'Failed to resolve Gemini file URI: {str(e)}'}), 500

    try:
        answer = gemini_service.ask(uri, messages)
    except Exception as e:
        return jsonify({'error': f'Q&A failed: {str(e)}'}), 500

    return jsonify({
        'answer': answer,
        'gemini_cache_status': cache_status,
    })


# ── Settings ─────────────────────────────────────────────────────────

@app.route('/settings')
def settings_page():
    """Render the settings page."""
    return render_template('settings.html', version=APP_VERSION)


@app.route('/api/connections', methods=['GET'])
def get_connections():
    connections = db_service.list_connections()
    active_id = db_service.get_active_connection_id()
    return jsonify({
        'connections': connections,
        'active_id': active_id
    })


@app.route('/api/connections', methods=['POST'])
def create_connection():
    data = request.get_json()
    if not data or 'name' not in data or 'provider' not in data or 'api_key' not in data or 'model_name' not in data:
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn_id = db_service.add_connection(
        name=data['name'],
        provider=data['provider'],
        api_key=data['api_key'],
        model_name=data['model_name'],
        base_url=data.get('base_url')
    )
    return jsonify({'success': True, 'id': conn_id})


@app.route('/api/connections/<int:conn_id>', methods=['PUT'])
def update_connection(conn_id):
    data = request.get_json()
    if not data or 'name' not in data or 'provider' not in data or 'api_key' not in data or 'model_name' not in data:
        return jsonify({'error': 'Missing required fields'}), 400
        
    success = db_service.update_connection(
        conn_id=conn_id,
        name=data['name'],
        provider=data['provider'],
        api_key=data['api_key'],
        model_name=data['model_name'],
        base_url=data.get('base_url')
    )
    if success:
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to update connection'}), 500


@app.route('/api/connections/<int:conn_id>', methods=['DELETE'])
def delete_connection(conn_id):
    success = db_service.delete_connection(conn_id)
    if success:
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to delete connection'}), 500


@app.route('/api/settings/active', methods=['PUT'])
def set_active_connection():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request'}), 400
        
    conn_id = data.get('conn_id')
    db_service.set_active_connection_id(conn_id)
    return jsonify({'success': True})


@app.route('/api/connections/test', methods=['POST'])
def test_connection():
    data = request.get_json()
    if not data or 'provider' not in data or 'api_key' not in data or 'model_name' not in data:
        return jsonify({'error': 'Missing required fields'}), 400
        
    provider = data['provider']
    api_key = data['api_key']
    model_name = data['model_name']
    base_url = data.get('base_url')

    try:
        if provider == 'openai':
            from openai import OpenAI
            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            client = OpenAI(**kwargs)
            # Try a simple completion
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=5
            )
            return jsonify({'success': True, 'message': 'Connection successful'})
            
        elif provider == 'anthropic':
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=model_name,
                max_tokens=5,
                messages=[{"role": "user", "content": "hello"}],
            )
            return jsonify({'success': True, 'message': 'Connection successful'})
            
        else:
            return jsonify({'error': 'Unknown provider'}), 400
            
    except Exception as e:
        error_msg = str(e)
        if "404 page not found" in error_msg.lower() or "404" in error_msg:
            if base_url and not base_url.endswith('/v1') and provider == 'openai':
                error_msg += " (Hint: For Ollama or LM Studio, ensure your base_url ends with /v1)"
        return jsonify({'error': f"Connection failed: {error_msg}"}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5123, debug=True)
