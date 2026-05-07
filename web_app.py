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
import reka_service
import db_service
import gemini_service


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


def sanitize_filename(video_name: str, reka_video_id: str) -> str:
    """Generate safe filename from video name and Reka video ID.
    
    Format: {sanitized_name}_{video_id_prefix}.mp4
    
    Args:
        video_name: Original video name from Reka.
        reka_video_id: Reka video UUID.
    
    Returns:
        Safe filename suitable for filesystem use.
    """
    # Remove non-alphanumeric characters except spaces and hyphens
    safe_name = re.sub(r'[^\w\s-]', '', video_name).strip().lower()
    # Replace spaces and multiple hyphens with single underscore
    safe_name = re.sub(r'[-\s]+', '_', safe_name)
    # Get first part of UUID (before first hyphen)
    video_id_prefix = reka_video_id.split('-')[0]
    # Limit name length and append UUID prefix
    return f"{safe_name[:80]}_{video_id_prefix}.mp4"


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


def _gemini_cache_status(gemini_info: dict | None) -> dict:
    """Return cache status dict for a Gemini file info record."""
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
            return {"gemini_cache_status": "fresh", "age_hours": round(age_hours, 2)}
        return {"gemini_cache_status": "expired", "age_hours": round(age_hours, 2)}
    except (ValueError, TypeError):
        return {"gemini_cache_status": "not_uploaded"}


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
    """List all locally-stored videos with Gemini file cache status.

    Returns:
        JSON with video list; each entry includes gemini_cache_status
        (fresh | expired | not_uploaded) and, when fresh, expires_in_hours.
    """
    videos = []
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        for filename in sorted(os.listdir(app.config['UPLOAD_FOLDER'])):
            if not allowed_file(filename):
                continue
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file_stats = os.stat(filepath)

            import cv2
            cap = cv2.VideoCapture(filepath)
            fps = duration = 0
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = total_frames / fps if fps > 0 else 0
                cap.release()

            gemini_info = db_service.get_gemini_file_info(filename)
            cache = _gemini_cache_status(gemini_info)

            entry = {
                'filename': filename,
                'filepath': filepath,
                'size': file_stats.st_size,
                'modified': file_stats.st_mtime,
                'duration': duration,
                'fps': fps,
                'gemini_uri': gemini_info['uri'] if gemini_info else None,
            }
            entry.update(cache)
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
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        # Delete the file
        os.remove(filepath)
        
        # Clean up database sync record if exists
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


# Reka API Endpoints

@app.route('/reka/status')
def reka_status():
    """Check if Reka API is configured.
    
    Returns:
        JSON with configuration status.
    """
    return jsonify({
        'configured': reka_service.is_configured(),
        'message': 'Reka API is configured' if reka_service.is_configured() else 'Reka API key not configured'
    })


@app.route('/reka/videos')
def list_reka_videos():
    """List all videos from Reka.
    
    Returns:
        JSON list of Reka videos.
    """
    result = reka_service.list_videos()
    
    if 'error' in result:
        return jsonify(result), 400
    
    return jsonify(result)


@app.route('/reka/upload', methods=['POST'])
def upload_to_reka():
    """Upload a local video file to Reka.
    
    Returns:
        JSON response with upload result.
    """
    data = request.json
    
    if not data or 'filename' not in data:
        return jsonify({'error': 'No filename provided'}), 400
    
    filename = data['filename']
    video_name = data.get('video_name', filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    result = reka_service.upload_video(
        video_path=filepath,
        video_name=video_name,
        index=True,
        enable_thumbnails=False
    )
    
    if 'error' in result:
        return jsonify(result), 400
    
    return jsonify(result)


@app.route('/reka/delete/<video_id>', methods=['DELETE'])
def delete_reka_video(video_id):
    """Delete a video from Reka.
    
    Args:
        video_id: ID of the video to delete.
    
    Returns:
        JSON response with deletion result.
    """
    result = reka_service.delete_video(video_id)
    
    if 'error' in result:
        return jsonify(result), 400
    
    # Clean up database sync record if exists
    db_service.delete_sync_by_reka_id(video_id)
    
    return jsonify(result)


def _resolve_gemini_uri(filename: str, filepath: str | None = None) -> tuple[str, str]:
    """Return (gemini_uri, cache_status), uploading if needed.

    For local videos: filepath must be provided; checks DB for fresh URI (< 48 h).
    For URL videos: filepath is None; checks DB for URL record and returns immediately.

    Raises:
        RuntimeError: If the upload fails.
        FileNotFoundError: If local filepath does not exist.
    """
    gemini_info = db_service.get_gemini_file_info(filename)
    
    # URL-based videos: always return fresh (no TTL)
    if gemini_info and gemini_info.get('source') == 'url':
        return gemini_info['uri'], 'fresh'
    
    cache = _gemini_cache_status(gemini_info)

    if cache.get("gemini_cache_status") == "fresh":
        return gemini_info["uri"], "fresh"

    # Expired or not uploaded — (re-)upload now
    if filepath is None:
        raise ValueError("filepath required for local video upload")
    
    uri = gemini_service.upload_video(filepath)
    timestamp = datetime.now(timezone.utc).isoformat()
    db_service.update_gemini_upload(filename, uri, timestamp)
    return uri, "re-uploaded"


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
def ask_gemini_question():
    """Ask a question about a local or URL-based video using Gemini Q&A.

    Body:
        {"filename": "video.mp4",
         "messages": [{"role": "user", "parts": ["What is this about?"]}]}

    Returns:
        {"answer": str, "gemini_cache_status": "fresh"|"re-uploaded"}
    """
    if not gemini_service.is_configured():
        return jsonify({'error': 'Gemini not configured'}), 503

    data = request.get_json()
    if not data or 'filename' not in data:
        return jsonify({'error': 'filename is required'}), 400

    messages = data.get('messages', [])
    if not messages:
        return jsonify({'error': 'messages must not be empty'}), 400

    filename = data['filename']
    
    # Try local file first; if not found, might be a URL video
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        # For URL videos (filename like 'url-abc123'), filepath won't exist
        # _resolve_gemini_uri will handle this case
        if not os.path.exists(filepath) and not filename.startswith('url-'):
            return jsonify({'error': f'Video file not found: {filename}'}), 404
        
        uri, cache_status = _resolve_gemini_uri(filename, filepath if os.path.exists(filepath) else None)
    except Exception as exc:
        print(f"[gemini/ask] Upload failed for {filename}: {exc}")
        return jsonify({'error': f'Gemini upload failed: {exc}'}), 500

    try:
        answer = gemini_service.ask(file_ref=uri, messages=messages)
    except Exception as exc:
        print(f"[gemini/ask] Ask failed for {filename}: {exc}")
        return jsonify({'error': f'Gemini request failed: {exc}'}), 500

    return jsonify({'answer': answer, 'gemini_cache_status': cache_status})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5123, debug=True)
