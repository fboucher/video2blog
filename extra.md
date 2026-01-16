
## Example with file upload to REKA

```python
import requests
import json

url = f"{BASE_URL}/v1/videos/upload"
video_path = "/content/demo.mp4" # local video path

# Video indexing request body for a local video
data = {
   "index": True, # boolean value indicating whether the video should be indexed for search/qa/etc
   "enable_thumbnails": False, # boolean value indicating whether to generate thumbnails for video chunks, this will increase the indexing time but will allow for quick thumbnail loading at search time
   "video_name": "vid16", # name of video to store in vision agent system for informative purpose. not ID
   "video_start_absolute_timestamp": "2025-04-12T19:05:45", # (Optional) a absolute timestamp indicating video start time in ISO 8601 format
   "group_id": "20f4bc2d-3ebe-4fd2-829f-9d88c79e8a37", # optional video group assignment
}
headers = {
    "X-Api-Key": REKA_API_KEY
}

# Open the video file and send the request
with open(video_path, "rb") as file:
    files = {"file": (video_path[1:], file, "video/mp4")}  # Send as multipart/form-data
    response = requests.post(url, headers=headers, data=data, files=files)

# Print response
print(response.status_code, response.json())
```

## Example list all video at Reka

```python
import requests

url = f"{BASE_URL}/v1/videos"
headers = {
    "X-Api-Key": REKA_API_KEY
}

response = requests.get(url, headers=headers)
print(response.status_code, response.json())
```

## Example Delate video at Reka

```python
curl -X DELETE https://vision-agent.api.reka.ai/v1/videos/550e8400-e29b-41d4-a716-446655440000 \
  -H "X-Api-Key: YOUR_API_KEY"
```


## Example of Q&A on video at Reka

```python
import requests
import json

url = f"{BASE_URL}/v1/qa/chat"

# Chat request body
payload = {
    "video_id": "550e8400-e29b-41d4-a716-446655440000",
    "messages": [
      {
        "role": "user",
        "content": "What is happening in this video?"
      }
    ]
}

headers = {
    "X-Api-Key": REKA_API_KEY,
    "Content-Type": "application/json",
}

response = requests.post(url, json=payload, headers=headers)
print(response.status_code, response.json())
```

