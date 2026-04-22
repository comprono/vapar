# Phase 1 Quick Setup Guide

## What I've Automated:
✅ Downloaded Docker Desktop installer  
✅ Created `setup_phase1.bat` script  
✅ Prepared verification tests  

## What You Need to Do (3 Minutes):

### Step 1: Install Docker Desktop
1. Find `Docker Desktop Installer.exe` in your Downloads folder
2. **Right-click** → **Run as Administrator**
3. Accept defaults (Use WSL 2)
4. Click "Install"
5. **Restart computer** when prompted

### Step 2: Run Setup Script
After restart:
1. Open PowerShell in `TB 1AG` folder
2. Run: `.\setup_phase1.bat`

The script will:
- Install Python packages
- Start TimescaleDB
- Run verification tests

### Step 3: Verify
You should see:
```
✓ All imports successful
✓ Database connection successful  
✓ VaR calculated
✓ Position tracking works
```

---

**If you encounter issues**, just let me know the error message and I'll help troubleshoot!
