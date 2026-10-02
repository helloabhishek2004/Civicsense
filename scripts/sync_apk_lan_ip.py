"""Sync Android APK target IP and re-sign with embedded debug key.

Replaces the backend API base URL in APK DEX files, updates DEX Adler32/SHA-1
headers, and re-signs the APK using uber-apk-signer (v1+v2+v3 signatures).
Takes ~1.5 seconds and requires zero Android SDK.
"""

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import zipfile
import zlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_APK = PROJECT_ROOT / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
SIGNER_JAR = PROJECT_ROOT / "scripts" / "uber-apk-signer.jar"


def get_current_lan_ip() -> str:
    """Extract active Wi-Fi IPv4 from get_lan_ip.ps1 or netsh."""
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(PROJECT_ROOT / "scripts" / "get_lan_ip.ps1")],
            text=True,
        )
        match = re.search(r"Active LAN IPv4:\s+([0-9\.]+)", out)
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return "10.11.201.7"


def fix_dex_header(data: bytearray) -> bytearray:
    """Recalculate SHA-1 and Adler32 checksums for Android DEX file."""
    sha1 = hashlib.sha1(data[32:]).digest()
    data[12:32] = sha1
    adler = zlib.adler32(data[12:]) & 0xFFFFFFFF
    data[8:12] = adler.to_bytes(4, "little")
    return data


def find_existing_ip(apk_path: Path) -> str | None:
    """Find the IP address currently baked into the APK DEX files."""
    with zipfile.ZipFile(apk_path, "r") as z:
        for name in z.namelist():
            if name.endswith(".dex"):
                data = z.read(name)
                match = re.search(rb"http://([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+):8000", data)
                if match:
                    return match.group(1).decode("ascii")
    return None


def patch_and_sign(target_ip: str, apk_path: Path = DEFAULT_APK) -> bool:
    if not apk_path.exists():
        print(f"ERROR: APK not found at {apk_path}")
        return False

    old_ip = find_existing_ip(apk_path)
    if not old_ip:
        print(f"Warning: Could not detect existing IP in {apk_path}")
        return False

    old_url = f"http://{old_ip}:8000".encode("ascii")
    target_url = f"http://{target_ip}:8000".encode("ascii")

    # Pad with trailing slashes so byte length matches exactly
    if len(target_url) < len(old_url):
        target_url = target_url + b"/" * (len(old_url) - len(target_url))
    elif len(target_url) > len(old_url):
        print(f"Warning: Target URL length ({len(target_url)}) exceeds original ({len(old_url)}).")

    if old_url == target_url:
        print(f"APK is already configured for {target_ip}. No patch needed.")
        return True

    print(f"Patching APK endpoint: {old_url.decode()} -> {target_url.decode()}")

    # Re-signing requires a Java runtime
    java_exe = shutil.which("java")
    ms_jdk = Path("C:/Program Files/Microsoft/jdk-21.0.12.101-hotspot/bin/java.exe")
    if ms_jdk.exists():
        java_exe = str(ms_jdk)

    if not java_exe:
        print("  Notice: Java runtime (java.exe) not found; skipping automatic APK re-signing.")
        print(f"          (Phone can connect manually: CivicSense -> Profile -> Backend Server URL -> http://{target_ip}:8000)")
        return False

    temp_unsigned = apk_path.parent / "temp-unsigned.apk"
    try:
        with zipfile.ZipFile(apk_path, "r") as zin, zipfile.ZipFile(
            temp_unsigned, "w", compression=zipfile.ZIP_DEFLATED
        ) as zout:
            for item in zin.infolist():
                # Strip existing signatures
                if item.filename.startswith("META-INF/") and (
                    item.filename.endswith(".SF")
                    or item.filename.endswith(".RSA")
                    or item.filename.endswith(".MF")
                ):
                    continue
                data = zin.read(item.filename)
                if item.filename.endswith(".dex") and old_url in data:
                    d = bytearray(data)
                    count = 0
                    while old_url in d:
                        idx = d.find(old_url)
                        d[idx : idx + len(old_url)] = target_url
                        count += 1
                    fixed = fix_dex_header(d)
                    print(f"  Patched {count} occurrences in {item.filename}")
                    zout.writestr(item, bytes(fixed))
                else:
                    zout.writestr(item, data)

        cmd = [java_exe, "-jar", str(SIGNER_JAR), "--apks", str(temp_unsigned), "--overwrite"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Signing failed: {res.stderr}")
            return False

        temp_unsigned.replace(apk_path)
        print(f"SUCCESS: {apk_path.name} signed & ready! Target: {target_url.decode().strip('/')}")
        return True
    except FileNotFoundError:
        print("  Notice: Java runtime not found; skipping automatic APK re-signing.")
        return False
    finally:
        if temp_unsigned.exists():
            temp_unsigned.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default=None, help="Target LAN IP for the APK")
    args = parser.parse_args()

    ip = args.ip or get_current_lan_ip()
    ok = patch_and_sign(ip)
    sys.exit(0 if ok else 1)

