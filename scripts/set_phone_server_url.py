import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_adb() -> Path:
    which_adb = shutil.which("adb")
    if which_adb:
        return Path(which_adb)
    # Check common Android SDK and winget locations
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        sdk_adb = Path(local_app_data) / "Android" / "Sdk" / "platform-tools" / "adb.exe"
        if sdk_adb.exists():
            return sdk_adb
        winget_dir = Path(local_app_data) / "Microsoft" / "WinGet"
        if winget_dir.exists():
            found = list(winget_dir.glob("**/platform-tools/adb.exe"))
            if found:
                return found[0]
    return Path("adb")


ADB = find_adb()
TARGET_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"



def make_string_pref(key: str, val: str) -> bytes:
    key_bytes = key.encode("utf-8")
    val_bytes = val.encode("utf-8")
    val_msg = bytes([0x2A, len(val_bytes)]) + val_bytes
    val_field = bytes([0x12, len(val_msg)]) + val_msg
    key_field = bytes([0x0A, len(key_bytes)]) + key_bytes
    entry = key_field + val_field
    return bytes([0x0A, len(entry)]) + entry


# 1. Fetch current preferences file from phone
cmd = [str(ADB), "exec-out", "run-as com.civicsense cat files/datastore/civicsense_preferences.preferences_pb"]
res = subprocess.run(" ".join(cmd), shell=True, capture_output=True)
data = res.stdout

if not data:
    print("Could not read preferences from phone.")
    sys.exit(1)

print(f"Read {len(data)} bytes from phone.")

# 2. Append or update custom_server_url
# Remove existing custom_server_url if present
if b"custom_server_url" in data:
    print("custom_server_url already present, will overwrite")

pref_entry = make_string_pref("custom_server_url", TARGET_URL)
new_data = data + pref_entry

# Write to local temp file
temp_file = Path("temp_new_prefs.pb")
temp_file.write_bytes(new_data)

# Push to device /data/local/tmp then move to app datastore via run-as
subprocess.run([str(ADB), "push", str(temp_file), "/data/local/tmp/civicsense_preferences.preferences_pb"], check=True)
subprocess.run([str(ADB), "shell", "run-as com.civicsense cp /data/local/tmp/civicsense_preferences.preferences_pb files/datastore/civicsense_preferences.preferences_pb"], check=True)
subprocess.run([str(ADB), "shell", "run-as com.civicsense chmod 600 files/datastore/civicsense_preferences.preferences_pb"], check=True)

temp_file.unlink(missing_ok=True)
print(f"Successfully configured phone Backend Server URL to: {TARGET_URL}")

# Restart app
subprocess.run([str(ADB), "shell", "am force-stop com.civicsense"], check=True)
subprocess.run([str(ADB), "shell", "am start -n com.civicsense/.MainActivity"], check=True)
print("Restarted CivicSense app on phone.")
