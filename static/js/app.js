// Global state
let currentVideoInfo = null;

// DOM Elements
const videoInput = document.getElementById('video-input');
const uploadArea = document.getElementById('upload-area');
const videoInfo = document.getElementById('video-info');
const existingFilesList = document.getElementById('existing-files-list');
const paramsSection = document.getElementById('params-section');
const resultsSection = document.getElementById('results-section');
const timestampParams = document.getElementById('timestamp-params');
const extractBtn = document.getElementById('extract-btn');
const progress = document.getElementById('progress');
const resultsContent = document.getElementById('results-content');

// Event Listeners
videoInput.addEventListener('change', handleFileSelect);
uploadArea.addEventListener('click', () => videoInput.click());
uploadArea.addEventListener('dragover', handleDragOver);
uploadArea.addEventListener('dragleave', handleDragLeave);
uploadArea.addEventListener('drop', handleDrop);
extractBtn.addEventListener('click', handleExtraction);

// Load existing files on page load
loadExistingFiles();

// Load Existing Files
async function loadExistingFiles() {
    try {
        const response = await fetch('/list-uploads');
        const data = await response.json();
        
        if (data.files && data.files.length > 0) {
            displayExistingFiles(data.files);
        } else {
            existingFilesList.innerHTML = '<div class="no-files-message">No existing files found. Upload a new file below.</div>';
        }
    } catch (error) {
        existingFilesList.innerHTML = '<div class="no-files-message">Error loading files.</div>';
    }
}

function displayExistingFiles(files) {
    existingFilesList.innerHTML = files.map(file => `
        <div class="file-item" data-filename="${file.filename}">
            <div class="file-info">
                <div class="file-name">${file.filename}</div>
                <div class="file-meta">${formatFileSize(file.size)} • ${formatDate(file.modified)}</div>
            </div>
            <div class="file-actions">
                <button class="file-select-btn" onclick="selectExistingFile('${file.filename}')">
                    Select
                </button>
                <button class="file-delete-btn" onclick="deleteExistingFile('${file.filename}')" title="Delete file">
                    🗑️
                </button>
            </div>
        </div>
    `).join('');
}

async function selectExistingFile(filename) {
    try {
        const response = await fetch('/select-file', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ filename: filename })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        currentVideoInfo = data;
        displayVideoInfo(data);
        paramsSection.style.display = 'block';
        
        // Highlight selected file
        document.querySelectorAll('.file-item').forEach(item => {
            item.classList.remove('selected');
        });
        document.querySelector(`.file-item[data-filename="${filename}"]`)?.classList.add('selected');
        
    } catch (error) {
        showError('Failed to select file: ' + error.message);
    }
}

async function deleteExistingFile(filename) {
    if (!confirm(`Are you sure you want to delete "${filename}"?`)) {
        return;
    }
    
    try {
        const response = await fetch('/delete-file', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ filename: filename })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        // Reload the file list
        loadExistingFiles();
        
        // Clear video info if the deleted file was selected
        if (currentVideoInfo && currentVideoInfo.filename === filename) {
            currentVideoInfo = null;
            videoInfo.classList.add('hidden');
            paramsSection.style.display = 'none';
            resultsSection.style.display = 'none';
        }
        
    } catch (error) {
        showError('Failed to delete file: ' + error.message);
    }
}

// File Upload Handlers
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        uploadVideo(file);
    }
}

function handleDragOver(event) {
    event.preventDefault();
    uploadArea.classList.add('dragover');
}

function handleDragLeave(event) {
    event.preventDefault();
    uploadArea.classList.remove('dragover');
}

function handleDrop(event) {
    event.preventDefault();
    uploadArea.classList.remove('dragover');
    
    const file = event.dataTransfer.files[0];
    if (file) {
        uploadVideo(file);
    }
}

async function uploadVideo(file) {
    const formData = new FormData();
    formData.append('video', file);
    
    try {
        // Show uploading state
        uploadArea.innerHTML = '<div class="spinner"></div><p>Uploading...</p>';
        
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            resetUploadArea();
            return;
        }
        
        currentVideoInfo = currentVideoInfo;
        displayVideoInfo(currentVideoInfo);
        paramsSection.style.display = 'block';
        
    } catch (error) {
        showError('Upload failed: ' + error.message);
        resetUploadArea();
    }
}

function displayVideoInfo(info) {
    videoInfo.classList.remove('hidden');
    videoInfo.innerHTML = `
        <h3>✓ Video Selected Successfully</h3>
        <div class="info-grid">
            <div class="info-item info-item-filename">
                <label>Filename</label>
                <strong title="${info.filename}">${info.filename}</strong>
            </div>
            <div class="info-item">
                <label>Duration</label>
                <strong>${formatDuration(info.duration)}</strong>
            </div>
            <div class="info-item">
                <label>FPS</label>
                <strong>${info.fps.toFixed(2)}</strong>
            </div>
            <div class="info-item">
                <label>Resolution</label>
                <strong>${info.width}x${info.height}</strong>
            </div>
            <div class="info-item">
                <label>Total Frames</label>
                <strong>${info.total_frames.toLocaleString()}</strong>
            </div>
        </div>
    `;
    
    uploadArea.innerHTML = `
        <div class="upload-icon">✓</div>
        <div class="upload-text">${info.filename}</div>
        <div class="upload-formats">Click to upload a different video</div>
    `;
}

function resetUploadArea() {
    uploadArea.innerHTML = `
        <div class="upload-icon">📹</div>
        <div class="upload-text">Click to select or drag & drop video file</div>
        <div class="upload-formats">Supported: MP4, AVI, MOV, MKV, WEBM, FLV</div>
    `;
}

// Extraction Handler
async function handleExtraction() {
    if (!currentVideoInfo) {
        showError('Please select a video first');
        return;
    }
    
    const timestampsInput = document.getElementById('timestamps').value;
    
    if (!timestampsInput) {
        showError('Please enter timestamps');
        return;
    }
    
    // Parse timestamps and convert to floats (supports both integers and decimals)
    let timestamps;
    try {
        timestamps = timestampsInput.split(',').map(ts => {
            const num = parseFloat(ts.trim());
            if (isNaN(num)) {
                throw new Error(`Invalid timestamp: ${ts.trim()}`);
            }
            return num;
        }).join(',');
    } catch (error) {
        showError(error.message);
        return;
    }
    
    const params = {
        filepath: currentVideoInfo.filepath,
        mode: 'timestamp',
        timestamps: timestamps,
        frames_per_timestamp: parseInt(document.getElementById('frames-per-timestamp').value)
    }
    
    try {
        extractBtn.disabled = true;
        resultsSection.style.display = 'block';
        progress.classList.remove('hidden');
        resultsContent.classList.add('hidden');
        resultsContent.innerHTML = '';
        
        const response = await fetch('/extract', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(params)
        });
        
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        displayResults(data);
        
    } catch (error) {
        showError('Extraction failed: ' + error.message);
    } finally {
        extractBtn.disabled = false;
        progress.classList.add('hidden');
    }
}

function displayResults(data) {
    resultsContent.classList.remove('hidden');
    
    const outputDirName = data.output_dir.split('/').pop();
    
    resultsContent.innerHTML = `
        <div class="results-summary">
            <h3>Extraction Complete!</h3>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="value">${data.total_frames}</div>
                    <div class="label">Frames Extracted</div>
                </div>
                <div class="summary-item">
                    <div class="value">${data.all_frames_count}</div>
                    <div class="label">Total Files</div>
                </div>
            </div>
            
            <div class="download-actions">
                <a href="/download-all/${outputDirName}" class="btn btn-download-all">
                    📦 Download All Frames (ZIP)
                </a>
            </div>
        </div>
        
        <h3>Preview & Download Individual Frames</h3>
        <div class="frames-grid">
            ${data.frames.map(frame => `
                <div class="frame-item">
                    <img src="/frames/${outputDirName}/${frame}" alt="${frame}">
                    <div class="frame-footer">
                        <div class="frame-name">${frame}</div>
                        <a href="/download-frame/${outputDirName}/${frame}" 
                           class="btn-download-frame" 
                           title="Download ${frame}">
                            ⬇️
                        </a>
                    </div>
                </div>
            `).join('')}
        </div>
        
        ${data.all_frames_count > 20 ? `
            <div class="info-message">
                Showing first 20 frames. Download the ZIP file to get all ${data.all_frames_count} frames.
            </div>
        ` : ''}
    `;
}

// Utility Functions
function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

function formatDate(timestamp) {
    const date = new Date(timestamp * 1000);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    
    return date.toLocaleDateString();
}

function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error';
    errorDiv.textContent = message;
    
    resultsContent.innerHTML = '';
    resultsContent.appendChild(errorDiv);
    resultsContent.classList.remove('hidden');
    
    setTimeout(() => {
        errorDiv.remove();
        if (resultsContent.children.length === 0) {
            resultsContent.classList.add('hidden');
        }
    }, 5000);
}
