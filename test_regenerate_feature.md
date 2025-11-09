# Video Regeneration Feature Implementation

## Changes Made

### 1. Frontend Changes (`/app/frontend/src/components/ContentStudio.jsx`)

**Added "Regenerate with Different Settings" Button:**
- New button appears after video assembly completes
- Located below the "Download Final Video" button
- Opens the assembly configuration dialog for customization
- Allows users to change transitions, subtitles, and platform optimization

**Button Behavior:**
- **Before Assembly**: Shows "Generate Final Video" button
- **During Assembly**: Shows progress bar with percentage
- **After Completion**: Shows both "Download Final Video" and "Regenerate with Different Settings"
- **Dialog Button**: Changes text from "Start Assembly" to "Regenerate Video" when regenerating

### 2. Backend Changes (`/app/backend/services/video_assembly_service.py`)

**Added Cleanup Logic in `start_assembly()` method:**
- Queries database for existing assemblies of the same project
- Deletes old assembled video files from filesystem
- Deletes temporary files (transitions, subtitles) from previous assembly
- Removes old assembly records from database
- Ensures only the latest assembly exists

**Cleanup Process:**
1. Find all previous assemblies for the project
2. Delete `output_path` video files
3. Delete all temporary files matching pattern `{old_assembly_id}_*`
4. Remove database records for old assemblies
5. Create new assembly with fresh ID

## How It Works

### Initial Video Generation:
```
All shots uploaded → Click "Generate Final Video" → 
Configure settings (transitions, subtitles, platform) → 
Click "Start Assembly" → Assembly begins → 
Progress bar shows 0-100% → Status: completed → 
"Download Final Video" + "Regenerate" buttons appear
```

### Video Regeneration:
```
Video completed → Click "Regenerate with Different Settings" → 
Assembly dialog opens (with previous settings) → 
Modify settings (change transition type, duration, etc.) → 
Click "Regenerate Video" → Backend deletes old files → 
New assembly begins → New video generated → 
Can download new version
```

## Assembly Options Available

### Transitions:
- **Enable/Disable**: Toggle switch
- **Type Options**: 
  - Fade (default)
  - Wipe
  - Dissolve
  - Slide Down
  - Slide Up
- **Duration**: 0.2s - 2.0s (adjustable)

### Subtitles:
- **Enable/Disable**: Toggle switch
- **Position**: Top, Center, Bottom
- **Font Size**: 24-72px (adjustable)
- **Auto-generated**: From shot scripts

### Platform Optimization:
- **YouTube**: 1920x1080, 16:9
- **TikTok**: 1080x1920, 9:16
- **Instagram Reels**: 1080x1920, 9:16

## Database Impact

**video_assemblies collection:**

Before regeneration:
```json
[
  {
    "assembly_id": "old-uuid-123",
    "project_id": "project-abc",
    "status": "completed",
    "output_path": "/app/backend/processed/old-uuid-123_final.mp4",
    "options": {"transition_type": "fade"}
  }
]
```

After regeneration:
```json
[
  {
    "assembly_id": "new-uuid-456",
    "project_id": "project-abc",
    "status": "completed",
    "output_path": "/app/backend/processed/new-uuid-456_final.mp4",
    "options": {"transition_type": "wipe"}
  }
]
```

**Note**: Old assembly record and files are deleted.

## File System Cleanup

**Files Deleted During Regeneration:**
- Main assembled video: `{old_assembly_id}_final.mp4`
- Merged video: `{old_assembly_id}_merged.mp4`
- Subtitle segments: `{old_assembly_id}_subtitle_0.mp4`, `_subtitle_1.mp4`, etc.
- Transition segments: `{old_assembly_id}_transition_1.mp4`, `_transition_2.mp4`, etc.

**Files Kept:**
- Original uploaded segments (in `/app/backend/uploads/`)
- These are reused for regeneration

## Benefits

1. **Experiment with Settings**: Try different transitions without re-uploading footage
2. **Platform Optimization**: Generate multiple versions for different platforms
3. **Clean Storage**: Old assemblies automatically deleted
4. **No Confusion**: Only latest assembled video exists
5. **Quick Iteration**: Faster than re-uploading and re-assembling

## Use Cases

### Use Case 1: Change Transition Style
- User generates video with "fade" transitions
- Watches preview, wants sharper cuts
- Clicks "Regenerate", changes to "wipe" transitions
- New video generated with wipe transitions

### Use Case 2: Multi-Platform Publishing
- Generate for YouTube (16:9)
- Download
- Regenerate for TikTok (9:16)
- Download
- Now has both versions from same footage

### Use Case 3: Subtitle Adjustments
- Generate with large subtitles (72px)
- Text too prominent
- Regenerate with smaller font (48px)
- Better visual balance

## UI States

### State 1: Before First Assembly
```
[Generate Final Video] button (green gradient)
```

### State 2: During Assembly
```
Assembling video... 45%
[Progress Bar]
Processing segments...
```

### State 3: After Completion
```
[Download Final Video] button (blue gradient)
[Regenerate with Different Settings] button (outline, green border)
```

### State 4: Regenerating
```
Assembling video... 30%
[Progress Bar]
Adding transitions...
```

## Technical Details

### Assembly ID Generation:
- Each assembly gets unique UUID
- Used for tracking progress
- Used for naming output files
- Allows multiple assemblies to be in progress (theoretically)

### Cleanup Safety:
- Wrapped in try-catch to prevent blocking
- Logs warnings if files can't be deleted
- Continues assembly even if cleanup fails
- Never deletes original uploaded segments

### Assembly Job Structure:
```python
{
    'assembly_id': 'uuid',
    'project_id': 'uuid',
    'status': 'queued|processing|completed|failed',
    'progress': 0-100,
    'segment_paths': [...],
    'shot_list': [...],
    'options': {...},
    'output_path': '/path/to/final.mp4',
    'created_at': 'ISO timestamp',
    'completed_at': 'ISO timestamp'
}
```

## Testing Instructions

1. **Create a project** with multiple shots
2. **Upload footage** to all shots
3. **Click "Generate Final Video"**
4. **Configure settings** (e.g., fade transitions, subtitles on)
5. **Wait for completion**
6. **Click "Download"** to get first version
7. **Click "Regenerate with Different Settings"**
8. **Change transition** to "wipe" or "dissolve"
9. **Change platform** from YouTube to TikTok
10. **Click "Regenerate Video"**
11. **Wait for new assembly**
12. **Download new version**
13. **Verify**:
    - Old assembly file deleted from `/app/backend/processed/`
    - New assembly file exists
    - Database only has latest assembly record
    - Settings were applied correctly

## Files Modified

1. `/app/frontend/src/components/ContentStudio.jsx`:
   - Lines 784-806: Added regenerate button
   - Line 1232: Dynamic button text for dialog

2. `/app/backend/services/video_assembly_service.py`:
   - Lines 49-103: Added cleanup logic to `start_assembly()` method

## Future Enhancements

### Optional Improvements:
1. **Assembly History**: Keep last 3 assemblies instead of deleting
2. **Compare Versions**: Side-by-side preview before downloading
3. **Preset Templates**: Save favorite settings as templates
4. **Batch Generation**: Generate for all platforms at once
5. **Preview Before Download**: Show 10-second preview in browser
6. **Download Queue**: Allow downloading while regenerating
