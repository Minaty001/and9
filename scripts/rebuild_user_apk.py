#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_APK = Path('/storage/emulated/0/jarvis.apk')
WORK_DIR = ROOT / 'apk_work' / 'rebuild_user'
FRAMEWORK = Path('/usr/share/android-framework-res/framework-res.apk')

def run(cmd, **kwargs):
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr.strip()}")
        sys.exit(1)
    return result.stdout.strip()

def main():
    print("═══ JARVIS Custom User APK Rebuild ═══\n")

    if not SOURCE_APK.is_file():
        raise FileNotFoundError(f"Source APK not found at {SOURCE_APK}")

    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Extract
    print("[1/5] Extracting source APK...")
    with zipfile.ZipFile(SOURCE_APK) as z:
        z.extractall(WORK_DIR / 'old')

    # Inject newly compiled classes.dex if it exists
    new_dex = Path('/root/jarvis_android/bin/classes.dex')
    if new_dex.is_file():
        print("  Injecting custom compiled classes.dex from jarvis_android...")
        shutil.copy2(new_dex, WORK_DIR / 'old' / 'classes.dex')

    # 2. Write AndroidManifest.xml (without VoiceInteractionService / Digital Assistant App configurations)
    print("[2/5] Writing updated AndroidManifest.xml...")
    MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.jarvis.app"
    android:versionCode="5"
    android:versionName="1.4">

    <uses-sdk android:minSdkVersion="28" android:targetSdkVersion="35" />

    <!-- Permissions requested by user -->
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.RECORD_AUDIO" />
    <uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />
    <uses-permission android:name="android.permission.CAMERA" />
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.MANAGE_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_MICROPHONE" />
    <uses-permission android:name="android.permission.VIBRATE" />
    <uses-permission android:name="android.permission.WAKE_LOCK" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
    <uses-permission android:name="android.permission.CALL_PHONE" />
    <uses-permission android:name="android.permission.READ_CONTACTS" />

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
</manifest>"""

    manifest_path = WORK_DIR / 'AndroidManifest.xml'
    with open(manifest_path, 'w', encoding='utf-8') as f:
        f.write(MANIFEST)

    # Remove any existing voice interaction metadata files from the resource folder
    xml_dir = WORK_DIR / 'old' / 'res' / 'xml'
    if xml_dir.exists():
        for f in xml_dir.glob('voice_interaction*'):
            try:
                f.unlink()
                print(f"  Removed voice interaction file: {f.name}")
            except Exception as e:
                print(f"  Warning: could not remove {f.name}: {e}")

    # 3. Package
    print("[3/5] Packaging with aapt...")
    unaligned = WORK_DIR / 'unaligned.apk'
    
    # We use aapt v1 for simplicity as it works perfectly with raw resource extraction
    run([
        "aapt", "package", "-f",
        "-M", str(manifest_path),
        "-S", str(WORK_DIR / 'old' / 'res'),
        "-I", str(FRAMEWORK),
        "-F", str(unaligned),
        "--min-sdk-version", "28",
        "--target-sdk-version", "35",
    ])

    # 4. Inject dex and other assets from old APK
    print("[4/5] Injecting classes.dex and assets...")
    with zipfile.ZipFile(unaligned, 'a') as apk:
        # classes.dex
        apk.write(WORK_DIR / 'old' / 'classes.dex', 'classes.dex')
        # assets (if any)
        assets_dir = WORK_DIR / 'old' / 'assets'
        if assets_dir.exists():
            for root, dirs, files in os.walk(assets_dir):
                for file in files:
                    full_path = Path(root) / file
                    rel_path = full_path.relative_to(WORK_DIR / 'old')
                    apk.write(full_path, str(rel_path))

    # 5. Zipalign + Sign
    print("[5/5] Aligning and signing...")
    aligned = WORK_DIR / 'aligned.apk'
    run(["zipalign", "-f", "4", str(unaligned), str(aligned)])

    keystore = WORK_DIR / 'jarvis.keystore'
    run([
        "keytool", "-genkeypair",
        "-v", "-keystore", str(keystore),
        "-keyalg", "RSA", "-keysize", "2048",
        "-validity", "10000",
        "-alias", "jarvis",
        "-storepass", "jarvis123",
        "-keypass", "jarvis123",
        "-dname", "CN=JARVIS, O=Jarvis, C=IN"
    ])

    final_apk = WORK_DIR / 'final.apk'
    run([
        "apksigner", "sign",
        "--ks", str(keystore),
        "--ks-pass", "pass:jarvis123",
        "--key-pass", "pass:jarvis123",
        "--ks-key-alias", "jarvis",
        "--out", str(final_apk),
        str(aligned)
    ])

    # Overwrite the original /storage/emulated/0/jarvis.apk
    shutil.copy2(final_apk, SOURCE_APK)
    print(f"\n✅ SUCCESS! Replaced {SOURCE_APK} with the updated permission-rich, non-assistant APK.")

    # Dump badging to verify
    print("\nVerifying APK permissions and capabilities:")
    dump_out = run(["aapt", "dump", "badging", str(SOURCE_APK)])
    for line in dump_out.split('\n'):
        if 'permission' in line or 'package:' in line or 'service' in line:
            print("  ", line)

if __name__ == '__main__':
    main()
