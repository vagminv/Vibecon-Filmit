# Re-upload Feature Implementation

## Changes Made

### 1. Frontend Changes (`/app/frontend/src/components/ContentStudio.jsx`)

**Before:**
- Upload button only showed when `shot.uploaded === false`
- Once uploaded, no way to replace the footage

**After:**
- Upload/Replace button now shows for both uploaded and non-uploaded shots
- Button text changes based on upload status:
  - **"Upload Footage"** - When shot has not been uploaded yet
  - **"Replace Footage"** - When shot already has content uploaded
- Button variant changes to "secondary" when showing "Replace" to differentiate it visually
- Button is hidden only when in editing mode

### 2. Backend Changes (`/app/backend/routers/director.py`)

**Before:**
- Used `$push` to add segments, keeping all uploads
- No deletion of old files
- Multiple versions of same segment could exist in database

**After:**
- Checks for existing segment with same name
- **Deletes old video file** from filesystem if it exists
- Uses `$pull` to remove old segment data from database first
- Then uses `$push` to add the new segment data
- Ensures only the **latest uploaded content** exists for each shot
- Added logging for file deletion operations

## How It Works

1. **User uploads initial video** for a shot
   - Shot marked as `uploaded: true`
   - Video file saved to `/app/backend/uploads/`
   - Segment data stored in `uploaded_segments` array

2. **User clicks "Replace Footage"**
   - File picker opens
   - User selects new video file

3. **Backend processes replacement:**
   - Finds old segment in database
   - Deletes old video file from disk
   - Removes old segment from `uploaded_segments` array
   - Saves new video file
   - Adds new segment data with updated timestamp

4. **Result:**
   - Shot still marked as `uploaded: true`
   - Only the latest video file exists on disk
   - Only the latest segment data exists in database
   - Video assembly will use the newest footage

## Testing Instructions

1. **Create a new project:**
   - Go to Director Home
   - Click "Start New Project"
   - Describe your video goal
   - Wait for shot list to be generated

2. **Upload initial footage:**
   - Click "Upload Footage" on any shot
   - Select a video file
   - Wait for upload to complete
   - Shot card turns green with checkmark

3. **Test re-upload:**
   - Click "Replace Footage" button (now visible on uploaded shot)
   - Select a different video file
   - Wait for upload to complete
   - Shot remains marked as uploaded

4. **Verify backend behavior:**
   - Check that old file was deleted from `/app/backend/uploads/`
   - Check database `uploaded_segments` array only has one entry per shot
   - Assemble video to confirm latest footage is used

## Database Schema Impact

**uploaded_segments array structure:**
```json
{
  "uploaded_segments": [
    {
      "segment_name": "hook",
      "file_path": "/app/backend/uploads/project-id_hook_video.mp4",
      "filename": "video.mp4",
      "uploaded_at": "2025-11-09T17:30:00.000Z"
    }
  ]
}
```

**Key behavior:**
- Each `segment_name` appears only ONCE in the array
- Most recent `uploaded_at` timestamp reflects last upload
- Old `file_path` is deleted from disk and removed from array

## Edge Cases Handled

1. **File doesn't exist:** Warning logged but upload continues
2. **Multiple rapid re-uploads:** Each replaces the previous
3. **Assembly with replaced footage:** Uses latest file_path
4. **Missing project:** Returns 404 error
5. **Editing mode:** Upload button hidden to prevent conflicts

## UI/UX Improvements

- **Visual feedback:** Button changes from "outline" to "secondary" variant when showing "Replace"
- **Clear labeling:** Users know they're replacing, not adding a second video
- **Consistent behavior:** Same upload flow for initial and replacement uploads
- **No confirmation dialog:** Smooth workflow (could add confirmation if desired)

## Files Modified

1. `/app/frontend/src/components/ContentStudio.jsx` - Lines 269-298
2. `/app/backend/routers/director.py` - Lines 171-224

## Recommendations

### Optional Enhancements:
1. **Add confirmation dialog** before replacing to prevent accidental overwrites
2. **Keep upload history** in a separate array for audit trail
3. **Show upload timestamp** in shot card
4. **Add "Compare" feature** to preview old vs new before replacing
5. **Implement undo** functionality for last N minutes after replacement
