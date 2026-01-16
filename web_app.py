#!/usr/bin/env python3
import io
import json
import os
import zipfile
from pathlib import Path
from typing import Dict, Any, List

from flask import Flask, render_template, request, jsonify, send_file, url_for
from werkzeug.utils import secure_filename

from keyframe_extractor import extract_keyframes, extract_frames_at_timestamps


# Constants
UPLOAD_FOLDER = '/app/uploads'
OUTPUT_FOLDER = '/app/output'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv'}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB

# Flask app configuration
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Ensure directories exist
Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
Path(OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)


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
        os.remove(filepath)
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
