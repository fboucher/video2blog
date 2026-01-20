#!/usr/bin/env python3
import io
import json
import os
import re
import zipfile
from pathlib import Path
from typing import Dict, Any, List

from flask import Flask, render_template, request, jsonify, send_file, url_for
from werkzeug.utils import secure_filename

from keyframe_extractor import extract_keyframes, extract_frames_at_timestamps
import reka_service
import db_service


# Constants
UPLOAD_FOLDER = '/app/uploads'
OUTPUT_FOLDER = '/app/output'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv'}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB

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


@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')


@app.route('/videos/list')
def list_all_videos():
    """Get unified list of all videos (Reka + Local + Synced).
    
    Returns:
        JSON with unified video list including sync status and available actions.
    """
    # Get all local video files
    local_files = {}
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if allowed_file(filename):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file_stats = os.stat(filepath)
                
                # Get video metadata
                import cv2
                cap = cv2.VideoCapture(filepath)
                fps = 0
                duration = 0
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    duration = total_frames / fps if fps > 0 else 0
                    cap.release()
                
                local_files[filename] = {
                    'filename': filename,
                    'filepath': filepath,
                    'size': file_stats.st_size,
                    'modified': file_stats.st_mtime,
                    'duration': duration,
                    'fps': fps
                }
    
    # Get all Reka videos
    reka_result = reka_service.list_videos()
    reka_videos = {}
    if 'videos' in reka_result and isinstance(reka_result['videos'], dict):
        # Reka API returns {success: true, videos: {results: [...]}}
        video_list = reka_result['videos'].get('results', [])
        for video in video_list:
            video_id = video.get('video_id')
            if video_id:
                reka_videos[video_id] = video
    
    # Get all sync records from database
    sync_records = db_service.list_all_syncs()
    syncs_by_reka_id = {sync['reka_video_id']: sync for sync in sync_records}
    syncs_by_filename = {sync['local_filename']: sync for sync in sync_records}
    
    # Build unified video list
    unified_videos = []
    processed_reka_ids = set()
    processed_filenames = set()
    
    # Process synced videos (in both Reka and local)
    for sync in sync_records:
        reka_id = sync['reka_video_id']
        filename = sync['local_filename']
        
        reka_video = reka_videos.get(reka_id)
        local_file = local_files.get(filename)
        
        if reka_video and local_file:
            # Fully synced
            unified_videos.append({
                'id': reka_id,
                'name': sync['video_name'],
                'source': 'synced',
                'reka_video_id': reka_id,
                'local_filename': filename,
                'local_filepath': local_file['filepath'],
                'reka_url': sync['reka_url'],
                'reka_indexing_status': sync['reka_indexing_status'],
                'duration': local_file['duration'],
                'fps': local_file['fps'],
                'size': local_file['size'],
                'modified': local_file['modified'],
                'can_select': sync['reka_indexing_status'] == 'indexed',
                'can_download': False,
                'can_delete_reka': True,
                'can_delete_local': True,
                'can_refresh_status': sync['reka_indexing_status'] != 'indexed'
            })
            processed_reka_ids.add(reka_id)
            processed_filenames.add(filename)
        elif reka_video and not local_file:
            # Reka exists but local file deleted - clean up sync
            db_service.delete_sync_by_reka_id(reka_id)
        elif not reka_video and local_file:
            # Local exists but Reka deleted - clean up sync
            db_service.delete_sync_by_filename(filename)
    
    # Process Reka-only videos (not synced locally)
    for reka_id, reka_video in reka_videos.items():
        if reka_id not in processed_reka_ids:
            # Extract video name from metadata
            video_name = reka_video.get('metadata', {}).get('video_name') or \
                        reka_video.get('metadata', {}).get('title') or \
                        'Unnamed Video'
            
            unified_videos.append({
                'id': reka_id,
                'name': video_name,
                'source': 'reka_only',
                'reka_video_id': reka_id,
                'local_filename': None,
                'local_filepath': None,
                'reka_url': reka_video.get('url'),
                'reka_indexing_status': reka_video.get('indexing_status', 'unknown'),
                'duration': None,
                'fps': None,
                'size': None,
                'modified': None,
                'can_select': False,
                'can_download': reka_video.get('indexing_status') == 'indexed',
                'can_delete_reka': True,
                'can_delete_local': False,
                'can_refresh_status': reka_video.get('indexing_status') != 'indexed'
            })
    
    # Process local-only videos (not synced to Reka)
    for filename, local_file in local_files.items():
        if filename not in processed_filenames:
            unified_videos.append({
                'id': filename,  # Use filename as ID for local-only
                'name': filename,
                'source': 'local_only',
                'reka_video_id': None,
                'local_filename': filename,
                'local_filepath': local_file['filepath'],
                'reka_url': None,
                'reka_indexing_status': None,
                'duration': local_file['duration'],
                'fps': local_file['fps'],
                'size': local_file['size'],
                'modified': local_file['modified'],
                'can_select': False,
                'can_download': False,
                'can_delete_reka': False,
                'can_delete_local': True,
                'can_refresh_status': False
            })
    
    # Sort by modified time (newest first), then by name
    unified_videos.sort(key=lambda x: (-(x['modified'] or 0), x['name']))
    
    return jsonify({'videos': unified_videos})


@app.route('/videos/download', methods=['POST'])
def download_reka_video():
    """Download a Reka video to local storage and create sync record.
    
    Returns:
        JSON response with download result and local file info.
    """
    data = request.json
    
    if not data or 'reka_video_id' not in data:
        return jsonify({'error': 'reka_video_id is required'}), 400
    
    reka_video_id = data['reka_video_id']
    video_url = data.get('video_url')
    video_name = data.get('video_name', 'Unnamed Video')
    reka_indexing_status = data.get('reka_indexing_status', 'unknown')
    
    if not video_url:
        return jsonify({'error': 'video_url is required'}), 400
    
    # Generate safe filename
    filename = sanitize_filename(video_name, reka_video_id)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    # Check for duplicates
    duplicate_check = db_service.check_duplicate(reka_video_id=reka_video_id, local_filename=filename)
    if duplicate_check.get('is_duplicate'):
        return jsonify({'error': duplicate_check.get('message', 'Video already synced')}), 409
    
    # Check if file already exists locally
    if os.path.exists(filepath):
        return jsonify({'error': f'File {filename} already exists locally'}), 409
    
    try:
        # Download video from Reka CDN
        download_result = reka_service.download_video(video_url, filepath)
        
        if 'error' in download_result:
            return jsonify(download_result), 400
        
        # Get video metadata
        import cv2
        cap = cv2.VideoCapture(filepath)
        if not cap.isOpened():
            os.remove(filepath)
            return jsonify({'error': 'Unable to open downloaded video file'}), 400
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        
        # Create sync record in database
        db_service.add_sync(
            reka_video_id=reka_video_id,
            local_filename=filename,
            video_name=video_name,
            reka_url=video_url,
            reka_indexing_status=reka_indexing_status
        )
        
        return jsonify({
            'success': True,
            'message': f'Downloaded {video_name}',
            'filename': filename,
            'filepath': filepath,
            'duration': duration,
            'fps': fps,
            'total_frames': total_frames,
            'width': width,
            'height': height,
            'reka_video_id': reka_video_id,
            'reka_indexing_status': reka_indexing_status
        })
        
    except Exception as e:
        # Clean up partial download
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': f'Download failed: {str(e)}'}), 500


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
    
    # Save uploaded file
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
    
    # Auto-upload to Reka (if configured)
    reka_video_id = None
    reka_indexing_status = None
    reka_upload_error = None
    
    if reka_service.is_configured():
        try:
            # Use original filename (without .mp4) as video name
            video_name = Path(filename).stem
            
            reka_result = reka_service.upload_video(
                video_path=filepath,
                video_name=video_name,
                index=True,
                enable_thumbnails=False
            )
            
            if 'error' not in reka_result and 'video_id' in reka_result:
                reka_video_id = reka_result['video_id']
                reka_indexing_status = 'indexing'
                
                # Create sync record in database
                db_service.add_sync(
                    reka_video_id=reka_video_id,
                    local_filename=filename,
                    video_name=video_name,
                    reka_url=reka_result.get('url'),
                    reka_indexing_status=reka_indexing_status
                )
            else:
                reka_upload_error = reka_result.get('error', 'Unknown error')
        except Exception as e:
            reka_upload_error = str(e)
    
    response = {
        'success': True,
        'filename': filename,
        'filepath': filepath,
        'duration': duration,
        'fps': fps,
        'total_frames': total_frames,
        'width': width,
        'height': height
    }
    
    # Add Reka info if uploaded successfully
    if reka_video_id:
        response['reka_video_id'] = reka_video_id
        response['reka_indexing_status'] = reka_indexing_status
        response['reka_synced'] = True
    else:
        response['reka_synced'] = False
        if reka_upload_error:
            response['reka_upload_error'] = reka_upload_error
    
    return jsonify(response)


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


@app.route('/reka/refresh-status/<video_id>', methods=['POST'])
def refresh_reka_status(video_id):
    """Refresh the indexing status of a Reka video.
    
    Args:
        video_id: ID of the video to refresh.
    
    Returns:
        JSON response with updated status.
    """
    # Get updated video data from Reka
    result = reka_service.list_videos()
    
    if 'error' in result:
        return jsonify(result), 400
    
    # Find the specific video
    video_data = None
    if 'videos' in result:
        for video in result['videos']:
            if video['id'] == video_id:
                video_data = video
                break
    
    if not video_data:
        return jsonify({'error': 'Video not found in Reka'}), 404
    
    # Update database with new indexing status
    new_status = video_data.get('indexing_status', 'unknown')
    db_service.update_reka_indexing_status(video_id, new_status)
    
    return jsonify({
        'success': True,
        'video_id': video_id,
        'indexing_status': new_status,
        'message': f'Status updated to {new_status}'
    })


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


@app.route('/reka/ask', methods=['POST'])
def ask_reka_question():
    """Ask a question about a video using Reka Q&A.
    
    Returns:
        JSON response with answer.
    """
    data = request.json
    
    if not data or 'video_id' not in data or 'question' not in data:
        return jsonify({'error': 'video_id and question are required'}), 400
    
    video_id = data['video_id']
    question = data['question']
    
    # Get conversation history if provided
    messages = data.get('messages', [])
    
    # Add the new question
    messages.append({
        'role': 'user',
        'content': question
    })
    
    result = reka_service.ask_question(video_id, messages)
    
    if 'error' in result:
        return jsonify(result), 400
    
    return jsonify(result)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
