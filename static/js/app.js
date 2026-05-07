// Global state - Unified video object
let currentVideo = null;
let chatMessages = [];

// Default question template
const DEFAULT_QUESTION = `You are a technical content writer creating blog posts from educational videos.

IMPORTANT: Your response MUST end with a TIMESTAMPS line (see output format below).

Your task is to:

1. Watch and analyze the video carefully
2. Write a complete, standalone blog post that covers the video's content with:
- A short, engaging introduction (2-3 sentences) that hooks the reader and clearly states what they'll learn
- Clear structure with descriptive headings and sections
- A brief conclusion that summarizes key takeaways
- Simple, accessible English (avoid jargon where possible; explain technical terms when necessary)
- Markdown formatting

3. Identify 3 key timestamps for important visual moments such as:
- Diagrams or visual explanations
- Final results or completed work
- Error messages or debugging steps
- Critical demonstrations
- Before/after comparisons

Requirements:
- The blog post should be understandable without watching the video
- Use conversational but professional tone
- Include all important details, steps, and concepts from the video
- Within the post, place placeholder images where visual content should appear using: ![Image description](KEYFRAME_[seconds])

---
Output format (follow exactly):

1. The complete blog post in markdown
2. Then, the VERY LAST line of your response MUST be the 3 timestamps as comma-separated seconds in this exact format:
TIMESTAMPS: 45, 127, 289

Do NOT add any text after the TIMESTAMPS line.
`;

// Helper function: fetch with timeout
async function fetchWithTimeout(url, options = {}, timeoutMs = 120000) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    
    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal
        });
        clearTimeout(timeout);
        return response;
    } catch (error) {
        clearTimeout(timeout);
        if (error.name === 'AbortError') {
            throw new Error('Request timed out after 2 minutes');
        }
        throw error;
    }
}

// DOM Elements
const videoInput = document.getElementById('video-input');
const videoInfo = document.getElementById('video-info');
const videosList = document.getElementById('videos-list');
const paramsSection = document.getElementById('params-section');
const resultsSection = document.getElementById('results-section');
const chatSection = document.getElementById('chat-section');
const timestampParams = document.getElementById('timestamp-params');
const extractBtn = document.getElementById('extract-btn');
const progress = document.getElementById('progress');
const resultsContent = document.getElementById('results-content');
const chatMessagesDiv = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const chatSendBtn = document.getElementById('chat-send-btn');

// Event Listeners
videoInput.addEventListener('change', handleFileSelect);
extractBtn.addEventListener('click', handleExtraction);
chatSendBtn.addEventListener('click', sendChatMessage);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendChatMessage();
});

// URL Upload Event Listeners
const urlUploadBtn = document.getElementById('url-upload-btn');
const urlInput = document.getElementById('url-input');

if (urlUploadBtn) {
    urlUploadBtn.addEventListener('click', uploadFromUrl);
}

if (urlInput) {
    urlInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') uploadFromUrl();
    });
}

// Load all videos on page load
loadAllVideos();

// Tab Switching Functions
function switchUploadTab(tab) {
    const fileArea = document.getElementById('file-upload-area');
    const urlArea = document.getElementById('url-upload-area');
    const tabs = document.querySelectorAll('.upload-tab');

    tabs.forEach(t => {
        t.classList.toggle('active', t.dataset.tab === tab);
    });

    if (tab === 'file') {
        fileArea.classList.remove('hidden');
        urlArea.classList.add('hidden');
    } else {
        fileArea.classList.add('hidden');
        urlArea.classList.remove('hidden');
    }
}

async function uploadFromUrl() {
    const urlInput = document.getElementById('url-input');
    const videoNameInput = document.getElementById('url-video-name');
    const uploadBtn = document.getElementById('url-upload-btn');
    const url = urlInput.value.trim();
    const videoName = videoNameInput.value.trim();

    if (!url) {
        showToast('Please enter a video URL', 'error');
        return;
    }

    // Basic validation
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        showToast('URL must start with http:// or https://', 'error');
        return;
    }

    try {
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '<span class="material-symbols-rounded">hourglass_empty</span> Processing...';
        showToast('Processing video URL...', 'info');

        // Build request body with URL and optional video name
        const requestBody = { url: url };
        if (videoName) {
            requestBody.video_name = videoName;
        }

        const response = await fetch('/upload-from-url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();

        if (data.error) {
            showToast(data.error, 'error');
            return;
        }

        showToast(`Video ready for Q&A: ${data.filename}`, 'success');

        // Reload video list (video will appear as URL video)
        loadAllVideos();

        // Clear inputs
        urlInput.value = '';
        videoNameInput.value = '';

    } catch (error) {
        showToast('Upload failed: ' + error.message, 'error');
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = '<span class="material-symbols-rounded">add_link</span> Add URL for Q&A';
    }
}

// Unified Video List Functions
async function loadAllVideos() {
    try {
        const response = await fetch('/videos/list');
        const data = await response.json();
        
        if (data.videos && data.videos.length > 0) {
            displayUnifiedVideoList(data.videos);
        } else {
            videosList.innerHTML = '<div class="no-files-message">No videos found. Upload a new video above.</div>';
        }
    } catch (error) {
        videosList.innerHTML = '<div class="no-files-message">Error loading videos.</div>';
        showToast('Error loading videos', 'error');
    }
}

function displayUnifiedVideoList(videos) {
    videosList.innerHTML = videos.map(video => {
        const sourceIcons = {
            'synced': { icon: 'sync', color: 'var(--ctp-mocha-green)', title: 'Synced (Reka + Local)' },
            'reka_only': { icon: 'cloud', color: 'var(--ctp-mocha-blue)', title: 'Reka Only' },
            'local_only': { icon: 'folder', color: 'var(--ctp-mocha-yellow)', title: 'Local Only' },
            'url': { icon: 'language', color: 'var(--ctp-mocha-lavender)', title: 'URL Video — Q&A Ready' }
        };
        
        const sourceInfo = sourceIcons[video.source] || { icon: 'help', color: 'var(--ctp-mocha-overlay0)', title: 'Unknown Source' };
        const statusBadge = getStatusBadge(video);
        const urlBadge = video.source === 'url' ? `
            <span class="badge badge-lavender" title="URL video is Q&A-ready. Frame extraction will download the video.">
                <span class="material-symbols-rounded">language</span>
                URL video — Q&A ready
            </span>
        ` : '';
        
        return `
        <div class="unified-video-item ${!video.can_select ? 'disabled' : ''}" data-video-id="${video.id}" data-video-source="${video.source}">
            <div class="video-item-header">
                <span class="sync-icon ${video.source}" title="${sourceInfo.title}">
                    <span class="material-symbols-rounded" style="color: ${sourceInfo.color};">${sourceInfo.icon}</span>
                </span>
                <div class="video-name">${escapeHtml(video.name)}</div>
                ${statusBadge}
                ${urlBadge}
            </div>
            <div class="video-item-meta">
                ${video.duration ? `<span>${formatDuration(video.duration)}</span>` : ''}
                ${video.size ? `<span>${formatFileSize(video.size)}</span>` : ''}
            </div>
            <div class="video-item-actions">
                ${video.can_select ? `
                    <button class="file-select-btn" onclick='selectVideo(${JSON.stringify(video).replace(/'/g, "&#39;")})'>
                        <span class="material-symbols-rounded">play_circle</span>
                        Select
                    </button>
                ` : `
                    <button class="file-select-btn" disabled title="Video not ready for processing">
                        <span class="material-symbols-rounded">play_circle</span>
                        Select
                    </button>
                `}
                ${(video.gemini_cache_status === 'expired' || video.gemini_cache_status === 'not_uploaded') ? `
                    <button class="file-action-btn upload-gemini-btn" onclick='uploadToGemini(${JSON.stringify(video).replace(/'/g, "&#39;")})' title="Upload to Gemini cache">
                        <span class="material-symbols-rounded">cloud_upload</span>
                        Upload to Gemini
                    </button>
                ` : ''}
                ${video.can_delete_local ? `
                    <button class="file-delete-btn" onclick="deleteLocal('${escapeHtml(video.local_filename)}')" title="Delete local copy">
                        <span class="material-symbols-rounded">delete</span>
                    </button>
                ` : ''}
            </div>
        </div>
        `;
    }).join('');
}

function getStatusBadge(video) {
    if (!video.gemini_cache_status) return '';
    
    const badges = {
        'fresh': { class: 'badge-green', text: 'Ready', icon: 'check_circle' },
        'expired': { class: 'badge-red', text: 'Expired', icon: 'schedule' },
        'not_uploaded': { class: 'badge-gray', text: 'Not uploaded', icon: 'cloud_upload' }
    };
    
    const badge = badges[video.gemini_cache_status] || badges['not_uploaded'];
    let badgeText = badge.text;
    
    if (video.gemini_cache_status === 'fresh' && video.expires_in_hours) {
        badgeText = `Ready (${video.expires_in_hours}h)`;
    }
    
    return `
        <span class="badge ${badge.class}">
            <span class="material-symbols-rounded">${badge.icon}</span>
            ${badgeText}
        </span>
    `;
}

async function selectVideo(video) {
    currentVideo = video;
    chatMessages = [];
    
    // Clear previous selections
    document.querySelectorAll('.unified-video-item').forEach(item => {
        item.classList.remove('selected');
    });
    document.querySelector(`.unified-video-item[data-video-id="${video.id}"]`)?.classList.add('selected');
    
    // Show video info
    videoInfo.classList.remove('hidden');
    videoInfo.innerHTML = `
        <h3>
            <span class="material-symbols-rounded">check_circle</span>
            Video Selected
        </h3>
        <div class="info-grid">
            <div class="info-item info-item-filename">
                <label>Name</label>
                <strong title="${escapeHtml(video.name)}">${escapeHtml(video.name)}</strong>
            </div>
            ${video.duration ? `
            <div class="info-item">
                <label>Duration</label>
                <strong>${formatDuration(video.duration)}</strong>
            </div>
            ` : ''}
            ${video.fps ? `
            <div class="info-item">
                <label>FPS</label>
                <strong>${video.fps.toFixed(2)}</strong>
            </div>
            ` : ''}
        </div>
    `;
    
    // Collapse Step 1 and show chat section for Q&A and extraction section
    document.getElementById('upload-section').removeAttribute('open');
    chatSection.style.display = 'block';
    paramsSection.style.display = 'block';
    resultsSection.style.display = 'none';
    
    // Handle params section differently for URL vs local videos
    if (video.source === 'url') {
        // Hide the normal params and show URL-specific message
        const timestampParams = document.getElementById('timestamp-params');
        if (timestampParams) {
            timestampParams.style.display = 'none';
        }
        // Update extract button for URL videos
        const originalExtractBtn = document.getElementById('extract-btn');
        if (originalExtractBtn) {
            originalExtractBtn.disabled = true;
            originalExtractBtn.innerHTML = `
                <span class="material-symbols-rounded">download</span>
                Extract Frames (downloads video)
            `;
            originalExtractBtn.title = 'Frame extraction coming soon — this will download the video';
        }
    } else {
        // Show normal params for local videos
        const timestampParams = document.getElementById('timestamp-params');
        if (timestampParams) {
            timestampParams.style.display = 'grid';
        }
        // Reset extract button
        const originalExtractBtn = document.getElementById('extract-btn');
        if (originalExtractBtn) {
            originalExtractBtn.disabled = false;
            originalExtractBtn.innerHTML = 'Extract Frames';
            originalExtractBtn.title = '';
        }
    }
    
    // Add Q&A-only messaging for URL videos
    if (video.source === 'url') {
        chatMessagesDiv.innerHTML = `
            <div class="chat-welcome">
                <h4>💡 This video is Q&A-ready</h4>
                <p>Frame extraction will download the video when triggered. Ask any questions about this video below.</p>
            </div>
        `;
    } else {
        chatMessagesDiv.innerHTML = '<div class="chat-welcome">Ask me anything about this video!</div>';
    }
    
    chatInput.value = DEFAULT_QUESTION;
    chatInput.focus();
}

async function downloadVideo(video) {
    showToast('Downloading video...', 'info');
    
    try {
        const response = await fetch('/videos/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                reka_video_id: video.reka_video_id,
                video_url: video.reka_url,
                video_name: video.name,
                reka_indexing_status: video.reka_indexing_status
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showToast(data.error, 'error');
            return;
        }
        
        showToast('Video downloaded successfully!', 'success');
        loadAllVideos();
    } catch (error) {
        showToast('Download failed: ' + error.message, 'error');
    }
}

async function refreshStatus(rekaVideoId) {
    try {
        const response = await fetch(`/reka/refresh-status/${rekaVideoId}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.error) {
            showToast(data.error, 'error');
            return;
        }
        
        showToast(`Status updated: ${data.indexing_status}`, 'success');
        loadAllVideos();
    } catch (error) {
        showToast('Failed to refresh status', 'error');
    }
}

async function deleteLocal(filename) {
    if (!confirm(`Delete local copy of "${filename}"?`)) return;
    
    try {
        const response = await fetch('/delete-file', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: filename })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showToast(data.error, 'error');
            return;
        }
        
        showToast('Local file deleted', 'success');
        loadAllVideos();
        
        // Clear selection if deleted
        if (currentVideo && currentVideo.local_filename === filename) {
            currentVideo = null;
            videoInfo.classList.add('hidden');
            chatSection.style.display = 'none';
            paramsSection.style.display = 'none';
        }
    } catch (error) {
        showToast('Failed to delete file', 'error');
    }
}

async function deleteReka(rekaVideoId) {
    if (!confirm('Delete this video from Reka?')) return;
    
    try {
        const response = await fetch(`/reka/delete/${rekaVideoId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.error) {
            showToast(data.error, 'error');
            return;
        }
        
        showToast('Reka video deleted', 'success');
        loadAllVideos();
        
        // Clear selection if deleted
        if (currentVideo && currentVideo.reka_video_id === rekaVideoId) {
            currentVideo = null;
            videoInfo.classList.add('hidden');
            chatSection.style.display = 'none';
            paramsSection.style.display = 'none';
        }
    } catch (error) {
        showToast('Failed to delete video', 'error');
    }
}

async function uploadToGemini(video) {
    const button = event.target.tagName === 'BUTTON' ? event.target : event.target.closest('button');
    if (!button || !button.classList.contains('upload-gemini-btn')) {
        showToast('Button element not found', 'error');
        return;
    }
    
    const originalHtml = button.innerHTML;
    
    try {
        button.disabled = true;
        button.innerHTML = '<span class="material-symbols-rounded" style="animation: spin 1s linear infinite;">sync</span> Uploading...';
        
        const response = await fetch('/videos/upload-to-gemini', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: video.filename })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showToast('Upload failed: ' + data.error, 'error');
            button.disabled = false;
            button.innerHTML = originalHtml;
            return;
        }
        
        showToast('Video uploaded to Gemini successfully!', 'success');
        loadAllVideos();
    } catch (error) {
        showToast('Upload to Gemini failed: ' + error.message, 'error');
        button.disabled = false;
        button.innerHTML = originalHtml;
    }
}

// File Upload Handlers
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        uploadVideo(file);
    }
}

async function uploadVideo(file) {
    const formData = new FormData();
    formData.append('video', file);

    // Get video name from input if provided
    const videoNameInput = document.getElementById('file-video-name');
    const videoName = videoNameInput.value.trim();
    if (videoName) {
        formData.append('video_name', videoName);
    }

    try {
        showToast('Uploading video...', 'info');

        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            showToast(data.error, 'error');
            return;
        }

        // Show success and auto-upload info
        if (data.reka_synced) {
            showToast('Video uploaded and synced to Reka!', 'success');
        } else {
            showToast('Video uploaded successfully!', 'success');
            if (data.reka_upload_error) {
                showToast('Reka sync failed: ' + data.reka_upload_error, 'warning');
            }
        }

        // Reload video list
        loadAllVideos();

        // Reset file input and name input
        videoInput.value = '';
        videoNameInput.value = '';

    } catch (error) {
        showToast('Upload failed: ' + error.message, 'error');
    }
}

// Extraction Handler
async function handleExtraction() {
    if (!currentVideo) {
        showToast('Please select a video first', 'error');
        return;
    }
    
    if (currentVideo.source === 'url') {
        showToast('Frame extraction coming soon — this will download the video', 'info');
        return;
    }
    
    if (!currentVideo.local_filepath) {
        showToast('Please select a video with local copy first', 'error');
        return;
    }
    
    const timestampsInput = document.getElementById('timestamps').value;
    
    if (!timestampsInput) {
        showToast('Please enter timestamps', 'error');
        return;
    }
    
    // Parse timestamps and convert to floats
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
        showToast(error.message, 'error');
        return;
    }
    
    const params = {
        filepath: currentVideo.local_filepath,
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
            showToast(data.error, 'error');
            return;
        }
        
        displayResults(data);
        showToast('Frames extracted successfully!', 'success');
        
    } catch (error) {
        showToast('Extraction failed: ' + error.message, 'error');
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
                    <span class="material-symbols-rounded">folder_zip</span>
                    Download All Frames (ZIP)
                </a>
                <button onclick="deleteAllFrames('${outputDirName}')" class="btn btn-delete-all-frames">
                    <span class="material-symbols-rounded">delete_sweep</span>
                    Delete All Frames
                </button>
            </div>
        </div>
        
        <h3>Preview & Download Individual Frames</h3>
        <div class="frames-grid" id="frames-grid-${outputDirName}">
            ${data.frames.map(frame => `
                <div class="frame-item" id="frame-${escapeHtml(frame).replace(/[^a-zA-Z0-9]/g, '_')}">
                    <img src="/frames/${outputDirName}/${frame}" alt="${frame}">
                    <div class="frame-footer">
                        <div class="frame-name">${frame}</div>
                        <div class="frame-actions">
                            <a href="/download-frame/${outputDirName}/${frame}" 
                               class="btn-download-frame" 
                               title="Download ${frame}">
                                <span class="material-symbols-rounded">download</span>
                            </a>
                            <button onclick="deleteSingleFrame('${outputDirName}', '${escapeHtml(frame)}')" 
                                    class="btn-delete-frame" 
                                    title="Delete ${frame}">
                                <span class="material-symbols-rounded">delete</span>
                            </button>
                        </div>
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

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icons = {
        'success': 'check_circle',
        'error': 'error',
        'warning': 'warning',
        'info': 'info'
    };
    
    toast.innerHTML = `
        <span class="material-symbols-rounded">${icons[type] || 'info'}</span>
        <span>${escapeHtml(message)}</span>
    `;
    
    container.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);
    
    // Remove after 4 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function showError(message) {
    showToast(message, 'error');
}

// Chat Functions
async function sendChatMessage() {
    if (!currentVideo || !currentVideo.filename) {
        showToast('Please select a local video first', 'error');
        return;
    }
    
    const question = chatInput.value.trim();
    if (!question) return;
    
    // Add user message to chat
    addChatMessage('user', question);
    chatInput.value = '';
    chatSendBtn.disabled = true;
    
    // Add loading indicator
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'chat-message assistant loading';
    loadingDiv.innerHTML = '<div class="spinner-small"></div><p>Thinking...</p>';
    chatMessagesDiv.appendChild(loadingDiv);
    chatMessagesDiv.scrollTop = chatMessagesDiv.scrollHeight;
    
    try {
        const response = await fetchWithTimeout('/gemini/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filename: currentVideo.filename,
                messages: [...chatMessages, { role: 'user', content: question }]
            })
        }, 120000); // 2 minutes timeout
        
        const data = await response.json();
        
        // Remove loading indicator
        loadingDiv.remove();
        
        if (data.error) {
            addChatMessage('error', data.error);
            return;
        }
        
        // Extract answer from response
        let answer = data.answer || 'No response received';
        
        // Auto-extract timestamps from AI response
        const timestampMatch = answer.match(/TIMESTAMPS:\s*([\d.,\s]+)/i);
        if (timestampMatch) {
            const timestampsValue = timestampMatch[1].trim().replace(/,\s*$/, '');
            document.getElementById('timestamps').value = timestampsValue;
            document.getElementById('params-section').style.display = '';
        } else {
            // Fallback: extract unique timestamps from KEYFRAME_[seconds] patterns
            const keyframeMatches = [...answer.matchAll(/KEYFRAME_([\d.]+)/g)];
            if (keyframeMatches.length > 0) {
                const uniqueTimestamps = [...new Set(keyframeMatches.map(m => m[1]))];
                document.getElementById('timestamps').value = uniqueTimestamps.join(', ');
                document.getElementById('params-section').style.display = '';
            }
        }

        // Add assistant message
        addChatMessage('assistant', answer);
        
        // Update chat history
        chatMessages.push({ role: 'user', content: question });
        chatMessages.push({ role: 'assistant', content: answer });
        
    } catch (error) {
        loadingDiv.remove();
        addChatMessage('error', 'Failed to get response: ' + error.message);
    } finally {
        chatSendBtn.disabled = false;
    }
}

function addChatMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}`;
    
    // Format content - preserve line breaks and basic formatting
    const formattedContent = content
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/```(.*?)```/gs, '<pre>$1</pre>');
    
    if (role === 'user') {
        messageDiv.innerHTML = `
            <div class="message-content">${formattedContent}</div>
        `;
    } else if (role === 'assistant') {
        messageDiv.innerHTML = `
            <div class="message-content">${formattedContent}</div>
            <button class="download-md-btn" onclick='downloadAsMarkdown(${JSON.stringify(content).replace(/'/g, "&#39;")})' title="Download as Markdown">
                <span class="material-symbols-rounded">download</span>
                <span>Download MD</span>
            </button>
        `;
    } else if (role === 'error') {
        messageDiv.innerHTML = `
            <div class="message-icon">
                <span class="material-symbols-rounded">error</span>
            </div>
            <div class="message-content">${formattedContent}</div>
        `;
    }
    
    chatMessagesDiv.appendChild(messageDiv);
    chatMessagesDiv.scrollTop = chatMessagesDiv.scrollHeight;
}

function downloadAsMarkdown(content) {
    // Create blob from content
    const blob = new Blob([content], { type: 'text/markdown' });
    
    // Generate filename with timestamp
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    const videoName = currentVideo?.name?.replace(/[^a-z0-9]/gi, '_').toLowerCase() || 'video';
    const filename = `${videoName}_answer_${timestamp}.md`;
    
    // Create download link and trigger download
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    
    // Cleanup
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showToast('Markdown file downloaded!', 'success');
}

// Frame Deletion Functions
async function deleteSingleFrame(jobName, filename) {
    if (!confirm(`Delete frame "${filename}"?`)) return;
    
    try {
        const response = await fetch(`/delete-frame/${jobName}/${filename}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.error) {
            showToast(data.error, 'error');
            return;
        }
        
        // Remove frame from UI
        const frameId = `frame-${filename.replace(/[^a-zA-Z0-9]/g, '_')}`;
        const frameElement = document.getElementById(frameId);
        if (frameElement) {
            frameElement.style.opacity = '0';
            frameElement.style.transform = 'scale(0.8)';
            setTimeout(() => frameElement.remove(), 300);
        }
        
        showToast('Frame deleted successfully', 'success');
    } catch (error) {
        showToast('Failed to delete frame: ' + error.message, 'error');
    }
}

async function deleteAllFrames(jobName) {
    if (!confirm(`Delete ALL frames for "${jobName}"? This cannot be undone.`)) return;
    
    try {
        const response = await fetch(`/delete-all-frames/${jobName}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.error) {
            showToast(data.error, 'error');
            return;
        }
        
        // Hide results section
        resultsSection.style.display = 'none';
        resultsContent.innerHTML = '';
        
        showToast('All frames deleted successfully', 'success');
    } catch (error) {
        showToast('Failed to delete frames: ' + error.message, 'error');
    }
}
