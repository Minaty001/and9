#!/usr/bin/env python3
"""
rebuild_apk.py — Rebuild jarvis.apk with updated permissions.

Removes unnecessary permissions (Camera, Location, Storage, etc.)
Adds required permissions (SYSTEM_ALERT_WINDOW, FOREGROUND_SERVICE_MICROPHONE)
Keeps only what JARVIS actually needs.

Uses: aapt2, zipalign, apksigner (all available on this system)
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OLD_APK = ROOT / "jarvis.apk"
NEW_APK = ROOT / "jarvis_updated.apk"
WORK_DIR = ROOT / "apk_work" / "rebuild"

# ── Clean text manifest with correct permissions ─────────────

MANIFEST_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.jarvis.app"
    android:versionCode="3"
    android:versionName="1.2">

    <uses-sdk android:minSdkVersion="28" android:targetSdkVersion="35" />

    <!-- ═══ REQUIRED PERMISSIONS ONLY ═══ -->
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.RECORD_AUDIO" />
    <uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />
    <uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_MICROPHONE" />
    <uses-permission android:name="android.permission.VIBRATE" />
    <uses-permission android:name="android.permission.WAKE_LOCK" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />

    <!-- REMOVED: CAMERA, LOCATION, STORAGE, BOOT_COMPLETED — not needed -->

    <application
        android:label="JARVIS"
        android:icon="@drawable/icon"
        android:usesCleartextTraffic="true"
        android:theme="@android:style/Theme.NoTitleBar">

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:configChanges="orientation|screenSize|keyboardHidden">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
"""


def run(cmd, **kwargs):
    """Run a command, print it, and check for errors."""
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr.strip()}")
        sys.exit(1)
    return result.stdout.strip()


def main():
    print("═══ JARVIS APK Permission Update ═══\n")

    # 1. Setup work directory
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    if not OLD_APK.is_file():
        raise FileNotFoundError(f"Expected APK not found at {OLD_APK}")

    # 2. Extract old APK
    print("[1/6] Extracting old APK...")
    import zipfile
    with zipfile.ZipFile(OLD_APK) as z:
        z.extractall(WORK_DIR / "old")

    # 3. Write updated manifest
    print("[2/6] Writing updated AndroidManifest.xml...")
    manifest_path = WORK_DIR / "AndroidManifest.xml"
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(MANIFEST_XML)

    # 4. Compile resources with aapt2
    print("[3/6] Compiling resources...")
    res_dir = WORK_DIR / "old" / "res"
    compiled_dir = WORK_DIR / "compiled"
    compiled_dir.mkdir(parents=True, exist_ok=True)

    # Compile each resource file
    for dirpath, dirnames, filenames in os.walk(res_dir):
        for fname in filenames:
            fpath = Path(dirpath) / fname
            run(["aapt2", "compile", "-o", str(compiled_dir), str(fpath)])

    # 5. Link into APK
    print("[4/6] Linking APK...")
    # Find android.jar for linking
    android_jar = None
    for path in [
        "/usr/share/android-sdk/platforms/android-28/android.jar",
        "/usr/lib/android-sdk/platforms/android-28/android.jar",
        "/opt/android-sdk/platforms/android-28/android.jar",
    ]:
        if os.path.exists(path):
            android_jar = path
            break

    if not android_jar:
        # Try to find any android.jar
        result = subprocess.run(["find", "/", "-name", "android.jar", "-maxdepth", "6"],
                                capture_output=True, text=True, timeout=10)
        jars = result.stdout.strip().split("\n")
        if jars and jars[0]:
            android_jar = jars[0]

    if not android_jar:
        # Use aapt (v1) instead — it doesn't need android.jar for simple repackaging
        print("  android.jar not found — using aapt v1 fallback...")
        return rebuild_with_aapt_v1()

    compiled_files = [
        str(compiled_dir / f)
        for f in os.listdir(compiled_dir) if f.endswith(".flat")
    ]

    unaligned = WORK_DIR / "jarvis_unaligned.apk"
    link_cmd = [
        "aapt2", "link",
        "-o", str(unaligned),
        "--manifest", str(manifest_path),
        "-I", android_jar,
    ] + compiled_files
    run(link_cmd)

    # Add classes.dex from old APK
    print("[5/6] Adding classes.dex...")
    import zipfile as zf
    with zf.ZipFile(unaligned, "a") as apk:
        old_dex = WORK_DIR / "old" / "classes.dex"
        apk.write(old_dex, "classes.dex")

    # 6. Zipalign + sign
    print("[6/6] Aligning and signing...")
    aligned = WORK_DIR / "jarvis_aligned.apk"
    run(["zipalign", "-f", "4", str(unaligned), str(aligned)])

    # Generate keystore if needed
    keystore = WORK_DIR / "jarvis.keystore"
    if not os.path.exists(keystore):
        run([
            "keytool", "-genkeypair",
            "-v", "-keystore", keystore,
            "-keyalg", "RSA", "-keysize", "2048",
            "-validity", "10000",
            "-alias", "jarvis",
            "-storepass", "jarvis123",
            "-keypass", "jarvis123",
            "-dname", "CN=JARVIS, O=Jarvis, C=IN",
        ])

    run([
        "apksigner", "sign",
        "--ks", keystore,
        "--ks-pass", "pass:jarvis123",
        "--key-pass", "pass:jarvis123",
        "--ks-key-alias", "jarvis",
        "--out", NEW_APK,
        aligned,
    ])

    print(f"\n✅ Done! Updated APK: {NEW_APK}")
    print("\nPermission changes:")
    print("  REMOVED: CAMERA, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION,")
    print("           READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, RECEIVE_BOOT_COMPLETED")
    print("  ADDED:   SYSTEM_ALERT_WINDOW, FOREGROUND_SERVICE_MICROPHONE")
    print("  KEPT:    INTERNET, ACCESS_NETWORK_STATE, RECORD_AUDIO, MODIFY_AUDIO_SETTINGS,")
    print("           VIBRATE, WAKE_LOCK, POST_NOTIFICATIONS, FOREGROUND_SERVICE")

    # Replace old APK
    shutil.copy2(NEW_APK, OLD_APK)
    print(f"\n📦 {OLD_APK.name} replaced with updated version (v1.2)")


def rebuild_with_aapt_v1():
    """Fallback: use aapt (v1) to repackage with updated manifest."""
    print("  Using aapt v1 repackage method...")

    manifest_path = WORK_DIR / "AndroidManifest.xml"
    res_dir = WORK_DIR / "old" / "res"
    unaligned = WORK_DIR / "jarvis_unaligned.apk"

    # Package with aapt v1
    run([
        "aapt", "package", "-f",
        "-M", str(manifest_path),
        "-S", str(res_dir),
        "-F", str(unaligned),
        "--min-sdk-version", "28",
        "--target-sdk-version", "35",
    ])

    # Add classes.dex
    import zipfile as zf
    with zf.ZipFile(unaligned, "a") as apk:
        old_dex = WORK_DIR / "old" / "classes.dex"
        apk.write(old_dex, "classes.dex")

    # Zipalign
    aligned = WORK_DIR / "jarvis_aligned.apk"
    run(["zipalign", "-f", "4", str(unaligned), str(aligned)])

    # Sign
    keystore = WORK_DIR / "jarvis.keystore"
    run([
        "keytool", "-genkeypair",
        "-v", "-keystore", str(keystore),
        "-keyalg", "RSA", "-keysize", "2048",
        "-validity", "10000",
        "-alias", "jarvis",
        "-storepass", "jarvis123",
        "-keypass", "jarvis123",
        "-dname", "CN=JARVIS, O=Jarvis, C=IN",
    ])

    run([
        "apksigner", "sign",
        "--ks", str(keystore),
        "--ks-pass", "pass:jarvis123",
        "--key-pass", "pass:jarvis123",
        "--ks-key-alias", "jarvis",
        "--out", str(NEW_APK),
        str(aligned),
    ])

    print(f"\n✅ Done! Updated APK: {NEW_APK}")
    shutil.copy2(NEW_APK, OLD_APK)
    print(f"📦 {OLD_APK.name} replaced with updated version (v1.2)")


if __name__ == "__main__":
    main()
