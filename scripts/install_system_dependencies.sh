#!/bin/bash
# System Dependencies Installation Script
# Run this script to install all required system-level dependencies

set -e  # Exit on error

echo "================================================"
echo "  Installing System Dependencies"
echo "================================================"
echo ""

# Update package list
echo "📦 Updating package list..."
apt-get update -qq > /dev/null 2>&1

# Install FFmpeg (required for video processing)
echo "🎬 Installing FFmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    apt-get install -y ffmpeg > /dev/null 2>&1
    echo "   ✅ FFmpeg installed"
else
    echo "   ✅ FFmpeg already installed"
fi

# Verify FFmpeg installation
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version | head -1 | awk '{print $3}')
    echo "   📌 FFmpeg version: $FFMPEG_VERSION"
else
    echo "   ❌ FFmpeg installation failed!"
    exit 1
fi

# Verify FFprobe installation
if command -v ffprobe &> /dev/null; then
    echo "   ✅ FFprobe installed"
else
    echo "   ❌ FFprobe installation failed!"
    exit 1
fi

echo ""
echo "================================================"
echo "  ✅ All system dependencies installed!"
echo "================================================"
echo ""
