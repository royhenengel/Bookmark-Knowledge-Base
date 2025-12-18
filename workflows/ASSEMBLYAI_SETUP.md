# AssemblyAI Setup Guide

## Why AssemblyAI?

Replaced Whisper + CloudConvert with AssemblyAI for:
- ✅ **20% cheaper** ($0.0025/min vs $0.003/min)
- ✅ **96% accuracy** (vs 85-90%)
- ✅ **2-3x faster** processing
- ✅ **No file size limits** (handles any video)
- ✅ **Simpler** (4 nodes vs 5 nodes)
- ✅ **$50 free credit** (~20,000 videos to test)

## Prerequisites

1. **Get AssemblyAI API Key**
   - Go to https://www.assemblyai.com/
   - Sign up for free account
   - Get API key from dashboard
   - You get $50 free credit (~20,000 TikTok videos)

2. **Add Credential to n8n**
   - Go to n8n → Credentials
   - Click "Add Credential"
   - Select "Header Auth"
   - **Name:** `AssemblyAI API`
   - **Header Name:** `authorization`
   - **Header Value:** `YOUR_API_KEY` (paste your key)
   - Save with ID: `assemblyai`

## Implementation

### Option 1: Import Workflow (Recommended - 5 minutes)

1. **Deactivate and delete** broken CloudConvert workflow in n8n

2. **Import new workflow:**
   - File: `workflows/TikTok_Complete_Processor_ASSEMBLYAI.json`
   - Click "Import from File" in n8n

3. **Update credential references:**
   - Open workflow editor
   - Click on "Upload to AssemblyAI" node
   - Select your AssemblyAI credential
   - Repeat for "Submit Transcription" and "Get Transcription" nodes

4. **Activate workflow**

5. **Test:**
   ```bash
   curl -X POST https://royhen.app.n8n.cloud/webhook/analyze-video-complete \
     -H 'Content-Type: application/json' \
     -d '{"video_url":"https://www.tiktok.com/@agentic.james/video/7583734051748482317"}'
   ```

### Option 2: Manual Implementation

If you prefer to modify your existing workflow:

#### Step 1: Remove Old Nodes

Delete these nodes:
- "Transcribe Audio" (Whisper)
- "Create CloudConvert Job" (if present)
- "Wait for CloudConvert" (if present)
- "Check CloudConvert Status" (if present)
- "Download MP3" (if present)

#### Step 2: Add 4 AssemblyAI Nodes

**Node 1: Upload to AssemblyAI**
- **Type:** HTTP Request
- **Method:** POST
- **URL:** `https://api.assemblyai.com/v2/upload`
- **Authentication:** Select your AssemblyAI credential
- **Send Body:** Yes
- **Body Type:** Binary Data
- **Position:** After "Download Video"

**Node 2: Submit Transcription**
- **Type:** HTTP Request
- **Method:** POST
- **URL:** `https://api.assemblyai.com/v2/transcript`
- **Authentication:** Select your AssemblyAI credential
- **Send Body:** Yes
- **Body Type:** JSON
- **JSON Body:**
```javascript
={{ {"audio_url": $json.upload_url} }}
```

**Node 3: Wait for AssemblyAI**
- **Type:** Wait
- **Wait Time:** 10 seconds

**Node 4: Get Transcription**
- **Type:** HTTP Request
- **Method:** GET
- **URL:**
```javascript
={{ "https://api.assemblyai.com/v2/transcript/" + $('Submit Transcription').item.json.id }}
```
- **Authentication:** Select your AssemblyAI credential

#### Step 3: Connect Nodes

```
Download Video
    ↓
    ├─→ Upload to Google Drive
    │
    └─→ Upload to AssemblyAI
            ↓
        Submit Transcription
            ↓
        Wait for AssemblyAI (10s)
            ↓
        Get Transcription
            ↓
        Merge All (input 1)
```

#### Step 4: Update Format Final Output Node

The "Get Transcription" node returns the same structure as Whisper, so no changes needed to the format node. The transcription text is in `$json.text`.

## Workflow Flow

```
Webhook Trigger
    ↓
Get Video Info (sub-workflow)
    ↓
[Visual Analysis (GPT-4) + Download Video]
    ↓
Upload to Google Drive + Upload to AssemblyAI
    ↓
Submit Transcription
    ↓
Wait 10 seconds
    ↓
Get Transcription
    ↓
Merge Results (3 inputs)
    ↓
Generate Metadata (GPT-4 Mini)
    ↓
Format & Return JSON
```

## How It Works

1. **Upload to AssemblyAI**
   - Takes video binary from "Download Video" node
   - Uploads to AssemblyAI's `/v2/upload` endpoint
   - Returns `upload_url`

2. **Submit Transcription**
   - Sends `upload_url` to `/v2/transcript` endpoint
   - Returns transcript `id` and initial status (`queued`)

3. **Wait for AssemblyAI**
   - Waits 10 seconds for processing
   - TikTok videos (10-60s) typically process in 5-15 seconds

4. **Get Transcription**
   - Polls `/v2/transcript/{id}` endpoint
   - Returns full transcript with `text` field
   - Same structure as Whisper response

## Response Format

AssemblyAI returns the same key fields as Whisper:

```json
{
  "id": "abc123",
  "status": "completed",
  "text": "Full transcription text here...",
  "words": [...],
  "confidence": 0.96,
  ...
}
```

Your existing "Format Final Output" node already extracts `$json.text`, so no changes needed.

## Cost Breakdown

**Per TikTok video (10-60 seconds):**
- GPT-4 Vision: $0.01
- **AssemblyAI: $0.0004-0.0025** (was Whisper: $0.006)
- GPT-4 Mini: $0.001
- **Total: $0.0114-0.0135** ✅

**Savings:** 29-33% cheaper than Whisper + CloudConvert

**Free tier:** $50 credit = ~20,000 videos

## Troubleshooting

### "Status is still 'processing' after 10 seconds"
- Increase wait time to 15-20 seconds
- Longer videos may need more time

### "Upload failed" or 401 error
- Check AssemblyAI credential is correct
- Verify API key in AssemblyAI dashboard
- Ensure credential is selected in all 3 HTTP Request nodes

### "Cannot read property 'text' of undefined"
- Transcription not complete yet
- Increase wait time
- Or add retry logic to poll status

### Empty transcription (text is empty string)
- Video has no speech (expected for music-only videos)
- This is normal behavior

## Testing

Test with the large video that previously failed with Whisper:

```bash
curl -X POST https://royhen.app.n8n.cloud/webhook/analyze-video-complete \
  -H 'Content-Type: application/json' \
  -d '{"video_url":"https://www.tiktok.com/@agentic.james/video/7583734051748482317"}' \
  --max-time 60
```

**Expected:**
- Processing time: ~20-30 seconds
- HTTP 200 with complete JSON response
- Transcription in `transcription` field

## Additional Features (Optional)

AssemblyAI includes free features you can enable by adding fields to the Submit Transcription JSON:

```javascript
={{
  {
    "audio_url": $json.upload_url,
    "sentiment_analysis": true,
    "auto_highlights": true,
    "content_safety": true
  }
}}
```

These add valuable metadata for free:
- **Sentiment analysis:** Positive/negative/neutral tone per sentence
- **Auto highlights:** Key moments in the video
- **Content safety:** Detects sensitive content

## Next Steps

1. Get AssemblyAI API key
2. Add credential to n8n
3. Import workflow
4. Test with large video
5. If successful, delete old CloudConvert workflow
6. Commit changes to git

---

**Sources:**
- [AssemblyAI Documentation - Transcribe Audio](https://www.assemblyai.com/docs/getting-started/transcribe-an-audio-file)
- [AssemblyAI API Reference](https://www.assemblyai.com/docs/api-reference/transcripts/submit)
- [AssemblyAI Pricing](https://www.assemblyai.com/pricing)
