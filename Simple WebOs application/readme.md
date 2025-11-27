# WebOS Video Receiver App - Complete Setup Guide

## 📋 Overview
This guide walks you through building a simple webOS app from scratch on Windows, testing it, and then gradually adding video receiving functionality.

---

## 🎯 Phase 1: Basic "Hello World" App (START HERE)

### Prerequisites
1. **Windows PC** with internet connection
2. **LG WebOS TV** (2015 or newer)
3. **Both PC and TV** on the same Wi-Fi network

---

## 🛠️ Step-by-Step Setup

### **STEP 1: Install Node.js**
1. Go to https://nodejs.org/
2. Download **LTS version** (recommended)
3. Run installer, use default settings
4. Verify installation:
   ```cmd
   node --version
   npm --version
   ```

### **STEP 2: Install WebOS CLI Tools**
1. Open **Command Prompt as Administrator**
2. Run:
   ```cmd
   npm install -g @webos-tools/cli
   ```
3. Wait for installation (may take 2-5 minutes)
4. Verify:
   ```cmd
   ares --version
   ```
   Should show version info

### **STEP 3: Prepare Your TV**
1. On your TV, go to **LG Content Store**
2. Search and install **"Developer Mode"** app
3. Launch Developer Mode app
4. Create account at: https://us.lgaccount.com/join/terms
5. Login to Developer Mode app
6. Toggle **"Dev Mode Status"** to **ON**
7. **Write down the IP address** shown (e.g., 192.168.1.100)
8. Go to TV Settings → Network → **LG Connect Apps** → Turn ON

### **STEP 4: Create Project Directory**
1. Create a folder on your PC: `C:\webos-projects\video-receiver-app`
2. Inside this folder, create these files:

**File 1: `appinfo.json`**
```json
{
  "id": "com.example.videoreceiver",
  "version": "1.0.0",
  "vendor": "My Company",
  "type": "web",
  "main": "index.html",
  "title": "Video Receiver",
  "icon": "icon.png",
  "resolution": "1920x1080"
}
```

**File 2: `index.html`** (Copy from the HTML artifact above)

**File 3: Create a simple icon**
- Create a PNG file named `icon.png` (80x80 pixels)
- You can use any image or create a simple colored square in Paint

### **STEP 5: Connect to Your TV**
1. Open Command Prompt
2. Navigate to your project:
   ```cmd
   cd C:\webos-projects\video-receiver-app
   ```
3. Add your TV (replace IP_ADDRESS with your TV's IP):
   ```cmd
   ares-setup-device --add webos_tv --info "{\"host\":\"IP_ADDRESS\",\"port\":\"9922\"}"
   ```
   Example:
   ```cmd
   ares-setup-device --add webos_tv --info "{\"host\":\"192.168.1.100\",\"port\":\"9922\"}"
   ```
4. **On your TV**: Accept the pairing request that appears
5. Verify connection:
   ```cmd
   ares-setup-device --list
   ```

### **STEP 6: Package and Deploy**
1. Package your app:
   ```cmd
   ares-package . --outdir ./build
   ```
2. Install on TV:
   ```cmd
   ares-install --device webos_tv ./build/*.ipk
   ```
3. Launch the app:
   ```cmd
   ares-launch --device webos_tv com.example.videoreceiver
   ```

### **STEP 7: View Your App**
- Check your TV screen - you should see a purple gradient screen with:
  - ✅ "App Running Successfully!"
  - App ID and version info
  - TV model information

### **View Logs (If Something Goes Wrong)**
```cmd
ares-log --device webos_tv --follow com.example.videoreceiver
```

---

## 🎉 Success Checklist
- ✅ Node.js installed
- ✅ WebOS CLI tools installed
- ✅ Developer Mode enabled on TV
- ✅ TV paired with PC
- ✅ App packaged successfully
- ✅ App installed on TV
- ✅ App running and visible on TV

---

## 🚀 Next Steps (Phase 2)
Once the basic app is working, we'll add:
1. HTTP server to receive video URLs
2. File storage capability
3. Video player functionality

---

## 🐛 Troubleshooting

### "ares: command not found"
- Reinstall webOS CLI: `npm install -g @webos-tools/cli`
- Check PATH environment variable

### "Cannot connect to TV"
- Check both devices on same network
- Verify TV IP address
- Ensure Developer Mode is ON
- Restart Developer Mode app on TV

### "Packaging failed"
- Ensure `appinfo.json` has valid JSON
- Check all required files exist
- Verify file permissions

### "Installation failed"
- Run: `ares-setup-device --list` to check connection
- Re-pair your TV
- Check TV's Developer Mode app is running

### App doesn't launch
- Check logs: `ares-log --device webos_tv --follow com.example.videoreceiver`
- Verify `index.html` is present
- Check for JavaScript errors in logs

---

## 📝 Useful Commands

```cmd
# List connected devices
ares-setup-device --list

# Close app on TV
ares-launch --device webos_tv --close com.example.videoreceiver

# Uninstall app
ares-install --device webos_tv --remove com.example.videoreceiver

# View running apps
ares-launch --device webos_tv --running

# View app info
ares-install --device webos_tv --list
```

---

## 💡 Tips
1. Keep Developer Mode app **open and running** on TV
2. Use the same network for PC and TV
3. Check logs frequently during development
4. Test each change incrementally

---

## 📞 Need Help?
If you get stuck at any step, let me know:
- Which step you're on
- Any error messages you see
- What happens when you run the command

**Let's test Phase 1 first before moving to video functionality!**