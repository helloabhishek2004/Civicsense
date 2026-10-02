# CivicSense — Laptop Setup & Live Demonstration Runbook

This guide contains everything you need to start, run, and demonstrate the **CivicSense** system on this laptop (`LOQ`) without external dependencies or internet access during the demonstration.

---

## 1. Quick Start: Launching the Demonstration (1 Step)

Open **PowerShell** in the project root (`Civicsense\Civicsense`) and run:

```powershell
.\scripts\start_demo.ps1
```

### What this automatically does:
1. **Resolves Python**: Uses the high-speed local venv at `C:\Users\LOQ\civicsense_venv` (outside OneDrive to prevent file-locking).
2. **Detects Current Wi-Fi / Hotspot IP**: Automatically detects the laptop's active LAN IPv4 address (e.g., `10.11.201.7`) using `.\scripts\get_lan_ip.ps1`.
3. **Updates Android Endpoint**: Syncs the detected IP directly into `android/local.properties`.
4. **Connects Database**: Connects to the bundled SQLite database (`backend/civicsense.db`) containing **42 verified reports**, **14 aggregated issues**, **6 municipal departments**, and precomputed AI embeddings. Zero Docker required!
5. **Starts Web Dashboard**: Launches the Authority Dashboard in a separate PowerShell window at [http://localhost:5173](http://localhost:5173).
6. **Starts FastAPI Backend**: Launches the server on `0.0.0.0:8000`, listening for local requests and remote Android mobile app connections.

---

## 2. Key Access URLs

| Interface | URL | Purpose |
| :--- | :--- | :--- |
| **Web Authority Dashboard** | [http://localhost:5173](http://localhost:5173) | Authority triage, map visualization, duplicate matching, verification |
| **Interactive API Documentation** | [http://localhost:8000/docs](http://localhost:8000/docs) | Swagger UI for live testing all REST endpoints |
| **Backend Health Check (Local)** | [http://localhost:8000/health](http://localhost:8000/health) | Verifies DB, MiniLM NLP model, and MobileNet vision model status |
| **Mobile API Base URL (Wi-Fi)** | `http://<YOUR_LAN_IP>:8000` | Configured inside Android app for mobile-to-backend communication |
| **Mobile Health Check (Phone Browser)** | `http://<YOUR_LAN_IP>:8000/health` | Test phone-to-laptop connectivity from phone's web browser |

---

## 3. Connecting the Android Mobile App

The native Android app (Jetpack Compose) communicates with the backend over HTTP.

### Pre-requisite: Same Network
Your phone and this laptop must be on the **same Wi-Fi network** OR connected via **Mobile Hotspot**.

### In-App Dynamic Server URL Configuration
You do **not** need to recompile the APK when you change Wi-Fi networks!
1. Open the **CivicSense** app on your phone.
2. Go to the **Profile** tab (bottom navigation).
3. Under **Preferences**, tap **Backend Server URL**.
4. Enter the active backend URL displayed by `start_demo.ps1` (e.g., `http://10.11.201.7:8000`).
5. Tap **Save**. All network requests (report submission, image uploads, feed sync) will immediately route to your laptop's backend.

### Quick Phone Connectivity Test
Before opening the app, open Chrome or any browser on your phone and browse to:
```
http://<YOUR_LAN_IP>:8000/health
```
If you see JSON output with `"status": "ok"` and `"database": "healthy"`, connectivity is 100% verified.

---

## 4. Handling Campus Wi-Fi AP Isolation (Crucial Demo Fallback)

> [!WARNING]
> **Campus / University Wi-Fi Warning**:
> Many university and college Wi-Fi networks enable **Client Isolation** (or AP Isolation), which blocks devices on the same Wi-Fi from talking to each other. If your phone cannot load `http://<LAN_IP>:8000/health` over college Wi-Fi:

### The 1-Minute Hotspot Fix:
1. Turn on **Mobile Hotspot** on your phone (or a peer's phone).
2. Connect your laptop to that phone's Mobile Hotspot Wi-Fi.
3. In PowerShell, run:
   ```powershell
   .\scripts\get_lan_ip.ps1 -UpdateFiles
   ```
   *(Or simply restart `.\scripts\start_demo.ps1`)*
4. Note the new Hotspot IP (e.g., `192.168.43.xxx`).
5. In the Android app, go to **Profile -> Backend Server URL** and set it to the new Hotspot URL.
6. Phone-to-laptop communication is now guaranteed and completely immune to college firewall/isolation rules!

---

## 5. Installing the Android App

The pre-compiled debug APK is ready to install at:
```
android\app\build\outputs\apk\debug\app-debug.apk
```

### Options to Transfer to Phone:
- **Option A (USB Cable)**: Connect phone via USB, set to "File Transfer", copy `app-debug.apk` to phone's "Downloads" folder, and install via file manager.
- **Option B (Browser Download via Localhost)**: When backend is running, the laptop can serve files or transfer via messaging (WhatsApp Web / Telegram).
- **Option C (ADB)**: If Android SDK / platform-tools is available:
  ```powershell
  adb install -r android\app\build\outputs\apk\debug\app-debug.apk
  ```

---

## 6. Live Demonstration Walkthrough Guide

To give a compelling, polished demonstration to faculty or evaluators:

### Step 1: Show the System Health & Architecture
- Open [http://localhost:8000/health](http://localhost:8000/health) in browser.
- Point out:
  - `status: "ok"`
  - `database: "healthy"`
  - `models: { "minilm": "READY", "degraded_mode": false }`
  - Real offline AI models running locally on the laptop CPU.

### Step 2: Show the Web Authority Dashboard
- Open [http://localhost:5173](http://localhost:5173).
- Show:
  - **Overview / Stats**: 42 active citizen reports across 6 municipal departments.
  - **Spatial Map**: Geospatial cluster map showing issues across Trivandrum / Kariavattom.
  - **AI Triage & Review**: Explainable severity scoring, multimodal confidence, and duplicate detection recommendations.

### Step 3: Demonstrate Live Citizen Report Submission (from Android Phone)
- On the phone, open **CivicSense**.
- Tap **+ Report Issue**.
- Capture or select a photo of a road pothole or garbage heap.
- On-device edge check analyzes image quality in real time (sharpness, blur, lighting).
- Fill in description: *"Large pothole causing vehicle damage near university gate."*
- Tap **Submit Report**.
- Within seconds, show the report appearing live in the **Web Dashboard** with automated AI category classification, calculated severity, and recommended department routing.

---

## 7. Troubleshooting Cheatsheet

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| `pip install WinError 32: process cannot access file` | OneDrive background sync locking files | The venv is safely located at `C:\Users\LOQ\civicsense_venv` outside OneDrive. Always use `C:\Users\LOQ\civicsense_venv\Scripts\python.exe`. |
| `ConnectionRefusedError` on phone | Wrong IP or phone on different network | Check IP with `.\scripts\get_lan_ip.ps1`. Ensure phone and laptop are on same Wi-Fi or phone hotspot. |
| Phone browser cannot open `http://<IP>:8000/health` | Campus Wi-Fi AP isolation | Switch to Phone Mobile Hotspot (Section 4). |
| Dashboard shows connection error | Backend not started or CORS | Ensure backend is running. CORS in `backend/app/main.py` is configured to allow LAN private IPs. |
| Want to reset demo data back to clean state | Testing onboarding and initial seed | Run `.\scripts\start_demo.ps1 -Reset` or tap **Reset Demo Data** in the mobile app Profile screen. |
