#!/bin/bash
# Filmit! Setup Script
# Run this script when setting up a new environment
# This ensures all system dependencies are installed

set -e  # Exit on error

echo "================================================"
echo "  Filmit! Environment Setup"
echo "================================================"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Update package lists
echo "📦 Updating package lists..."
apt-get update -qq > /dev/null 2>&1

# Install FFmpeg (required for video assembly)
echo "🎬 Checking FFmpeg..."
if ! command_exists ffmpeg; then
    echo "   Installing FFmpeg..."
    apt-get install -y ffmpeg > /dev/null 2>&1
    echo "   ✅ FFmpeg installed"
else
    echo "   ✅ FFmpeg already installed ($(ffmpeg -version | head -1 | awk '{print $3}'))"
fi

# Verify FFprobe (comes with FFmpeg)
if ! command_exists ffprobe; then
    echo "   ❌ FFprobe not found (should come with FFmpeg)"
    exit 1
else
    echo "   ✅ FFprobe available"
fi

# Install Python dependencies
echo ""
echo "🐍 Installing Python dependencies..."
cd /app/backend
if [ -f "requirements.txt" ]; then
    pip install -q -r requirements.txt
    echo "   ✅ Python dependencies installed"
else
    echo "   ⚠️  requirements.txt not found"
fi

# Install Node dependencies
echo ""
echo "📦 Installing Node dependencies..."
cd /app/frontend
if [ -f "package.json" ]; then
    yarn install --silent 2>/dev/null
    echo "   ✅ Node dependencies installed"
else
    echo "   ⚠️  package.json not found"
fi

# Create necessary directories
echo ""
echo "📁 Creating required directories..."
mkdir -p /app/backend/uploads
mkdir -p /app/backend/processed
chmod 755 /app/backend/uploads
chmod 755 /app/backend/processed
echo "   ✅ Directories created"

# Verify setup
echo ""
echo "🔍 Verifying installation..."
ERRORS=0

if ! command_exists ffmpeg; then
    echo "   ❌ FFmpeg not found"
    ERRORS=$((ERRORS + 1))
fi

if ! command_exists python3; then
    echo "   ❌ Python3 not found"
    ERRORS=$((ERRORS + 1))
fi

if ! command_exists node; then
    echo "   ❌ Node not found"
    ERRORS=$((ERRORS + 1))
fi

if [ $ERRORS -eq 0 ]; then
    echo "   ✅ All dependencies verified"
else
    echo "   ❌ Found $ERRORS missing dependencies"
    exit 1
fi

echo ""
echo "================================================"
echo "  ✅ Setup Complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "  1. Restart services: sudo supervisorctl restart all"
echo "  2. Check status: sudo supervisorctl status"
echo ""
