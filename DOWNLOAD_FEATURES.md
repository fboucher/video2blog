# Download Features Guide

## Overview

The Keyframe Extractor now includes three convenient ways to download your extracted frames:

1. **Download All Frames (ZIP)** - Get all extracted frames in a single compressed file
2. **Download Individual Frames** - Download specific frames one at a time
3. **Download Metadata JSON** - Get detailed extraction information

## How to Use

### 1. Download All Frames as ZIP

After extraction completes, you'll see a button:
```
📦 Download All Frames (ZIP)
```

**What's included:**
- All extracted frame images (.jpg files)
- Metadata JSON file with extraction details
- Compressed into a single .zip file

**Example filename:** `video_frames.zip`

**Use case:** When you want to get all frames at once for offline processing or archiving.

### 2. Download Individual Frames

Each frame in the preview has a download button (⬇️) in the bottom right corner.

**Steps:**
1. Find the frame you want in the preview grid
2. Click the ⬇️ download icon
3. Frame downloads immediately to your browser's download folder

**Example filename:** `keyframe_0001_t5.23s.jpg` or `frame_ts000_10.50s_exact_f000315.jpg`

**Use case:** When you only need specific frames instead of the entire set.

### 3. Download Metadata JSON

Click the green button:
```
📄 Download Metadata JSON
```

**What's included:**
- Video information (duration, FPS, resolution)
- Extraction parameters used
- List of all extracted frames with details:
  - Frame numbers
  - Timestamps
  - Filenames

**Scene Detection metadata includes:**
```json
{
  "video_path": "/app/uploads/video.mp4",
  "total_frames": 7200,
  "duration": 240.0,
  "fps": 30.0,
  "keyframes_extracted": 45,
  "threshold": 0.3,
  "keyframes": [
    {
      "frame": 150,
      "timestamp": 5.0,
      "filename": "keyframe_0001_t5.00s.jpg"
    },
    ...
  ]
}
```

**Timestamp extraction metadata includes:**
```json
{
  "video_path": "/app/uploads/video.mp4",
  "total_frames": 7200,
  "duration": 240.0,
  "fps": 30.0,
  "requested_timestamps": [10.5, 25.0, 60.3],
  "frames_per_timestamp": 3,
  "total_frames_extracted": 9,
  "frames": [
    {
      "timestamp_index": 0,
      "target_timestamp": 10.5,
      "actual_timestamp": 10.467,
      "frame_number": 314,
      "offset_from_target": -1,
      "filename": "frame_ts000_10.50s_-1_f000314.jpg"
    },
    ...
  ]
}
```

## API Endpoints

If you're accessing the service programmatically:

### Download All Frames (ZIP)
```
GET /download-all/{job_name}
```
**Example:** `http://localhost:5000/download-all/video`

**Returns:** ZIP file containing all frames and metadata

### Download Single Frame
```
GET /download-frame/{job_name}/{filename}
```
**Example:** `http://localhost:5000/download-frame/video/keyframe_0001_t5.00s.jpg`

**Returns:** JPEG image file

### Download Metadata
```
GET /metadata/{job_name}/{metadata_file}
```
**Example:** `http://localhost:5000/metadata/video/keyframes_metadata.json`

**Returns:** JSON file

## File Storage

All extracted frames are stored in the `output` directory on your host machine:

```
./output/
├── video/
│   ├── keyframe_0001_t5.23s.jpg
│   ├── keyframe_0002_t12.45s.jpg
│   ├── ...
│   └── keyframes_metadata.json
└── another_video/
    ├── frame_ts000_10.50s_exact_f000315.jpg
    ├── ...
    └── timestamp_frames_metadata.json
```

You can access these files directly from the filesystem if needed.

## Tips

1. **Large extractions:** If you extracted many frames (100+), use the ZIP download to avoid downloading files one by one.

2. **Preview limitation:** The web interface shows the first 20 frames only. All frames are included in the ZIP download.

3. **Direct access:** Files in `./output/` on your host machine are the same as what you download through the web interface.

4. **Metadata usage:** Use the JSON metadata to:
   - Build frame catalogs
   - Create timelines
   - Automate post-processing workflows
   - Track extraction parameters

5. **Batch processing:** You can extract multiple videos and download them all at once by accessing the output directory.

## Troubleshooting

**ZIP download is slow:**
- Normal for large frame sets
- Progress depends on frame count and resolution
- Consider reducing max_frames or using lower resolution source videos

**Individual download doesn't work:**
- Check browser's download settings
- Ensure pop-ups aren't blocked
- Try right-click → "Save link as"

**Can't find downloaded files:**
- Check browser's default download folder
- Look in Downloads folder on your system
- Check browser's download history (Ctrl+J / Cmd+J)

**Empty ZIP file:**
- Ensure extraction completed successfully
- Check the output directory has files
- Restart the container and try again
