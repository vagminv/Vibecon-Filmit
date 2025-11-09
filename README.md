# Filmit! - AI-Powered Video Creation Platform

## 🚀 Quick Start for New Environments

**IMPORTANT: When setting up in a new Emergent instance, run this first:**

```bash
/app/setup.sh
```

This installs FFmpeg and all required dependencies.

---

## Common Error Fix

**Getting "Assembly failed: Merge failed: [Errno 2] No such file or directory: '/usr/bin/ffmpeg'"?**

**Solution:**
```bash
# Run the setup script
/app/setup.sh

# Or manually install FFmpeg
apt-get update && apt-get install -y ffmpeg

# Restart services
sudo supervisorctl restart all
```

---

## Full Setup Instructions

See [SETUP_INSTRUCTIONS.md](/app/SETUP_INSTRUCTIONS.md) for complete setup guide.

---

# Here are your Instructions
