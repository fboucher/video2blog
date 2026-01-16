# Keyframe Extractor

A Python application with a web interface to extract keyframes from video files using OpenCV. Run in a Docker/Podman container for easy deployment.

## Features

- **Web Interface:** User-friendly browser-based UI for uploading videos and configuring extraction
- **Two extraction modes:**
  - Automatic scene detection using histogram comparison
  - Timestamp-based extraction for precise frame capture
- Configurable detection threshold
- Maximum frame limit to control output size
- Extract multiple frames around specific timestamps
- Metadata export with timestamps
- Real-time preview of extracted frames
- Docker/Podman containerized for easy deployment

## Quick Start (Web Interface - Recommended)

1. **Build the container:**
   ```bash
   podman build -t extractor .
   # or with Docker:
   docker build -t extractor .
   ```

2. **Create necessary directories:**
   ```bash
   mkdir -p uploads output
   ```

3. **Start the web application:**
   ```bash
   # Using Podman:
   podman run -d --name extractor-web -p 5000:5000 \
     -v $(pwd)/uploads:/app/uploads \
     -v $(pwd)/output:/app/output \
     extractor
   
   # Or using Docker:
   docker run -d --name extractor-web -p 5000:5000 \
     -v $(pwd)/uploads:/app/uploads \
     -v $(pwd)/output:/app/output \
     extractor
   
   # Or using docker-compose/podman-compose:
   docker-compose up -d
   ```

4. **Open your browser and navigate to:**
   ```
   http://localhost:5000
   ```

5. **Use the web interface to:**
   - Upload your video file
   - Choose extraction mode (Scene Detection or Timestamp)
   - Configure parameters
   - Extract frames and preview results

### Stopping the Container

```bash
# Podman:
podman stop extractor-web
podman rm extractor-web

# Docker:
docker stop extractor-web
docker rm extractor-web
```

## Usage

### Web Interface (Recommended)

The web interface provides an intuitive way to extract frames:

1. **Upload Video:** Drag and drop or click to select your video file
2. **Choose Mode:** 
   - **Scene Detection:** Automatically finds scene changes
   - **Timestamp Extraction:** Extract frames at specific times
3. **Configure Parameters:**
   - Scene Detection: Set threshold and max frames
   - Timestamp: Enter comma-separated timestamps (e.g., `10.5, 25.0, 60.3`)
4. **Extract:** Click the extract button and view results
5. **Download:** Preview frames and download metadata JSON

### Command Line Interface

The application also supports CLI usage for automation:

#### Mode 1: Scene Detection

Automatically detects scene changes and extracts keyframes:

```bash
python keyframe_extractor.py video.mp4 -o ./frames -t 0.3 -m 100
```

#### Mode 2: Timestamp-Based Extraction

Extract frames at specific timestamps (in seconds):

```bash
python keyframe_extractor.py video.mp4 --timestamps 10.5,25.0,60.3 -o ./frames
```

By default, this extracts 3 frames per timestamp (1 before, 1 at, 1 after). You can customize this:

```bash
python keyframe_extractor.py video.mp4 --timestamps 10.5,25.0 --frames-per-timestamp 5 -o ./frames
```

### Command Line Arguments

```
usage: keyframe_extractor.py [-h] [-o OUTPUT] [-t THRESHOLD] [-m MAX_FRAMES] 
                             [--timestamps TIMESTAMPS] [--frames-per-timestamp N]
                             video_path

Extract keyframes from video files

positional arguments:
  video_path            Path to the input video file

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output directory for keyframes (default: ./keyframes)
  -t THRESHOLD, --threshold THRESHOLD
                        Scene detection threshold (0.0-1.0) (default: 0.3)
  -m MAX_FRAMES, --max-frames MAX_FRAMES
                        Maximum number of keyframes to extract (default: 100)
  --timestamps TIMESTAMPS
                        Comma-separated list of timestamps (in seconds) to extract frames at
                        Example: "10.5,25.0,60.3"
  --frames-per-timestamp N
                        Number of frames to extract per timestamp (default: 3)
                        Frames are distributed around the target timestamp
```

### Docker Compose

The docker-compose.yml file is configured to run the web interface:

```bash
# Start the web service
docker-compose up -d

# Access at http://localhost:5000
```

To use CLI mode with docker-compose, override the command:

```bash
docker-compose run --rm extractor python keyframe_extractor.py /app/uploads/video.mp4 --timestamps 10.5,25.0 -o /app/output
```

## Parameters

- **Threshold** (0.0-1.0): Lower values detect more scenes, higher values detect fewer scenes
- **Max Frames**: Maximum number of keyframes to extract (default: 100)
- **Output Directory**: Where extracted keyframes will be saved

## Output

### Scene Detection Mode

Creates:
- Individual keyframe images named `keyframe_NNNN_tXX.XXs.jpg`
- `keyframes_metadata.json` with extraction details

### Timestamp Mode

Creates:
- Individual frame images named `frame_tsNNN_XX.XXs_±N_fXXXXXX.jpg`
  - `tsNNN`: Timestamp index (which timestamp in your list)
  - `XX.XXs`: Target timestamp
  - `±N`: Offset from target (e.g., `-1`, `exact`, `+1`)
  - `fXXXXXX`: Actual frame number
- `timestamp_frames_metadata.json` with detailed extraction information

## Examples

### Scene Detection Examples

```bash
# Extract keyframes with custom settings
python keyframe_extractor.py video.mp4 -o ./frames -t 0.2 -m 50
```

This will extract up to 50 keyframes with a more sensitive scene detection threshold.

### Timestamp Extraction Examples

```bash
# Extract 3 frames around specific timestamps
python keyframe_extractor.py video.mp4 --timestamps 10.5,25.0,60.3 -o ./frames

# Extract 5 frames per timestamp (2 before, 1 exact, 2 after)
python keyframe_extractor.py video.mp4 --timestamps 30.0,90.5 --frames-per-timestamp 5 -o ./frames

# Extract single frame at exact timestamp
python keyframe_extractor.py video.mp4 --timestamps 45.2 --frames-per-timestamp 1 -o ./frames
```

### Docker CLI Examples

To use the CLI directly in Docker/Podman:

```bash
# Scene detection mode
podman run --rm -v $(pwd)/uploads:/app/uploads -v $(pwd)/output:/app/output \
  extractor python keyframe_extractor.py /app/uploads/video.mp4 -o /app/output

# Timestamp mode
podman run --rm -v $(pwd)/uploads:/app/uploads -v $(pwd)/output:/app/output \
  extractor python keyframe_extractor.py /app/uploads/video.mp4 \
  --timestamps 10.5,25.0,60.3 -o /app/output
```

## Architecture

- **Web Application:** Flask-based web server with REST API
- **Frontend:** Pure HTML/CSS/JavaScript with drag-and-drop upload
- **Backend:** Python with OpenCV for video processing
- **Storage:** Volume-mounted directories for uploads and outputs
- **Port:** 5000 (HTTP)

## File Structure

```
.
├── keyframe_extractor.py   # Core extraction logic
├── web_app.py              # Flask web application
├── templates/
│   └── index.html          # Web interface
├── static/
│   ├── css/
│   │   └── style.css       # Styling
│   └── js/
│       └── app.js          # Frontend logic
├── Dockerfile              # Container definition
├── docker-compose.yml      # Compose configuration
├── requirements.txt        # Python dependencies
├── uploads/                # Video uploads (volume mount)
└── output/                 # Extracted frames (volume mount)
```