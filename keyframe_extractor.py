#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
from typing import List, Dict, Any

import cv2
import numpy as np

def extract_keyframes(
    video_path: str,
    output_dir: str,
    threshold: float = 0.3,
    max_frames: int = 100
) -> List[Dict[str, Any]]:
    """Extract keyframes from a video file using scene detection.
    
    Args:
        video_path: Path to the input video file.
        output_dir: Directory to save extracted keyframes.
        threshold: Scene detection threshold between 0.0 and 1.0. Lower values
            detect more scenes. Default is 0.3.
        max_frames: Maximum number of keyframes to extract. Default is 100.
    
    Returns:
        List of dictionaries containing frame metadata (frame number, timestamp, filename).
    
    Raises:
        ValueError: If video file cannot be opened or threshold is out of range.
        IOError: If output directory cannot be created.
    """
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Open video file
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Unable to open video file: {video_path}")
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    
    print(f"Video info: {duration:.2f}s, {fps:.2f} fps, {total_frames} frames")
    
    # Initialize variables
    keyframes = []
    prev_frame = None
    frame_count = 0
    saved_count = 0
    
    # Read video frame by frame
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # Skip frames to reduce processing (sample every 5th frame)
        if frame_count % 5 != 0:
            continue
        
        # Convert to grayscale for comparison
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if prev_frame is not None:
            # Calculate histograms
            hist_current = cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist_prev = cv2.calcHist([prev_frame], [0], None, [256], [0, 256])
            
            # Normalize histograms
            cv2.normalize(hist_current, hist_current, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
            cv2.normalize(hist_prev, hist_prev, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
            
            # Calculate histogram difference
            hist_diff = cv2.compareHist(hist_prev, hist_current, cv2.HISTCMP_CORREL)
            
            # If difference is significant, save as keyframe
            if hist_diff < (1 - threshold) and saved_count < max_frames:
                timestamp = frame_count / fps
                filename = f"keyframe_{saved_count:04d}_t{timestamp:.2f}s.jpg"
                output_path = os.path.join(output_dir, filename)
                
                cv2.imwrite(output_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
                keyframes.append({
                    'frame': frame_count,
                    'timestamp': timestamp,
                    'filename': filename
                })
                
                print(f"Saved keyframe {saved_count + 1}/{max_frames}: {filename} (t={timestamp:.2f}s)")
                saved_count += 1
        
        prev_frame = gray
        
        # Break if we've reached max frames
        if saved_count >= max_frames:
            break
    
    cap.release()
    
    # Save metadata
    metadata_path = os.path.join(output_dir, "keyframes_metadata.json")
    with open(metadata_path, 'w') as f:
        json.dump({
            'video_path': video_path,
            'total_frames': total_frames,
            'duration': duration,
            'fps': fps,
            'keyframes_extracted': len(keyframes),
            'threshold': threshold,
            'keyframes': keyframes
        }, f, indent=2)
    
    print(f"\nExtraction complete! Saved {len(keyframes)} keyframes to {output_dir}")
    print(f"Metadata saved to {metadata_path}")
    
    return keyframes


def extract_frames_at_timestamps(
    video_path: str,
    output_dir: str,
    timestamps: List[float],
    frames_per_timestamp: int = 3
) -> List[Dict[str, Any]]:
    """Extract frames at specific timestamps from a video file.
    
    For each timestamp, extracts the specified number of frames centered around
    that timestamp (1 before, 1 at, 1 after by default for 3 frames total).
    
    Args:
        video_path: Path to the input video file.
        output_dir: Directory to save extracted frames.
        timestamps: List of timestamps (in seconds) where frames should be extracted.
        frames_per_timestamp: Number of frames to extract per timestamp (default: 3).
            Frames are distributed around the target timestamp.
    
    Returns:
        List of dictionaries containing frame metadata (frame number, timestamp, filename).
    
    Raises:
        ValueError: If video file cannot be opened or timestamps are invalid.
        IOError: If output directory cannot be created.
    """
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Open video file
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Unable to open video file: {video_path}")
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    
    print(f"Video info: {duration:.2f}s, {fps:.2f} fps, {total_frames} frames")
    
    # Validate timestamps
    for ts in timestamps:
        if ts < 0 or ts > duration:
            cap.release()
            raise ValueError(f"Timestamp {ts:.2f}s is out of range (0.0-{duration:.2f}s)")
    
    extracted_frames = []
    
    # Calculate offset for frames around timestamp
    offset = (frames_per_timestamp - 1) // 2
    
    for ts_idx, timestamp in enumerate(timestamps):
        print(f"\nExtracting {frames_per_timestamp} frames around timestamp {timestamp:.2f}s...")
        
        # Calculate center frame number for this timestamp
        center_frame = int(timestamp * fps)
        
        # Extract frames around the center
        for i in range(-offset, frames_per_timestamp - offset):
            target_frame = center_frame + i
            
            # Skip if frame is out of bounds
            if target_frame < 0 or target_frame >= total_frames:
                print(f"  Skipping frame {target_frame} (out of bounds)")
                continue
            
            # Seek to the target frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            ret, frame = cap.read()
            
            if not ret:
                print(f"  Warning: Could not read frame {target_frame}")
                continue
            
            # Calculate actual timestamp
            actual_timestamp = target_frame / fps
            offset_label = f"{i:+d}" if i != 0 else "exact"
            
            # Generate filename
            filename = f"frame_ts{ts_idx:03d}_{timestamp:.2f}s_{offset_label}_f{target_frame:06d}.jpg"
            output_path = Path(output_dir) / filename
            
            # Save frame
            cv2.imwrite(str(output_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            
            extracted_frames.append({
                'timestamp_index': ts_idx,
                'target_timestamp': timestamp,
                'actual_timestamp': actual_timestamp,
                'frame_number': target_frame,
                'offset_from_target': i,
                'filename': filename
            })
            
            print(f"  Saved: {filename} (frame {target_frame}, t={actual_timestamp:.2f}s)")
    
    cap.release()
    
    # Save metadata
    metadata_path = Path(output_dir) / "timestamp_frames_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump({
            'video_path': video_path,
            'total_frames': total_frames,
            'duration': duration,
            'fps': fps,
            'requested_timestamps': timestamps,
            'frames_per_timestamp': frames_per_timestamp,
            'total_frames_extracted': len(extracted_frames),
            'frames': extracted_frames
        }, f, indent=2)
    
    print(f"\nExtraction complete! Saved {len(extracted_frames)} frames to {output_dir}")
    print(f"Metadata saved to {metadata_path}")
    
    return extracted_frames


def main():
    parser = argparse.ArgumentParser(
        description='Extract keyframes from video files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract keyframes using scene detection
  %(prog)s video.mp4 -o ./frames -t 0.3 -m 50
  
  # Extract 3 frames at specific timestamps
  %(prog)s video.mp4 --timestamps 10.5,25.0,60.3 -o ./frames
  
  # Extract 5 frames per timestamp
  %(prog)s video.mp4 --timestamps 10.5,25.0 --frames-per-timestamp 5 -o ./frames
        """
    )
    parser.add_argument('video_path', help='Path to the input video file')
    parser.add_argument('-o', '--output', default='./keyframes', help='Output directory for keyframes')
    parser.add_argument('-t', '--threshold', type=float, default=0.3, 
                       help='Scene detection threshold (0.0-1.0, default: 0.3)')
    parser.add_argument('-m', '--max-frames', type=int, default=100, 
                       help='Maximum number of keyframes to extract (default: 100)')
    parser.add_argument('--timestamps', type=str, 
                       help='Comma-separated list of timestamps (in seconds) to extract frames at, e.g., "10.5,25.0,60.3"')
    parser.add_argument('--frames-per-timestamp', type=int, default=3,
                       help='Number of frames to extract per timestamp (default: 3)')
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.video_path):
        print(f"Error: Video file not found: {args.video_path}")
        return 1
    
    # If timestamps provided, use timestamp extraction mode
    if args.timestamps:
        try:
            # Parse timestamps
            timestamps = [float(ts.strip()) for ts in args.timestamps.split(',')]
            
            # Validate frames_per_timestamp
            if args.frames_per_timestamp < 1:
                print(f"Error: frames-per-timestamp must be at least 1")
                return 1
            
            extract_frames_at_timestamps(
                args.video_path, 
                args.output, 
                timestamps, 
                args.frames_per_timestamp
            )
            return 0
        except ValueError as e:
            print(f"Error: Invalid timestamp format. Use comma-separated numbers (e.g., '10.5,25.0,60.3')")
            print(f"Details: {e}")
            return 1
        except Exception as e:
            print(f"Error: {e}")
            return 1
    else:
        # Use scene detection mode
        # Validate threshold
        if not 0.0 <= args.threshold <= 1.0:
            print(f"Error: Threshold must be between 0.0 and 1.0")
            return 1
        
        try:
            extract_keyframes(args.video_path, args.output, args.threshold, args.max_frames)
            return 0
        except Exception as e:
            print(f"Error: {e}")
            return 1

if __name__ == "__main__":
    exit(main())