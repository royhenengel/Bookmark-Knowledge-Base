# CloudConvert Fix - HTTP Request Nodes

## Problem Identified

The Code node approach failed with error:
```
$http is not defined [line 6]
ReferenceError
```

**Root cause:** n8n Code nodes don't have access to `$http` for making HTTP requests.

## Solution

Replace the Code node with **4 native HTTP Request nodes**:

1. **Create CloudConvert Job** - Initiates conversion with import/url
2. **Wait for CloudConvert** - Waits 30 seconds for processing
3. **Check CloudConvert Status** - Retrieves job result
4. **Download MP3** - Downloads the converted audio file

## Implementation

### Option 1: Import Fixed Workflow (Recommended)

1. **Deactivate current workflow** in n8n
2. **Delete the current workflow** (it has the broken Code node)
3. **Import new workflow:**
   - File: `workflows/TikTok_Complete_Processor_CLOUDCONVERT_FIXED.json`
4. **Activate the new workflow**
5. **Test with large video**

### Option 2: Manual Fix (If you want to keep existing workflow)

1. **Open your current workflow** in n8n editor

2. **Delete the "CloudConvert Audio Extract" node** (the Code node that's failing)

3. **Add 4 new HTTP Request nodes:**

#### Node 1: Create CloudConvert Job
- **Type:** HTTP Request
- **Method:** POST
- **URL:** `https://api.cloudconvert.com/v2/jobs`
- **Authentication:** Select your CloudConvert credential (ID: `6ntH86z73QMaDw41`)
- **Send Body:** Yes
- **Body Type:** JSON
- **JSON Body:**
```javascript
={{ {
  "tasks": {
    "import-video": {
      "operation": "import/url",
      "url": $('Get Video Info').item.json.video_download_url,
      "filename": "video.mp4"
    },
    "convert-audio": {
      "operation": "convert",
      "input": ["import-video"],
      "output_format": "mp3",
      "audio_codec": "mp3",
      "audio_bitrate": 128
    },
    "export-audio": {
      "operation": "export/url",
      "input": ["convert-audio"]
    }
  }
} }}
```

#### Node 2: Wait for CloudConvert
- **Type:** Wait
- **Wait Time:** 30 seconds

#### Node 3: Check CloudConvert Status
- **Type:** HTTP Request
- **Method:** GET
- **URL:** `={{ $('Create CloudConvert Job').item.json.data.links.self }}`
- **Authentication:** Select your CloudConvert credential

#### Node 4: Download MP3
- **Type:** HTTP Request
- **Method:** GET
- **URL:** `={{ $json.data.tasks.find(t => t.name === "export-audio").result.files[0].url }}`
- **Response Format:** File (under Options → Response → Response Format)

4. **Connect the nodes:**
```
Download Video → Create CloudConvert Job
Create CloudConvert Job → Wait for CloudConvert
Wait for CloudConvert → Check CloudConvert Status
Check CloudConvert Status → Download MP3
Download MP3 → Transcribe Audio
```

5. **Keep existing connection:**
```
Download Video → Upload to Google Drive
```

## Workflow Flow

```
Download Video (from TikTok)
    ↓
    ├─→ Upload to Google Drive
    │
    └─→ Create CloudConvert Job
            ↓
        Wait 30 seconds
            ↓
        Check CloudConvert Status
            ↓
        Download MP3
            ↓
        Transcribe Audio (Whisper)
```

## Why This Works

- ✅ **No Code node** - uses native n8n HTTP Request nodes
- ✅ **No `$http` dependency** - standard n8n functionality
- ✅ **import/url operation** - CloudConvert downloads video directly (no manual upload)
- ✅ **30-second wait** - sufficient for most TikTok videos (5-60 seconds)
- ✅ **Binary file handling** - native n8n file passing to Whisper

## Testing

After implementation, test with the large video:

```bash
curl -X POST https://royhen.app.n8n.cloud/webhook/analyze-video-complete \
  -H 'Content-Type: application/json' \
  -d '{"video_url":"https://www.tiktok.com/@agentic.james/video/7583734051748482317"}'
```

**Expected:**
- Processing time: ~45-55 seconds (30s CloudConvert + 15-25s other processing)
- HTTP 200 with complete JSON response including transcription

## Troubleshooting

### "Cannot read property 'result' of undefined"
- Job not finished after 30 seconds
- **Fix:** Increase wait time to 45 seconds

### "Cannot read property 'files' of undefined"
- CloudConvert conversion failed
- **Fix:** Check CloudConvert dashboard for error details

### Empty transcription
- Video has no speech (expected for music-only videos)
- This is normal behavior

## Next Steps

1. Import the fixed workflow
2. Test with large video
3. If successful, delete old broken workflow
4. Commit the working workflow to git
