# Quick Start Guide - Keyframe Extractor Web Interface

## Getting Started in 3 Steps

### 1. Build and Start the Container

```bash
# Build the container
podman build -t extractor .

# Create directories
mkdir -p uploads output

# Start the web application
podman run -d --name extractor-web -p 5000:5000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/output:/app/output \
  extractor
```

### 2. Open Your Browser

Navigate to: **http://localhost:5000**

### 3. Extract Frames

#### Using Scene Detection:
1. Upload your video file (drag & drop or click)
2. Select "Scene Detection" mode
3. Adjust threshold (0.3 recommended) and max frames (100)
4. Click "Extract Frames"
5. Preview results and download:
   - **Download All Frames (ZIP)** - Get all extracted frames in one file
   - **Download individual frames** - Click ⬇️ on any frame
   - **Download Metadata JSON** - Get extraction details

#### Using Timestamp Extraction:
1. Upload your video file
2. Select "Timestamp Extraction" mode
3. Enter timestamps: `10.5, 25.0, 60.3` (comma-separated seconds)
4. Set frames per timestamp (default: 3)
5. Click "Extract Frames"
6. Preview results and download:
   - **Download All Frames (ZIP)** - Get all frames + metadata
   - **Download individual frames** - Click ⬇️ on specific frames
   - **Download Metadata JSON** - Get timestamp details

## Container Management

```bash
# View logs
podman logs extractor-web

# Stop container
podman stop extractor-web

# Start again
podman start extractor-web

# Remove container
podman stop extractor-web && podman rm extractor-web

# Rebuild after changes
podman build -t extractor . && podman stop extractor-web && podman rm extractor-web && \
podman run -d --name extractor-web -p 5000:5000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/output:/app/output \
  extractor
```

## Accessing Results

- **Extracted frames**: `./output/<video-name>/`
- **Metadata JSON**: `./output/<video-name>/*_metadata.json`
- **Web preview**: Available in browser after extraction
- **Download**: Click the metadata link in the results

## Troubleshooting

### Port already in use
```bash
# Change port to 5001
podman run -d --name extractor-web -p 5001:5000 ...
# Access at http://localhost:5001
```

### Container won't start
```bash
# Check logs
podman logs extractor-web

# Verify image exists
podman images extractor
```

### Can't upload video
- Check file format (MP4, AVI, MOV, MKV, WEBM, FLV)
- Ensure file size is under 500MB
- Verify `uploads` directory has write permissions

## Features

✅ Drag and drop video upload  
✅ Real-time video info display  
✅ Two extraction modes (Scene Detection & Timestamps)  
✅ Configurable parameters  
✅ Live preview of extracted frames  
✅ **Download all frames as ZIP**  
✅ **Download individual frames one by one**  
✅ Metadata JSON export  
✅ Persistent storage via volume mounts  

## Example Usage

**Extract keyframes at 5s, 15s, and 30s with 5 frames each:**
1. Upload video
2. Choose "Timestamp Extraction"
3. Enter: `5, 15, 30`
4. Set frames per timestamp: `5`
5. Extract

This will create 15 frames total (5 frames × 3 timestamps), distributed around each timestamp.
