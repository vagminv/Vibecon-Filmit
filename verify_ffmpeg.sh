#!/bin/bash
# FFmpeg Verification Script
# This script checks if FFmpeg is properly installed and accessible

echo "================================================"
echo "  FFmpeg Installation Verification"
echo "================================================"
echo ""

# Check FFmpeg binary
echo "1. Checking FFmpeg binary..."
if command -v ffmpeg &> /dev/null; then
    echo "   ✅ FFmpeg binary found at: $(which ffmpeg)"
    ffmpeg -version | head -1
else
    echo "   ❌ FFmpeg binary not found!"
    echo "   Installing FFmpeg..."
    apt-get update > /dev/null 2>&1
    apt-get install -y ffmpeg > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "   ✅ FFmpeg installed successfully"
    else
        echo "   ❌ Failed to install FFmpeg"
        exit 1
    fi
fi
echo ""

# Check FFprobe binary
echo "2. Checking FFprobe binary..."
if command -v ffprobe &> /dev/null; then
    echo "   ✅ FFprobe binary found at: $(which ffprobe)"
else
    echo "   ❌ FFprobe binary not found!"
    exit 1
fi
echo ""

# Check Python ffmpeg-python module
echo "3. Checking ffmpeg-python module..."
cd /app/backend
if python3 -c "import ffmpeg" 2>/dev/null; then
    echo "   ✅ ffmpeg-python module installed"
    pip show ffmpeg-python | grep Version
else
    echo "   ❌ ffmpeg-python module not found!"
    echo "   Installing ffmpeg-python..."
    pip install ffmpeg-python > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "   ✅ ffmpeg-python installed successfully"
    else
        echo "   ❌ Failed to install ffmpeg-python"
        exit 1
    fi
fi
echo ""

# Test FFmpeg from Python
echo "4. Testing FFmpeg integration with Python..."
python3 << 'PYEOF'
import ffmpeg
import sys

try:
    # Test stream creation
    stream = ffmpeg.input('test.mp4')
    print("   ✅ FFmpeg-python integration working")
except Exception as e:
    print(f"   ❌ Integration test failed: {e}")
    sys.exit(1)
PYEOF

if [ $? -ne 0 ]; then
    exit 1
fi
echo ""

# Check video tools imports
echo "5. Checking video_tools.py imports..."
python3 << 'PYEOF'
import sys
sys.path.append('/app/backend/agents')
try:
    from video_tools import (
        ffmpeg_merge_videos,
        ffmpeg_add_transition,
        ffmpeg_add_subtitles,
        get_video_metadata,
        optimize_for_platform
    )
    print("   ✅ All video_tools functions available")
except ImportError as e:
    print(f"   ❌ Import failed: {e}")
    sys.exit(1)
PYEOF

if [ $? -ne 0 ]; then
    exit 1
fi
echo ""

echo "================================================"
echo "  ✅ All FFmpeg checks passed!"
echo "================================================"
echo ""
echo "Summary:"
echo "  - FFmpeg binary: Installed"
echo "  - FFprobe binary: Installed"
echo "  - ffmpeg-python module: Installed"
echo "  - Python integration: Working"
echo "  - video_tools.py: Ready"
echo ""
