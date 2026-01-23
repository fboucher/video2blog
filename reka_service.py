#!/usr/bin/env python3
"""Reka API Service for video operations and Q&A."""

import os
from typing import Dict, List, Any

import requests
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

REKA_API_KEY = os.getenv('REKA_API_KEY')
REKA_BASE_URL = os.getenv('REKA_BASE_URL', 'https://vision-agent.api.reka.ai')


def get_headers() -> Dict[str, str]:
    """Get headers for Reka API requests.
    
    Returns:
        Dictionary with API headers.
    """
    return {
        'X-Api-Key': REKA_API_KEY,
        'Content-Type': 'application/json'
    }


def list_videos() -> Dict[str, Any]:
    """List all videos from Reka.
    
    Returns:
        Dictionary with videos list or error.
    """
    if not REKA_API_KEY:
        return {'error': 'REKA_API_KEY not configured'}
    
    url = f"{REKA_BASE_URL}/v1/videos"
    
    try:
        response = requests.get(url, headers=get_headers(), timeout=30)
        response.raise_for_status()
        return {'success': True, 'videos': response.json()}
    except requests.exceptions.RequestException as e:
        return {'error': f'Failed to list videos: {str(e)}'}


def upload_video(
    video_path: str,
    video_name: str,
    index: bool = True,
    enable_thumbnails: bool = False,
    group_id: str = "default"
) -> Dict[str, Any]:
    """Upload a video to Reka.

    Args:
        video_path: Local path to video file.
        video_name: Name for the video in Reka system.
        index: Whether to index the video for search/QA.
        enable_thumbnails: Whether to generate thumbnails.
        group_id: Video group assignment (defaults to "default").
    
    Returns:
        Dictionary with upload result, video_id, or error.
    """
    if not REKA_API_KEY:
        return {'error': 'REKA_API_KEY not configured'}
    
    if not os.path.exists(video_path):
        return {'error': f'Video file not found: {video_path}'}
    
    url = f"{REKA_BASE_URL}/v1/videos/upload"

    data = {
        'index': index,
        'enable_thumbnails': enable_thumbnails,
        'video_name': video_name,
        'group_id': group_id,
    }

    headers = {
        'X-Api-Key': REKA_API_KEY
    }
    
    try:
        with open(video_path, 'rb') as file:
            filename = os.path.basename(video_path)
            files = {'file': (filename, file, 'video/mp4')}
            response = requests.post(
                url,
                headers=headers,
                data=data,
                files=files,
                timeout=300  # 5 minutes for upload
            )
            response.raise_for_status()
            response_data = response.json()
            
            # Extract video_id for database sync tracking
            video_id = response_data.get('video_id')
            
            return {
                'success': True,
                'video_id': video_id,
                'data': response_data,
                'message': f'Successfully uploaded: {video_name}'
            }
    except requests.exceptions.RequestException as e:
        return {'error': f'Failed to upload video: {str(e)}'}


def upload_video_from_url(
    video_url: str,
    video_name: str,
    index: bool = True,
    enable_thumbnails: bool = False,
    group_id: str = "default"
) -> Dict[str, Any]:
    """Upload a video to Reka directly from a URL.

    Args:
        video_url: URL to the video (YouTube, Vimeo, direct video URL, etc.)
        video_name: Name for the video in Reka system.
        index: Whether to index the video for search/QA.
        enable_thumbnails: Whether to generate thumbnails.
        group_id: Video group assignment (defaults to "default").

    Returns:
        Dictionary with upload result, video_id, or error.
    """
    if not REKA_API_KEY:
        return {'error': 'REKA_API_KEY not configured'}

    url = f"{REKA_BASE_URL}/v1/videos/upload"

    data = {
        'index': index,
        'enable_thumbnails': enable_thumbnails,
        'video_name': video_name,
        'video_url': video_url,  # Reka downloads from this URL
        'group_id': group_id,
    }

    headers = {'X-Api-Key': REKA_API_KEY}

    try:
        response = requests.post(
            url,
            headers=headers,
            data=data,
            timeout=300  # 5 minutes
        )
        response.raise_for_status()
        response_data = response.json()

        video_id = response_data.get('video_id')

        return {
            'success': True,
            'video_id': video_id,
            'data': response_data,
            'message': f'Successfully uploaded from URL: {video_name}'
        }
    except requests.exceptions.RequestException as e:
        return {'error': f'Failed to upload video from URL: {str(e)}'}


def delete_video(video_id: str) -> Dict[str, Any]:
    """Delete a video from Reka.

    Args:
        video_id: ID of the video to delete.

    Returns:
        Dictionary with deletion result or error.
    """
    if not REKA_API_KEY:
        return {'error': 'REKA_API_KEY not configured'}

    url = f"{REKA_BASE_URL}/v1/videos/{video_id}"

    try:
        response = requests.delete(
            url,
            headers={'X-Api-Key': REKA_API_KEY},
            timeout=30
        )
        response.raise_for_status()
        return {'success': True, 'message': 'Video deleted successfully'}
    except requests.exceptions.RequestException as e:
        return {'error': f'Failed to delete video: {str(e)}'}


def ask_question(video_id: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Ask a question about a video using Reka Q&A.
    
    Args:
        video_id: ID of the video to query.
        messages: List of message dictionaries with 'role' and 'content'.
    
    Returns:
        Dictionary with answer or error.
    """
    if not REKA_API_KEY:
        return {'error': 'REKA_API_KEY not configured'}
    
    url = f"{REKA_BASE_URL}/v1/qa/chat"
    
    payload = {
        'video_id': video_id,
        'messages': messages
    }
    
    try:
        response = requests.post(
            url,
            json=payload,
            headers=get_headers(),
            timeout=120  # 2 minutes for Q&A responses
        )
        response.raise_for_status()
        return {'success': True, 'data': response.json()}
    except requests.exceptions.RequestException as e:
        return {'error': f'Failed to ask question: {str(e)}'}


def is_configured() -> bool:
    """Check if Reka API is properly configured.
    
    Returns:
        True if API key is set, False otherwise.
    """
    return bool(REKA_API_KEY)


def download_video(video_url: str, save_path: str) -> Dict[str, Any]:
    """Download video file from Reka CDN.
    
    Args:
        video_url: Direct URL to video file (from Reka API).
        save_path: Local path where to save the video.
        
    Returns:
        Dictionary with success status, filepath, and bytes downloaded.
    """
    try:
        # Stream download to avoid memory issues with large files
        response = requests.get(video_url, stream=True, timeout=300)
        response.raise_for_status()
        
        total_bytes = 0
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    total_bytes += len(chunk)
        
        return {
            'success': True,
            'filepath': save_path,
            'bytes_downloaded': total_bytes
        }
        
    except requests.exceptions.RequestException as e:
        # Clean up partial download
        if os.path.exists(save_path):
            os.remove(save_path)
        return {'error': f'Download failed: {str(e)}'}
    except Exception as e:
        if os.path.exists(save_path):
            os.remove(save_path)
        return {'error': f'Unexpected error: {str(e)}'}

