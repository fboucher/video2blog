# Workflow

Video2Blog turns videos into blog posts in four steps.

## Step 1: Select or Upload a Video

Both local file uploads and URLs (YouTube, Vimeo, direct links) are supported.

**Upload:** Drag and drop or click to select a video file. Supported formats: MP4, AVI, MOV, MKV, WebM, FLV.

**URL:** Paste a video URL. The application downloads it via yt-dlp in the background.

Once uploaded, the video appears in the **Your Videos** list. A green **Ready** badge means it's been uploaded to Gemini and is ready for AI queries. A yellow **Indexing** badge means it's still processing.

## Step 2: Chat with AI

Select a video and use the chat panel to ask questions about it. The default prompt requests a blog post draft with relevant timestamps.

The AI assistant:
- Analyzes the full video using Gemini's vision capabilities
- Writes a blog post draft in markdown
- Suggests 3 key timestamps for important visual moments

Timestamps are automatically populated into **Step 3** as editable rows.

## Step 3: Configure Extraction

Fine-tune which frames to extract from the video.

**Keyframe List:** Each suggested timestamp appears as a row with:
- ☑ Checkbox — include/exclude the keyframe
- ✏️ Editable timestamp — change the second value
- 🗑️ Delete — remove unwanted keyframes

**Auto-Detect:** Run scene-detection (histogram analysis) to find scene changes automatically. Available for local videos.

**Add Keyframe:** Manually add timestamps for custom extraction points.

**Frames per Keyframe:** Number of frames to extract around each timestamp (default: 1). A value of 3 extracts the frame before, at, and after the timestamp.

Click **Extract Frames** to run the extraction. For URL videos, the video is downloaded first. Results appear in **Step 4**.

## Step 4: Edit with AI Blog Editor

Open the **AI Blog Editor** to refine your draft using AI-powered skills.

The editor has a split-pane layout:
- **Left:** Your blog post with full editing control
- **Right:** AI tools panel

**Skills:** Pre-built editing actions (e.g., copy editing, fact-checking). Each skill is a system prompt that guides the AI on how to edit the text.

**Custom Prompts:** Write any instruction for the AI to follow.

**Version History:** Every edit is versioned. Restore previous versions anytime.

**Apply:** Accept AI suggestions directly into your draft.

See [Skills](skills.md) for details on creating custom skills.
