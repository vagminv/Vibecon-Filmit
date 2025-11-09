# Video Generation Testing Guide

## Issue Found

**Error:** "Failed to check assembly status"

**Root Cause:** FFmpeg was not installed on the system

**Fix Applied:** 
```bash
apt-get update && apt-get install -y ffmpeg
sudo supervisorctl restart backend
```

---

## Current Status

✅ **FFmpeg Installed:** `/usr/bin/ffmpeg` (version 5.1.7)
✅ **Backend Restarted:** Services operational
✅ **Health Check:** Passing

---

## How to Test Video Generation

### Prerequisites

1. **Create a project** with AI Director
2. **Upload footage** to at least one shot
3. **Click "Generate Video"** button

### Step-by-Step Testing

#### 1. Upload Test Videos

**Option A: Use Real Videos**
- Click "Upload Footage" on any shot
- Select a video file from your device
- Wait for upload to complete (green checkmark)

**Option B: Create Test Videos** (for quick testing)
```bash
# Create 3-second test videos
cd /app/backend/uploads

# Black screen video
ffmpeg -f lavfi -i color=c=black:s=1920x1080:d=3 -r 30 test_shot1.mp4

# Red screen video
ffmpeg -f lavfi -i color=c=red:s=1920x1080:d=3 -r 30 test_shot2.mp4

# Blue screen video
ffmpeg -f lavfi -i color=c=blue:s=1920x1080:d=3 -r 30 test_shot3.mp4
```

#### 2. Generate Video

1. **Navigate to Content Studio** for your project
2. **Scroll down** below shot cards
3. **Click "Generate Video"** button
4. **Configure settings:**
   - Enable/disable transitions
   - Choose transition type (fade, wipe, etc.)
   - Enable/disable subtitles
   - Select platform (YouTube, TikTok, Instagram)
5. **Click "Start Assembly"** (or "Regenerate Video")

#### 3. Monitor Progress

**In the UI:**
- Progress bar shows 0-100%
- Status messages update:
  - "Processing segments..."
  - "Adding transitions..."
  - "Optimizing video..."
  - "Finalizing..."

**In Backend Logs:**
```bash
tail -f /var/log/supervisor/backend.out.log | grep assembly
```

Expected messages:
```
INFO: Starting assembly for project {project_id}
INFO: Assembly job {assembly_id} created
INFO: Processing segment 1/3
INFO: Adding transitions
INFO: Assembly completed successfully
```

#### 4. Download Video

When complete:
1. **"Download Video"** button appears
2. Click to download final assembled video
3. Video file downloads to your device

#### 5. Regenerate (Optional)

1. **Click "Regenerate Video"**
2. **Change settings:**
   - Try different transition type
   - Adjust platform optimization
   - Modify subtitle settings
3. **Click "Regenerate Video"**
4. New video generates with updated settings

---

## API Testing (Backend)

### Test Assembly Endpoint

```bash
# Start assembly
curl -X POST http://localhost:8001/api/director/assemble \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "YOUR_PROJECT_ID",
    "options": {
      "add_transitions": true,
      "transition_type": "fade",
      "transition_duration": 0.8,
      "add_subtitles": true,
      "subtitle_position": "bottom",
      "subtitle_font_size": 48,
      "optimize_platform": "youtube"
    }
  }' | python3 -m json.tool
```

Expected response:
```json
{
  "success": true,
  "assembly_id": "uuid-here",
  "message": "Video assembly started. Processing N segments.",
  "segments_count": N
}
```

### Check Assembly Status

```bash
# Replace ASSEMBLY_ID with actual ID from above
curl -s http://localhost:8001/api/director/assembly-status/ASSEMBLY_ID | python3 -m json.tool
```

Expected response:
```json
{
  "assembly_id": "uuid",
  "status": "completed",  // or "queued", "processing", "failed"
  "progress": 100,
  "output_path": "/app/backend/processed/uuid_final.mp4",
  "created_at": "timestamp",
  "completed_at": "timestamp"
}
```

### Download Video

```bash
# Download the assembled video
curl -o final_video.mp4 http://localhost:8001/api/director/download/ASSEMBLY_ID
```

---

## Troubleshooting

### Error: "FFmpeg not found"

**Solution:**
```bash
# Install FFmpeg
apt-get update && apt-get install -y ffmpeg

# Restart backend
sudo supervisorctl restart backend

# Verify
which ffmpeg
ffmpeg -version
```

### Error: "No video segments found"

**Cause:** No videos uploaded to any shots

**Solution:**
1. Go to Content Studio
2. Click "Upload Footage" on each shot
3. Upload video files
4. Try "Generate Video" again

### Error: "Assembly failed"

**Check logs:**
```bash
tail -f /var/log/supervisor/backend.err.log
```

**Common causes:**
- FFmpeg not installed
- Invalid video files
- Corrupted uploads
- Disk space full
- Permission issues

### Progress Stuck

**If progress bar doesn't update:**

1. **Check backend logs:**
```bash
tail -f /var/log/supervisor/backend.out.log | grep assembly
```

2. **Check assembly status manually:**
```bash
curl http://localhost:8001/api/director/assembly-status/ASSEMBLY_ID
```

3. **Restart backend if needed:**
```bash
sudo supervisorctl restart backend
```

### Frontend Error: "Failed to check assembly status"

**Causes:**
1. Backend down
2. Network issue
3. Assembly ID invalid
4. CORS issue

**Solutions:**
```bash
# Check backend is running
sudo supervisorctl status backend

# Check backend logs
tail -f /var/log/supervisor/backend.err.log

# Restart backend
sudo supervisorctl restart backend

# Verify health
curl http://localhost:8001/api/health
```

---

## Video Assembly Options

### Transitions

**Types:**
- `fade` - Smooth fade (default)
- `wipe` - Directional wipe
- `dissolve` - Cross dissolve
- `slidedown` - Slide down
- `slideup` - Slide up

**Duration:** 0.2 - 2.0 seconds

### Subtitles

**Position:** top, center, bottom
**Font Size:** 24-72px
**Source:** Auto-generated from shot scripts

### Platform Optimization

**YouTube:** 1920x1080, 16:9
**TikTok:** 1080x1920, 9:16 (vertical)
**Instagram Reels:** 1080x1920, 9:16 (vertical)

---

## Performance Notes

### Assembly Time

Typical assembly times:
- **3 segments, no effects:** ~5-10 seconds
- **5 segments, transitions:** ~15-30 seconds
- **10 segments, transitions + subtitles:** ~45-90 seconds

Variables:
- Number of segments
- Video resolution
- Transitions enabled
- Subtitle processing
- Platform optimization

### File Sizes

**Uploads Directory:** `/app/backend/uploads/`
- Original uploaded segments

**Processed Directory:** `/app/backend/processed/`
- Final assembled videos
- Temporary subtitle files
- Temporary transition files

**Cleanup:**
Old assembly files are automatically deleted when regenerating.

---

## Quick Test Script

```bash
#!/bin/bash
# Quick test of video assembly

echo "1. Checking FFmpeg..."
which ffmpeg || (echo "❌ FFmpeg not found" && exit 1)
echo "✅ FFmpeg installed"

echo "2. Checking backend..."
curl -s http://localhost:8001/api/health | grep -q "healthy"
if [ $? -eq 0 ]; then
    echo "✅ Backend healthy"
else
    echo "❌ Backend not responding"
    exit 1
fi

echo "3. Creating test videos..."
cd /app/backend/uploads
ffmpeg -f lavfi -i color=c=black:s=1280x720:d=2 -r 30 test1.mp4 -y 2>/dev/null
ffmpeg -f lavfi -i color=c=red:s=1280x720:d=2 -r 30 test2.mp4 -y 2>/dev/null
echo "✅ Test videos created"

echo ""
echo "All checks passed! Ready to test video generation."
echo "Upload test1.mp4 and test2.mp4 to your project shots."
```

---

## Summary

**Status:** ✅ Video generation system operational

**Requirements:**
- FFmpeg installed
- Backend running
- Videos uploaded to shots

**Test Flow:**
1. Upload footage to shots
2. Click "Generate Video"
3. Configure settings
4. Wait for completion
5. Download video

**Support:**
- Logs: `/var/log/supervisor/backend.*.log`
- Test script: See above
- Troubleshooting: See section above
